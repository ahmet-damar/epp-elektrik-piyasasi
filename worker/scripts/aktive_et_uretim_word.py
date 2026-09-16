"""EPP — Word (2016-2025) `uretim-geneli` batch'lerini (`fact_uretim_
kaynak_geneli`+`fact_uretim_il_geneli`) çapraz mutabakat ile GATE'li
aktive eder (2026-09-16, canlı backfill — ADIM 4 kapanışı).

`worker/scripts/backfill_uretim_excel.py`'nin aktivasyon deseniyle
BİREBİR AYNI (yalnız Excel'in TEK `parser_version` sabitinden farklı
olarak Word'ün 10 farklı `word-20XX-uretim-geneli-v1` değerini
`LIKE 'word-%-uretim-geneli-v1'` ile kapsar): her `running` durumundaki
batch için, o batch'in `tarih_id`'si `worker/scripts/mutabakat_uretim.
periyot_aktivasyona_uygun_mu()`den GEÇERSE `pipeline.batch_onayla()`
ile aktive edilir; geçmezse (yalnız 202402 beklenen istisnası — Bulgu J,
il tarafı hiç yüklenmedi, kaynak tarafı mutabakat kontrolünün kendi
`bir_taraf_eksik` kuralı gereği AYNI tarih_id'nin bir parçası olarak
doğal biçimde bloklanır — MUTABAKAT KONTROLÜNE İSTİSNA EKLENMEZ, established
proje kuralı) `running`/`is_active=false` bırakılır, elle inceleme
beklenir.

Kullanım:
    python -m worker.scripts.aktive_et_uretim_word --dry-run   # yalnız listele, aktive ETME
    python -m worker.scripts.aktive_et_uretim_word              # mutabakat + aktivasyon
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg

from worker import pipeline
from worker.db import get_database_url
from worker.scripts import mutabakat_uretim


def _running_tarih_idleri(conn: psycopg.Connection) -> list[tuple[int, int]]:
    """`word-%-uretim-geneli-v1` parser_version'lı, hâlâ 'running'
    durumundaki batch'lerin (tarih_id, batch_id) listesini döner —
    tarih_id'ye göre sıralı."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sa.source_period, ib.batch_id
            FROM ingestion_batch ib
            JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
            WHERE ib.parser_version LIKE 'word-%-uretim-geneli-v1'
              AND ib.status = 'running'
            ORDER BY sa.source_period
            """
        )
        rows = cur.fetchall()
    sonuc = []
    for source_period, batch_id in rows:
        yil_str, ay_str = source_period.split("-")
        tarih_id = int(yil_str) * 100 + int(ay_str)
        sonuc.append((tarih_id, batch_id))
    return sonuc


def main() -> int:
    ap = argparse.ArgumentParser(
        description="EPP: Word uretim-geneli batch'lerini mutabakat ile GATE'li aktive et"
    )
    ap.add_argument("--actor", default="manual-cli:aktive-et-uretim-word")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Yalnız hangi ayların aktive edileceğini/bloklanacağını listele, DB'YE YAZMA",
    )
    args = ap.parse_args()

    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        running = _running_tarih_idleri(conn)
        print(
            f"'running' durumunda {len(running)} batch bulundu (word-*-uretim-geneli-v1)."
        )

        aktive_edilen: list[int] = []
        bloklanan: list[tuple[int, str]] = []
        for tarih_id, batch_id in running:
            uygun, sebep = mutabakat_uretim.periyot_aktivasyona_uygun_mu(conn, tarih_id)
            print(
                f"  {tarih_id} (batch_id={batch_id}): uygun={uygun}"
                + (f" ({sebep})" if sebep else "")
            )
            if not uygun:
                bloklanan.append((tarih_id, sebep))
                continue
            if args.dry_run:
                aktive_edilen.append(tarih_id)
                continue
            pipeline.batch_onayla(conn, batch_id, actor_name=args.actor)
            conn.commit()
            aktive_edilen.append(tarih_id)

        print(
            f"\n{'[DRY-RUN] Aktive EDİLECEK' if args.dry_run else 'Aktive edilen'}: {aktive_edilen}"
        )
        if bloklanan:
            print(
                f"BLOKLANAN (aktive EDİLMEDİ — çapraz mutabakat uyuşmadı/bir taraf eksik): {bloklanan}"
            )

    return 0 if not bloklanan else 1


if __name__ == "__main__":
    sys.exit(main())
