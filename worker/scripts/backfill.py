"""EPP — Faz 1 backfill: yerel EPDK aylık dosyalarını job kuyruğuna alır
("tüm aylar" — geçmiş dosyaların toplu yüklenmesi, dokumanlar/01 §7 Faz 1).

Gerçek EPDK dosya adları tarih bilgisi TAŞIMAZ (bkz. bu projede kullanılan
gerçek dosya: "_PortalAdmin_Uploads_Content_FastAccess_8684c04c60369.xlsx" —
rastgele portal-üretimi bir ad) — bu yüzden dosya adından tarih_id türetmeye
ÇALIŞILMAZ; bir manifest (dosya adı -> tarih_id/source_period eşlemesi) gerekir.

Kullanım:
    python worker/scripts/backfill.py --dizin ./gercek_dosyalar --manifest manifest.json

manifest.json biçimi:
    {
      "2026_ocak.xlsx": {"tarih_id": 202601, "source_period": "2026-01"},
      "2026_subat.xlsx": {"tarih_id": 202602, "source_period": "2026-02"}
    }

Bu script YALNIZCA kuyruğa alır (pipeline.epdk_isi_kuyruga_al) — parse
etmez. Kuyruğu işlemek için ayrıca çalıştırılmalı: python worker/job_worker.py

Aynı mekanizma, düzeltilmiş bir parser sürümüyle TÜM ayları yeniden işlemek
için de kullanılabilir: aynı manifest'i farklı --parser-version ile tekrar
çalıştırmak, P0-5 sayesinde her ay için yeni bir batch açar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from worker import pipeline


def main() -> None:
    ap = argparse.ArgumentParser(
        description="EPP Faz 1 backfill: EPDK dosyalarını job kuyruğuna al"
    )
    ap.add_argument(
        "--dizin", required=True, type=Path, help="xlsx dosyalarının bulunduğu dizin"
    )
    ap.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="dosya adı -> {tarih_id, source_period} JSON eşlemesi",
    )
    ap.add_argument("--parser-version", default="0.1")
    ap.add_argument("--schema-version", default="1")
    args = ap.parse_args()

    manifest: dict[str, dict[str, object]] = json.loads(
        args.manifest.read_text(encoding="utf-8")
    )
    database_url = os.environ["DATABASE_URL"]

    kuyruklanan = 0
    # prepare_threshold=None: bkz. worker/db.py:get_db_connection().
    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        for dosya_adi, bilgi in manifest.items():
            yol = args.dizin / dosya_adi
            if not yol.exists():
                print(f"[ATLA] {dosya_adi}: dizinde yok ({yol})")
                continue
            icerik = yol.read_bytes()
            sonuc = pipeline.epdk_isi_kuyruga_al(
                conn,
                dosya_adi=dosya_adi,
                icerik=icerik,
                tarih_id=int(str(bilgi["tarih_id"])),
                source_period=str(bilgi["source_period"]),
                parser_version=args.parser_version,
                schema_version=args.schema_version,
            )
            conn.commit()
            kuyruklanan += 1
            print(
                f"[KUYRUKLANDI] {dosya_adi} -> batch_id={sonuc.batch_id} job_id={sonuc.job_id}"
            )

    print(
        f"\n{kuyruklanan} dosya kuyruğa alındı. İşlemek için: python worker/job_worker.py"
    )


if __name__ == "__main__":
    main()
