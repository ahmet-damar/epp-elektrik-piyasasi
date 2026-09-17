"""EPP — 'running' durumunda TAKILI KALMIŞ `ingestion_batch` kayıtlarını
bulan, KALICI, SALT OKUMA script (2026-09-17, doğrulama turu — kapsam
raporundaki Madde 1e).

**Değişmez (invariant):** hiçbir batch, established "gece-boyu kural"ın
öngördüğü normal yükleme/mutabakat/aktivasyon döngüsünden çok daha uzun
süre `running` durumunda kalmamalı. `word_2024.py` gibi loader'lar bir
batch'i YÜKLEME adımı bitince BİLİNÇLİ OLARAK `running` bırakır
(aktivasyon AYRI bir adımdır) — bu kısa süreliğine BEKLENEN bir ara
durumdur. Ama mutabakat/aktivasyon adımı hiç çalıştırılmazsa (elle
inceleme unutulursa) YA DA kalıcı bir mutabakat reddi varsa (bkz. Madde
1 — batch_id=732, `fact_uretim_kaynak_geneli`/2024-02, T3'ün Bulgu J
gereği kasıtlı olarak hiç yüklenmemesi yüzünden `periyot_aktivasyona_
uygun_mu()`nun ASLA geçemeyeceği bir durum), batch SÜRESİZ `running`
kalır — `job_status.next_retry_at`in geçmişte kalması deseniyle AYNI
sınıf sessiz-bekleme riski (bkz. `worker/analytics.py:gecmis_kalan_
isleri_bul()`, 2026-09-16).

**Madde 1d'nin bulgusu (bu script'in VAR OLMA nedeni):**
`ingestion_batch.status` durum makinesinde ('queued','running',
'succeeded','failed','retrying','dead_letter') "mutabakat tarafından
kalıcı olarak reddedildi" için AYRI bir TERMİNAL durum YOK — bir batch
süresiz `running` kalabilir, tıpkı batch 732 gibi (bkz. kapsam raporu
"Doğrulama Turu" eki, Madde 1). Bu script o şema boşluğunu KAPATMIYOR
(yeni bir durum/migration bu turun kapsamı DIŞINDA, yalnız ÖNERİLDİ) —
yalnız problemi GÖRÜNÜR kılıyor.

**MUTLAK KISIT — SALT OKUMA:** yalnız SELECT, hiçbir yazma YOK."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg
from psycopg import Connection

from worker.db import get_database_url

VARSAYILAN_ESIK_SAAT = 24.0


@dataclass(frozen=True)
class TakiliBatch:
    batch_id: int
    parser_version: str
    status: str
    created_at: datetime
    kac_saattir_calisiyor: float


def takili_running_batchleri_bul(
    conn: Connection,
    *,
    esik_saat: float = VARSAYILAN_ESIK_SAAT,
    simdi: datetime | None = None,
) -> list[TakiliBatch]:
    """`status='running'` VE `created_at`'i şu andan (`simdi`, testlerde
    sabitlenebilir) `esik_saat`den daha eskiye giden TÜM batch'leri döner
    — en eski önce sıralı. Boş liste = hiçbir batch eşiği aşmıyor."""
    if simdi is None:
        simdi = datetime.now(tz=UTC)
    sinir = simdi - timedelta(hours=esik_saat)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT batch_id, parser_version, status, created_at
            FROM ingestion_batch
            WHERE status = 'running' AND created_at < %s
            ORDER BY created_at
            """,
            (sinir,),
        )
        rows = cur.fetchall()
    return [
        TakiliBatch(
            batch_id=row[0],
            parser_version=row[1],
            status=row[2],
            created_at=row[3],
            kac_saattir_calisiyor=(simdi - row[3]).total_seconds() / 3600,
        )
        for row in rows
    ]


def main() -> int:
    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        conn.read_only = True
        takililar = takili_running_batchleri_bul(conn)
        conn.rollback()

    if not takililar:
        print(
            f"Hiçbir batch {VARSAYILAN_ESIK_SAAT:.0f} saatten uzun 'running' kalmamış."
        )
        return 0

    print(
        f"⚠️ {len(takililar)} batch {VARSAYILAN_ESIK_SAAT:.0f} saatten uzun "
        "'running' durumunda takılı:"
    )
    for t in takililar:
        print(
            f"  batch_id={t.batch_id} parser_version={t.parser_version} "
            f"created_at={t.created_at.isoformat()} "
            f"({t.kac_saattir_calisiyor:.1f} saattir çalışıyor)"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
