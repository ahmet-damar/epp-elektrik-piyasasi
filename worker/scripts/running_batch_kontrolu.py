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

**Madde 1d'nin bulgusu — KAPANDI (2026-09-18, migration 20260918_0001):**
`ingestion_batch.status`a "mutabakat tarafından kalıcı olarak reddedildi"
için `mutabakat_reddedildi` terminal durumu eklendi (bkz. `worker/
scripts/mutabakat_uretim.py:mutabakat_reddini_kaydet()`).

**2026-09-19'da bulunan İKİNCİ, KARDEŞ boşluk (migration 20260919_0001
ile kapandı):** `otomatik_onaya_uygun()` (per-batch İÇ mutabakat,
`worker/pipeline.py`) `False` döndüğünde `worker/job_worker.py` batch'i
AYNI ŞEKİLDE hiçbir kalıcı duruma geçirmiyordu — konsola uyarı basıp
`running`de bırakıyordu (gerçek örnek: batch 4-8, 2026-02..06 Excel, 19
gün fark edilmedi, bkz. `Claude outputs/kapanis_2026-09-19_batch_4_8.md`).
Artık `job_worker.py` bu durumda batch'i `'onay_bekliyor'`a (TERMİNAL
DEĞİL) geçirir + `audit_log`'a yazar — bu script'in `takili_running_
batchleri_bul()`'u (yalnız `status='running'` filtreler) bu sınıfı ARTIK
YANLIŞLIKLA "takılı" SAYMAZ; ayrı, sakin bir `onay_bekleyen_batchleri_
bul()` bu kuyruğu raporlar.

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
VARSAYILAN_ONAY_ESIK_GUN = 0.0


@dataclass(frozen=True)
class TakiliBatch:
    batch_id: int
    parser_version: str
    status: str
    created_at: datetime
    kac_saattir_calisiyor: float


@dataclass(frozen=True)
class OnayBekleyenBatch:
    batch_id: int
    parser_version: str
    created_at: datetime
    kac_gundur_bekliyor: float
    sebep: str | None


def takili_running_batchleri_bul(
    conn: Connection,
    *,
    esik_saat: float = VARSAYILAN_ESIK_SAAT,
    simdi: datetime | None = None,
) -> list[TakiliBatch]:
    """`status='running'` VE `created_at`'i şu andan (`simdi`, testlerde
    sabitlenebilir) `esik_saat`den daha eskiye giden TÜM batch'leri döner
    — en eski önce sıralı. Boş liste = hiçbir batch eşiği aşmıyor.
    `'onay_bekliyor'`/`'mutabakat_reddedildi'` durumundaki batch'ler
    `status='running'` FİLTRESİNE hiç girmediğinden buradan doğal olarak
    HARİÇTİR — ayrı, kasıtlı bir durum geçişleri var artık."""
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


def onay_bekleyen_batchleri_bul(
    conn: Connection,
    *,
    esik_gun: float = VARSAYILAN_ONAY_ESIK_GUN,
    simdi: datetime | None = None,
) -> list[OnayBekleyenBatch]:
    """`status='onay_bekliyor'` olan TÜM batch'leri döner (varsayılan eşik
    0 gün — hepsini listeler). `takili_running_batchleri_bul()`'un
    "bir şey BOZULMUŞ olabilir" alarmından KASITLI OLARAK AYRI — bu,
    normal/beklenen bir iş akışı adımı olan sakin bir "inceleme kuyruğu"
    listesidir (2026-08-31'in Ocak/Şubat-Haziran yüklemelerinin HEMEN
    HEPSİ bu yoldan geçti, bkz. `06_canli_veri_operasyon_gunlugu.md`).
    `kac_gundur_bekliyor` `created_at`'ten hesaplanır (ingest tamamlanma
    anıyla pratikte aynı zaman damgası — ayrı bir `updated_at` kolonu
    yok)."""
    if simdi is None:
        simdi = datetime.now(tz=UTC)
    sinir = simdi - timedelta(days=esik_gun)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT batch_id, parser_version, created_at, error_summary
            FROM ingestion_batch
            WHERE status = 'onay_bekliyor' AND created_at < %s
            ORDER BY created_at
            """,
            (sinir,),
        )
        rows = cur.fetchall()
    return [
        OnayBekleyenBatch(
            batch_id=row[0],
            parser_version=row[1],
            created_at=row[2],
            kac_gundur_bekliyor=(simdi - row[2]).total_seconds() / 86400,
            sebep=row[3],
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
        onay_bekleyenler = onay_bekleyen_batchleri_bul(conn)
        conn.rollback()

    cikis_kodu = 0

    if not takililar:
        print(
            f"Hiçbir batch {VARSAYILAN_ESIK_SAAT:.0f} saatten uzun 'running' kalmamış."
        )
    else:
        cikis_kodu = 1
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

    if onay_bekleyenler:
        print(
            f"\nℹ️ {len(onay_bekleyenler)} batch 'onay_bekliyor' (insan kararı "
            "bekleniyor, ALARM DEĞİL — inceleme kuyruğu):"
        )
        for b in onay_bekleyenler:
            print(
                f"  batch_id={b.batch_id} parser_version={b.parser_version} "
                f"({b.kac_gundur_bekliyor:.1f} gündür) sebep={b.sebep}"
            )

    return cikis_kodu


if __name__ == "__main__":
    sys.exit(main())
