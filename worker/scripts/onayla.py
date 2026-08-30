"""EPP — Faz 0/1 elle batch onayı: pipeline.batch_onayla()'yı ayrı bir süreçten
(shell/CLI) çağırmak için ince bir kabuk.

Neden gerekli: pipeline.batch_onayla() KASITLI OLARAK yalnız `batch_id: int`
alır, epdk_aylik_isle()'ın döndürdüğü IslemSonucu bellek nesnesini DEĞİL —
bu nesne (pandas DataFrame'ler içerir) bir Python process'i sonlandığında
kaybolur. `otomatik_onaya_uygun()` eşiği tutmadığında (gerçek bir örnek için
bkz. dokumanlar/06_canli_veri_operasyon_gunlugu.md) elle onay AYRI bir
terminal oturumunda/script çalıştırmasında verilir; elde yalnız batch_id
(tam sayı, DB'de zaten duruyor) kalır. Bu script o boşluğu resmi
pipeline.batch_onayla()'yı DOĞRUDAN çağırarak kapatır — aynı mantığı elle
yeniden yazmaya gerek kalmaz.

Kullanım:
    python -m worker.scripts.onayla --batch-id 3

DATABASE_URL ortam değişkeninden okunur (worker/db.py load_dotenv() ile
.env'i otomatik yükler).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from worker import pipeline
from worker.db import get_database_url  # import yan etkisi: .env yüklenir


def main() -> int:
    ap = argparse.ArgumentParser(
        description="EPP: bir batch'i elle onayla (pipeline.batch_onayla())"
    )
    ap.add_argument("--batch-id", required=True, type=int)
    args = ap.parse_args()

    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    with psycopg.connect(database_url) as conn:
        aktive_edilen = pipeline.batch_onayla(conn, args.batch_id)
        conn.commit()

    if aktive_edilen:
        print(
            f"[OK] batch_id={args.batch_id} aktive edildi: {', '.join(aktive_edilen)}"
        )
    else:
        print(
            f"[UYARI] batch_id={args.batch_id} hiçbir tabloya veri yazmamış "
            "(tümü reddedildi/karantinada) - hiçbir tablo aktive edilmedi, "
            "batch yine de 'succeeded' işaretlendi."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
