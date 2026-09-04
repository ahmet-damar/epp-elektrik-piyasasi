"""EPP — worker/kpi.py:esik_rengi() saf fonksiyon testleri (Görev 3, 2026-09-05).

DB gerektirmez.
"""

from __future__ import annotations

import pytest

from worker import kpi


def test_esik_rengi_yukselik_yesil() -> None:
    """yön=yukselik: değer >= yesil_alt → yeşil (örn. KPI-25, %+5 >= %+3)."""
    assert kpi.esik_rengi(5.0, yesil_alt=3.0, sari_alt=0.0, yon="yukselik") == "yesil"


def test_esik_rengi_yukselik_sari() -> None:
    assert kpi.esik_rengi(1.5, yesil_alt=3.0, sari_alt=0.0, yon="yukselik") == "sari"


def test_esik_rengi_yukselik_kirmizi() -> None:
    assert (
        kpi.esik_rengi(-2.0, yesil_alt=3.0, sari_alt=0.0, yon="yukselik") == "kirmizi"
    )


def test_esik_rengi_yukselik_sinir_degerleri_dahil() -> None:
    """Sınır değerleri (>=) İÇİNDE sayılmalı — tam yesil_alt yeşil, tam
    sari_alt sarı olmalı, "az farkla kırmızı" gibi bir sürpriz olmamalı."""
    assert kpi.esik_rengi(3.0, yesil_alt=3.0, sari_alt=0.0, yon="yukselik") == "yesil"
    assert kpi.esik_rengi(0.0, yesil_alt=3.0, sari_alt=0.0, yon="yukselik") == "sari"


def test_esik_rengi_alcelik_yesil() -> None:
    """yön=alcelik: değer <= yesil_alt → yeşil (örn. KPI-06 HHI, 0,10 <= 0,15)."""
    assert kpi.esik_rengi(0.10, yesil_alt=0.15, sari_alt=0.25, yon="alcelik") == "yesil"


def test_esik_rengi_alcelik_sari() -> None:
    assert kpi.esik_rengi(0.20, yesil_alt=0.15, sari_alt=0.25, yon="alcelik") == "sari"


def test_esik_rengi_alcelik_kirmizi() -> None:
    assert (
        kpi.esik_rengi(0.30, yesil_alt=0.15, sari_alt=0.25, yon="alcelik") == "kirmizi"
    )


def test_esik_rengi_deger_none_hesaplanamaz() -> None:
    """'hesaplanamaz' bir KPI'ye sahte bir renk üretilmemeli."""
    assert kpi.esik_rengi(None, yesil_alt=3.0, sari_alt=0.0, yon="yukselik") is None


def test_esik_rengi_bilinmeyen_yon_hata_verir() -> None:
    with pytest.raises(ValueError, match="Bilinmeyen yön"):
        kpi.esik_rengi(1.0, yesil_alt=3.0, sari_alt=0.0, yon="tuhaf")
