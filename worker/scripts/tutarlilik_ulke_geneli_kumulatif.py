"""EPP — fact_tuketim_ulke_geneli kümülatif-bağımlılık tutarlılık kontrolü
(2026-09-08, Aşama 3 — batch bağımlılığı düzeltmesi).

**Neden bu script var:** `ingest.onceki_ay_kumulatif_ulke_geneli_getir()`,
ay N'nin AYLIK değerini türetirken ay N-1'in O ANDA kayıtlı kümülatif
değerini kullanır (bkz. worker/pipeline.py:isle_ay_ulke_geneli_excel()).
Eğer N-1 SONRADAN başka bir batch'le (düzeltilmiş bir kümülatif değerle)
aktive edilirse, N'nin halihazırda kayıtlı `tuketim_mwh` değeri artık N-1'in
GÜNCEL aktif kümülatifinden türetilmemiş olur — bu SESSİZCE olur, çünkü N'nin
satırı hiç yeniden yazılmaz. Bu script bu durumu AÇIKÇA yakalar: her aktif
Excel ayı (kumulatif_tuketim_mwh IS NOT NULL) için, kayıtlı aylık değerin
"kendi kümülatifi − bir önceki ayın GÜNCEL aktif kümülatifi" ile hâlâ
eşleştiğini doğrular.

**Ne YAPMAZ:** otomatik düzeltme yapmaz, hiçbir satırı değiştirmez —
yalnız tutarsızlığı raporlar (exit code 1). Düzeltme, ilgili ayın
pipeline'ının yeniden çalıştırılıp yeni bir batch olarak aktive edilmesiyle
yapılır (mevcut batch/is_active deseninin dışına çıkılmaz).

Kalıcı, tekrar çalıştırılabilir bir script — `mutabakat_ulke_geneli.py` ile
AYNI CLI deseni (main() -> int, exit code 0=tutarlı, 1=tutarsız bulundu)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg

from worker.db import get_database_url

TOLERANS_ORAN = 0.005
TOLERANS_MIN_MWH = 1.0


def tutarlilik_kontrol_et(
    conn: psycopg.Connection,
    *,
    tolerans_oran: float = TOLERANS_ORAN,
    tolerans_min_mwh: float = TOLERANS_MIN_MWH,
) -> list[dict]:
    """Her AKTİF (is_active=true) `fact_tuketim_ulke_geneli` satırı için
    (yalnız `kumulatif_tuketim_mwh IS NOT NULL` olanlar — Excel ayları),
    kayıtlı `tuketim_mwh`'nin, "kendi kümülatifi − bir önceki ayın GÜNCEL
    aktif kümülatifi" ile hâlâ eşleştiğini doğrular.

    Döner: `detaylar` — her satır için hesaplama detayı, `tutarli` alanı
    False olanlar N-1'in aktivasyondan sonra değiştiğini (veya hiç aktif
    N-1 kalmadığını) gösterir. Yılın ilk ayı (referans kümülatif 0 sayılır)
    ve N-1'in kendisi hiç Excel/kümülatif kaydı değilse (örn. Word'den
    Excel'e geçiş sınırı, 202601 gibi) otomatik `tutarli=True` sayılır —
    bunlar tasarım gereği kümülatif zincirin dışında kalır."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ftu.tarih_id, dg.grup_adi, ftu.tuketim_mwh,
                   ftu.kumulatif_tuketim_mwh, ftu.ingestion_batch_id
            FROM fact_tuketim_ulke_geneli ftu
            JOIN dim_tuketici_grubu dg ON dg.grup_id = ftu.grup_id
            WHERE ftu.is_active = true AND ftu.kumulatif_tuketim_mwh IS NOT NULL
            ORDER BY ftu.tarih_id, dg.grup_adi
            """
        )
        satirlar = cur.fetchall()

        cur.execute(
            """
            SELECT ftu.tarih_id, dg.grup_adi, ftu.kumulatif_tuketim_mwh
            FROM fact_tuketim_ulke_geneli ftu
            JOIN dim_tuketici_grubu dg ON dg.grup_id = ftu.grup_id
            WHERE ftu.is_active = true AND ftu.kumulatif_tuketim_mwh IS NOT NULL
            """
        )
        aktif_kumulatif: dict[tuple[int, str], float] = {
            (tarih_id, grup): float(deger) for tarih_id, grup, deger in cur.fetchall()
        }

    detaylar: list[dict] = []
    for tarih_id, grup, aylik, kendi_kumulatif, batch_id in satirlar:
        aylik = float(aylik)
        kendi_kumulatif = float(kendi_kumulatif)
        ay = tarih_id % 100
        if ay == 1:  # yılın ilk ayı — referans kümülatif 0 sayılır (tasarım gereği)
            detaylar.append(
                {
                    "tarih_id": tarih_id,
                    "grup": grup,
                    "durum": "yilin_ilk_ayi",
                    "tutarli": True,
                }
            )
            continue

        onceki_tarih_id = tarih_id - 1
        onceki_aktif_kumulatif = aktif_kumulatif.get((onceki_tarih_id, grup))
        if onceki_aktif_kumulatif is None:
            # N-1 hiç aktif/kümülatifli bir Excel ayı değil (örn. Word/Excel
            # sınırı, 202601 gibi) — kümülatif zincirin dışında, tasarım gereği.
            detaylar.append(
                {
                    "tarih_id": tarih_id,
                    "grup": grup,
                    "durum": "onceki_ay_kumulatifsiz",
                    "tutarli": True,
                }
            )
            continue

        beklenen_aylik = kendi_kumulatif - onceki_aktif_kumulatif
        fark = abs(beklenen_aylik - aylik)
        tolerans = max(tolerans_min_mwh, abs(kendi_kumulatif) * tolerans_oran)
        tutarli = fark <= tolerans
        detaylar.append(
            {
                "tarih_id": tarih_id,
                "grup": grup,
                "batch_id": batch_id,
                "kendi_kumulatif": kendi_kumulatif,
                "onceki_ay_guncel_aktif_kumulatif": onceki_aktif_kumulatif,
                "kayitli_aylik": aylik,
                "beklenen_aylik": beklenen_aylik,
                "fark": fark,
                "tutarli": tutarli,
            }
        )

    return detaylar


def main() -> int:
    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1
    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        detaylar = tutarlilik_kontrol_et(conn)
    tutarsizlar = [d for d in detaylar if not d.get("tutarli", True)]
    print(f"Kontrol edilen (tarih_id, grup) çifti: {len(detaylar)}")
    print(f"Tutarlı: {len(detaylar) - len(tutarsizlar)}, tutarsız: {len(tutarsizlar)}")
    for d in tutarsizlar:
        print(
            "  [TUTARSIZ]",
            f"tarih_id={d['tarih_id']} grup={d['grup']} batch_id={d['batch_id']}"
            f" kayıtlı_aylık={d['kayitli_aylik']:.3f}"
            f" beklenen_aylık={d['beklenen_aylik']:.3f}"
            f" (önceki ayın GÜNCEL aktif kümülatifi değişmiş olabilir —"
            f" bu ay yeniden işlenip aktive edilmeli)",
        )
    return 0 if not tutarsizlar else 1


if __name__ == "__main__":
    sys.exit(main())
