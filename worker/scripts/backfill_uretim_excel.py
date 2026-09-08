"""EPP — `fact_uretim_kaynak_geneli` + `fact_uretim_il_geneli`'ni 2026+
Excel aylarına doldurur (2026-09-09, gece çalışması — Aşama 3/ADIM 3
madde 4). `worker/scripts/backfill_ulke_geneli_excel.py` için ince bir
CLI sarmalayıcı — AYNI `MANIFEST`'i (gerçek dosyaların yerel disk
konumları) yeniden kullanır, `fact_uretim`'in (T1/T4) kendi batch
zincirine DOKUNMAZ.

**Aktivasyon, çapraz mutabakat ile GATE'lidir (kullanıcı talimatı —
"tutmuyorsa aktivasyonu ENGELLE"):** her ay yüklendikten SONRA,
aktivasyondan ÖNCE `worker/scripts/mutabakat_uretim.
periyot_aktivasyona_uygun_mu()` çağrılır — yalnız UYGUN çıkan aylar
`pipeline.batch_onayla()` ile aktive edilir; uyumsuz aylar `running`
durumunda (is_active=false) bırakılır, elle inceleme beklenir.

Kullanım:
    python -m worker.scripts.backfill_uretim_excel --dry-run
    python -m worker.scripts.backfill_uretim_excel --ay 202601
    python -m worker.scripts.backfill_uretim_excel                # tümü + mutabakat + aktivasyon
    python -m worker.scripts.backfill_uretim_excel --aktive-etme  # yalnız yükle, aktive ETME
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import openpyxl
import psycopg

from worker import pipeline
from worker.db import get_database_url
from worker.scripts import mutabakat_uretim
from worker.scripts.backfill_ulke_geneli_excel import MANIFEST

PARSER_VERSION = "excel-uretim-geneli-v1"


def _batch_id_bul(conn: psycopg.Connection, source_period: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ib.batch_id FROM ingestion_batch ib
            JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
            WHERE sa.source_type = 'epdk_aylik' AND sa.source_period = %s
              AND ib.parser_version = %s AND ib.status != 'failed'
            ORDER BY ib.batch_id DESC LIMIT 1
            """,
            (source_period, PARSER_VERSION),
        )
        row = cur.fetchone()
    return row[0] if row else None


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
    ap.add_argument(
        "--aktive-etme",
        action="store_true",
        help="yükle ama aktivasyon adımını ATLA (mutabakat da çalışmaz)",
    )
    ap.add_argument("--actor", default="manual-cli:excel-uretim-backfill")
    args = ap.parse_args()

    hedefler = {args.ay: MANIFEST[args.ay]} if args.ay else MANIFEST

    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    islenen_tarihler: list[int] = []

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
                from worker import parser as parser_mod
                from worker.pipeline import _sayfa

                kaynak = (
                    parser_mod.tablo2_uretim_kaynak_oku(_sayfa(wb, 2), tarih_id)[
                        "uretim_mwh"
                    ].sum()
                    + parser_mod.tablo5_lisanssiz_uretim_kaynak_oku(
                        _sayfa(wb, 5), tarih_id
                    )["uretim_mwh"].sum()
                )
                il = (
                    parser_mod.tablo3_uretim_il_oku(_sayfa(wb, 3), tarih_id)[
                        "uretim_mwh"
                    ].sum()
                    + parser_mod.tablo6_lisanssiz_uretim_il_oku(
                        _sayfa(wb, 6), tarih_id
                    )["uretim_mwh"].sum()
                )
                print(
                    f"[DRY-RUN] {tarih_id}: kaynak toplamı={kaynak:.3f} "
                    f"il toplamı={il:.3f} fark={abs(kaynak - il):.3f}"
                )
                continue

            sonuc = pipeline.isle_ay_uretim_excel(
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
                islenen_tarihler.append(tarih_id)
                print(f"  -> batch_id={sonuc.batch_id}")

        if args.dry_run or args.aktive_etme:
            return 0

        print("\n=== Mutabakat + Aktivasyon (uygun olmayan aylar BLOKLANIR) ===")
        aktive_edilen: list[int] = []
        bloklanan: list[tuple[int, str]] = []
        for tarih_id in islenen_tarihler:
            uygun, sebep = mutabakat_uretim.periyot_aktivasyona_uygun_mu(conn, tarih_id)
            print(f"  {tarih_id}: uygun={uygun}" + (f" ({sebep})" if sebep else ""))
            if not uygun:
                bloklanan.append((tarih_id, sebep))
                continue
            yil, ay = tarih_id // 100, tarih_id % 100
            batch_id = _batch_id_bul(conn, f"{yil}-{ay:02d}")
            if batch_id is None:
                bloklanan.append((tarih_id, "batch_id bulunamadı"))
                continue
            pipeline.batch_onayla(conn, batch_id, actor_name=args.actor)
            conn.commit()
            aktive_edilen.append(tarih_id)

        print(f"\nAktive edilen: {aktive_edilen}")
        if bloklanan:
            print(
                f"BLOKLANAN (aktive EDİLMEDİ — çapraz mutabakat uyuşmadı): {bloklanan}"
            )

    return 0 if not bloklanan else 1


if __name__ == "__main__":
    raise SystemExit(main())
