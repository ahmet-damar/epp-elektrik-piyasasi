"""
EPP — Veri doğrulama scripti.
Yüklenen 81 il verisinin EPDK resmi toplamlarıyla tutarlılığını kontrol eder.
Çalıştırma:  python worker/dogrula.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from tr_ocak2026 import TABLO11, TABLO2_KAYNAK  # noqa: E402

# EPDK raporundaki resmi Türkiye toplamları
RESMI = {
    "toplam_tuketim": 26148333.994,   # Tablo 7/11 Genel Toplam
    "toplam_uretim": 31259275.117,    # Tablo 2 TOPLAM
    "sanayi_iletim": 6704748.400,     # Tablo 11 Sanayi-İLETİM toplam
}


def main() -> int:
    print("=" * 60)
    print("EPP — VERİ DOĞRULAMA · EPDK Ocak 2026 (81 İl)")
    print("=" * 60)

    # Hesapla
    toplam_tuketim = sum(sum(r[1:]) for r in TABLO11)
    toplam_uretim = sum(u for _, u, _ in TABLO2_KAYNAK)
    yenilenebilir = sum(u for _, u, y in TABLO2_KAYNAK if y)
    sanayi_iletim = sum(r[5] for r in TABLO11)  # index 5 = sanayi_iletim

    print(f"\n  İl sayısı           : {len(TABLO11)}")
    print(f"  Toplam tüketim      : {toplam_tuketim:>16,.0f} MWh")
    print(f"  Toplam üretim       : {toplam_uretim:>16,.0f} MWh")
    print(f"  Yenilenebilir payı  : %{yenilenebilir/toplam_uretim*100:.1f}")
    print(f"  Sanayi-İletim (P0-2): {sanayi_iletim:>16,.0f} MWh")

    print("\n  EPDK RESMİ TOPLAMLA KARŞILAŞTIRMA (±%0,5):")
    tum_ok = True
    for ad, got, want in [
        ("Toplam tüketim", toplam_tuketim, RESMI["toplam_tuketim"]),
        ("Toplam üretim", toplam_uretim, RESMI["toplam_uretim"]),
        ("Sanayi-İletim", sanayi_iletim, RESMI["sanayi_iletim"]),
    ]:
        sapma = abs(got - want) / want * 100
        ok = sapma <= 0.5
        tum_ok = tum_ok and ok
        isaret = "OK" if ok else "XX"
        print(f"    [{isaret}] {ad:16s} hesap={got:,.0f}  resmi={want:,.0f}  sapma=%{sapma:.3f}")

    print("\n" + "=" * 60)
    if tum_ok:
        print("SONUC: [BASARILI] 81 IL VERISI EPDK RESMI TOPLAMLARIYLA TUTUYOR")
    else:
        print("SONUC: [HATA] Sapma tespit edildi")
    print("=" * 60)
    return 0 if tum_ok else 1


if __name__ == "__main__":
    sys.exit(main())
