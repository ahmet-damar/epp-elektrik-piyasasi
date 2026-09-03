"""EPP — Word (2016-2022) aktarımından gelen TÜM 'running' batch'leri toplu
aktive eder (pipeline.batch_onayla()). Yalnız source_type='epdk_aylik_word'
kapsamındaki batch'leri hedefler — 2026 Excel/canlı-veri pipeline'ına HİÇ
dokunmaz (o batch'ler zaten ya succeeded ya farklı bir source_type taşır).

Neden toplu: 2016-2022 arası 160+ ayrı batch var (worker/scripts/word_20YY.py,
her biri ayrı bir CLI çalıştırması), tek tek `onayla.py --batch-id N` çok
yavaş. Bu script pipeline.batch_onayla()'yı DOĞRUDAN, aynı mantıkla, ama
toplu çağırır.

GÜVENLİK NOTU (neden "kırmızı satırlı" batch'ler de risksiz aktive edilebilir):
worker/pipeline.py:_isle_govde() -> kpi.dogrula_*() red saydığı satırları
ingest.fact_*_yukle()'ye HİÇ GÖNDERMEZ (yalnız .kabul DataFrame'i DB'ye
yazılır) — yani red satırlar zaten hiçbir zaman is_active=false olarak bile
DB'ye girmedi. batch_onayla() yalnız DB'de ZATEN duran (önceden kabul
edilmiş) satırları is_active=true yapar; hiçbir red satırını "geri
getirmez". Bu yüzden red sayısı > 0 olan bir batch'i aktive etmek, 0 red'li
bir batch'i aktive etmekten FARKLI bir risk taşımaz — ikisi de yalnız
önceden doğrulanmış satırları görünür kılar. (bkz. dokumanlar/09_PROJE_
DURUMU.md §3 madde 2 — red satırların KENDİSİNİN neden negatif olduğunu
anlamak hâlâ ayrı, açık bir araştırma konusu, ama bu AKTİVASYONU
engellemez.)

Varsayılan: --dry-run (yalnız listeler, hiçbir şey yazmaz). Gerçek aktivasyon
için --confirm gerekir.

Kullanım:
    python -m worker.scripts.toplu_onayla_word
    python -m worker.scripts.toplu_onayla_word --confirm --actor "Ahmet"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from worker import pipeline
from worker.db import get_database_url


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "EPP: 2016-2022 Word aktarımından gelen tüm 'running' batch'leri "
            "toplu aktive eder"
        )
    )
    ap.add_argument(
        "--confirm",
        action="store_true",
        help="Gerçekten aktive et (verilmezse yalnız listeler, hiçbir şey yazmaz)",
    )
    ap.add_argument(
        "--actor",
        default="Ahmet-toplu-aktivasyon",
        help="audit_log.actor_name'e yazılır (kim onayladı)",
    )
    args = ap.parse_args()

    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ib.batch_id, sa.source_period, ib.parser_version,
                       ib.total_row_count, ib.accepted_row_count,
                       ib.rejected_row_count
                FROM ingestion_batch ib
                JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
                WHERE sa.source_type = 'epdk_aylik_word'
                  AND ib.status = 'running'
                ORDER BY sa.source_period, ib.parser_version
                """
            )
            satirlar = cur.fetchall()

        if not satirlar:
            print("Aktivasyon bekleyen 'running' Word batch'i yok.")
            return 0

        print(f"{len(satirlar)} batch aktivasyon bekliyor:\n")
        toplam_red = 0
        for batch_id, donem, pv, toplam, kabul, red in satirlar:
            toplam_red += red or 0
            bayrak = f"  [{red} red]" if red else ""
            print(
                f"  batch_id={batch_id:>4}  {donem}  {pv:<20} "
                f"{kabul}/{toplam} kabul{bayrak}"
            )
        print(
            f"\nToplam: {len(satirlar)} batch, {toplam_red} satır zaten "
            "reddedilmiş (DB'ye hiç yazılmadı, aktivasyon bunları etkilemez)."
        )

        if not args.confirm:
            print(
                "\n[DRY-RUN] Hiçbir şey aktive edilmedi. Gerçek aktivasyon "
                "için --confirm ekleyin."
            )
            return 0

        print(f"\n--confirm verildi, {len(satirlar)} batch aktive ediliyor...")
        basarili = 0
        for batch_id, donem, pv, *_ in satirlar:
            try:
                aktive_edilen = pipeline.batch_onayla(
                    conn, batch_id, actor_name=args.actor
                )
                conn.commit()
                basarili += 1
                print(
                    f"  [OK] batch_id={batch_id} ({donem}, {pv}): "
                    f"{', '.join(aktive_edilen) or '(hiçbir tablo)'}"
                )
            except Exception as exc:  # noqa: BLE001 - toplu işlemde tek batch'in hatası diğerlerini durdurmasın
                conn.rollback()
                print(f"  [HATA] batch_id={batch_id} ({donem}, {pv}): {exc}")

    print(f"\nBitti: {basarili}/{len(satirlar)} batch aktive edildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
