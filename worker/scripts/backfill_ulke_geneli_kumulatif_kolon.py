"""EPP — 2026-09-08, Aşama 3 (batch bağımlılığı düzeltmesi, migration
20260908_0002): mevcut 6 Excel batch'inin (202601-202606, `excel-ulke-
geneli-v1`, batch_id 591-596) AKTİF satırlarına, o batch'ler oluşturulduğunda
HENÜZ VAR OLMAYAN `kumulatif_tuketim_mwh` kolonunu doldurur.

**Neden bu ayrı bir tek seferlik script (migration'ın İÇİNDE DEĞİL):**
`tuketim_mwh` (aylık, türetilen) değerleri zaten DOĞRU ve DEĞİŞMİYOR — bu
`worker/scripts/adim3_madde1_reverify_driver.py`(scratchpad, disposable
postgres:17) ile BAĞIMSIZ olarak kanıtlandı: 6 ayın 30 satırı da, YENİ
kod yoluyla (onceki_ay_kumulatif_ulke_geneli_getir + kumulatif_tuketim_mwh
kolonu) sıfırdan yeniden işlendiğinde CANLIDAKİ değerlerle ondalık basamağa
kadar BİREBİR eşleşti. Yalnız EKSİK olan, o zaman henüz var olmayan ham
kümülatif değer — bu script SADECE onu, AYNI kaynak dosyalardan (T11'in
Genel Toplam satırı) okuyup UPDATE eder; `tuketim_mwh`'ye, batch kimliğine
(ingestion_batch_id) ya da is_active'e DOKUNMAZ. Migration'lar şema-only
kalır (proje konvansiyonu) — veri operasyonu ayrı script'te.

Kullanım: python -m worker.scripts.backfill_ulke_geneli_kumulatif_kolon [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import openpyxl
import psycopg

from worker import parser as parser_mod
from worker.db import get_database_url
from worker.pipeline import _sayfa
from worker.scripts.backfill_ulke_geneli_excel import MANIFEST


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        for tarih_id, yol in sorted(MANIFEST.items()):
            if not yol.exists():
                print(f"[ATLA] {tarih_id}: dosya bulunamadı: {yol}")
                continue
            wb = openpyxl.load_workbook(yol, data_only=True)
            ws11 = _sayfa(wb, 11)
            kumulatif = parser_mod.tablo11_genel_toplam_satiri_oku(ws11)
            print(f"{tarih_id}: {kumulatif}")

            if args.dry_run:
                continue

            with conn.cursor() as cur:
                for grup, deger in kumulatif.items():
                    cur.execute(
                        """
                        UPDATE fact_tuketim_ulke_geneli ftu
                        SET kumulatif_tuketim_mwh = %s
                        FROM dim_tuketici_grubu dg
                        JOIN ingestion_batch ib ON ib.parser_version = 'excel-ulke-geneli-v1'
                        WHERE ftu.grup_id = dg.grup_id
                          AND ftu.ingestion_batch_id = ib.batch_id
                          AND dg.grup_adi = %s
                          AND ftu.tarih_id = %s
                          AND ftu.is_active = true
                          AND ftu.kumulatif_tuketim_mwh IS NULL
                        """,
                        (deger, grup, tarih_id),
                    )
                    if cur.rowcount != 1:
                        raise RuntimeError(
                            f"{tarih_id}/{grup}: beklenen 1 satır güncellendi, "
                            f"{cur.rowcount} güncellendi (zaten dolu mu, "
                            "yoksa aktif satır mı yok?)"
                        )
            conn.commit()
            print(f"  -> {tarih_id}: 5 satır güncellendi (commit edildi)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
