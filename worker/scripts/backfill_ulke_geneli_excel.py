"""EPP — `fact_tuketim_ulke_geneli`'yi 2026+ Excel aylarına genişletir
(2026-09-08, Aşama 3/ADIM 2). `worker/pipeline.py:isle_ay_ulke_geneli_excel()`
için ince bir CLI sarmalayıcı — Word yıllarındaki `word_20XX.py --ulke-geneli`
deseninin Excel eşdeğeri. `fact_tuketim`'in kendi batch zincirine DOKUNMAZ,
ayrı bir batch zinciri kurar (`parser_version='excel-ulke-geneli-v1'`).

Kaynak dosyaların yerel diskteki konumu bu ortama özgü (bazıları
`var/uploads/`de content-addressed, Ocak 2026 `EPDK Verileri/` klasöründe
orijinal adıyla) — MANIFEST burada AÇIKÇA elle eşlenir, Word yıllarındaki
MANIFEST_20XX desenine benzer.

Kullanım:
    python -m worker.scripts.backfill_ulke_geneli_excel --dry-run
    python -m worker.scripts.backfill_ulke_geneli_excel --ay 202601
    python -m worker.scripts.backfill_ulke_geneli_excel
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import openpyxl
import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from worker import pipeline
from worker.db import get_database_url

MANIFEST: dict[int, Path] = {
    202601: Path(
        r"C:\Users\adama\Downloads\EPDK Verileri\_PortalAdmin_Uploads_Content_FastAccess_8684c04c60369.xlsx"
    ),
    202602: Path(
        "var/uploads/e0fb81994c83a55f1422a3ce12e5dd782ecef64356fefd6ecfa1d8323fed7c9a.xlsx"
    ),
    202603: Path(
        "var/uploads/6a5fd2cb3155c9defcbb893fcfa8a6ab86ad0161efbc692e06ad13900f2e0bb2.xlsx"
    ),
    202604: Path(
        "var/uploads/e363301278d7eeb309153f61a3f5a142ab8a62872bc492f194b3bb24ff2b3f5a.xlsx"
    ),
    202605: Path(
        "var/uploads/de9f692b8f94a1fb0444666667b9ebdcb3d111085889b868956d21e66c58788d.xlsx"
    ),
    202606: Path(
        "var/uploads/c969785842e7c858f2e564b947937c8a8630ec7812155d0930f272cb722d9854.xlsx"
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--ay",
        type=int,
        help="belirli bir tarih_id (örn. 202601) — yoksa MANIFEST'teki tümü",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="yalnız parse et, DB'ye YAZMA"
    )
    ap.add_argument("--actor", default="manual-cli:excel-ulke-geneli-backfill")
    args = ap.parse_args()

    hedefler = {args.ay: MANIFEST[args.ay]} if args.ay else MANIFEST

    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    # prepare_threshold=None: bkz. worker/db.py:get_db_connection().
    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        for tarih_id, yol in sorted(hedefler.items()):
            if not yol.exists():
                print(f"[ATLA] {tarih_id}: dosya bulunamadı: {yol}")
                continue
            icerik = yol.read_bytes()
            wb = openpyxl.load_workbook(yol, data_only=True)
            yil, ay = tarih_id // 100, tarih_id % 100
            source_period = f"{yil}-{ay:02d}"

            if args.dry_run:
                from worker.pipeline import _sayfa

                ws11 = _sayfa(wb, 11)
                from worker import parser as parser_mod

                degerler = parser_mod.tablo11_genel_toplam_satiri_oku(ws11)
                print(f"[DRY-RUN] {tarih_id}: kümülatif Genel Toplam = {degerler}")
                continue

            sonuc = pipeline.isle_ay_ulke_geneli_excel(
                conn,
                wb=wb,
                tarih_id=tarih_id,
                dosya_adi=yol.name,
                icerik=icerik,
                source_period=source_period,
                actor_name=args.actor,
            )
            if sonuc is not None:
                conn.commit()
                print(f"  -> batch_id={sonuc.batch_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
