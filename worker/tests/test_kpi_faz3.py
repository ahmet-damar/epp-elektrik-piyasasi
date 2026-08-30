"""EPP — Faz 3 (hava normalizasyonu) worker/kpi.py saf fonksiyon testleri.

DB gerektirmez — worker/analytics.py'nin DB'den çekip bu fonksiyonlara
geçireceği şekilde sentetik DataFrame'ler kurulur.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from worker import kpi


def test_beta_gamma_tahmin_et_bilinen_dogrusal_iliski() -> None:
    """tuketim = 1000 + 5*hdd + 3*cdd (gürültüsüz) - OLS tam katsayıları
    kurtarmalı (β≈5, γ≈3)."""
    rng = np.random.default_rng(42)
    hdd = rng.uniform(0, 500, 24)
    cdd = rng.uniform(0, 300, 24)
    tuketim = 1000 + 5 * hdd + 3 * cdd
    gecmis = pd.DataFrame({"tuketim_mwh": tuketim, "hdd": hdd, "cdd": cdd})

    sonuc = kpi.beta_gamma_tahmin_et(gecmis)
    assert sonuc is not None
    beta, gamma, sabit = sonuc
    assert beta == pytest.approx(5.0)
    assert gamma == pytest.approx(3.0)
    assert sabit == pytest.approx(1000.0)


def test_beta_gamma_tahmin_et_yetersiz_gozlem_hesaplanamaz() -> None:
    gecmis = pd.DataFrame(
        {"tuketim_mwh": [100.0, 110.0], "hdd": [10.0, 12.0], "cdd": [0.0, 0.0]}
    )
    assert kpi.beta_gamma_tahmin_et(gecmis, min_gozlem=12) is None


def test_beta_gamma_tahmin_et_bos_dataframe() -> None:
    assert (
        kpi.beta_gamma_tahmin_et(pd.DataFrame(columns=["tuketim_mwh", "hdd", "cdd"]))
        is None
    )


def test_hava_normu_hesapla_ortalama() -> None:
    seri = pd.DataFrame({"hdd": [100.0] * 9 + [200.0], "cdd": [10.0] * 10})
    sonuc = kpi.hava_normu_hesapla(seri, yil_sayisi=10)
    assert sonuc is not None
    hdd_norm, cdd_norm = sonuc
    assert hdd_norm == pytest.approx(110.0)
    assert cdd_norm == pytest.approx(10.0)


def test_hava_normu_hesapla_yetersiz_yil_hesaplanamaz() -> None:
    seri = pd.DataFrame({"hdd": [100.0] * 5, "cdd": [10.0] * 5})
    assert kpi.hava_normu_hesapla(seri, yil_sayisi=10) is None


def test_tuketim_normu_hesapla_ortalama() -> None:
    seri = pd.Series([100.0, 200.0, 300.0, 400.0, 500.0])
    assert kpi.tuketim_normu_hesapla(seri, yil_sayisi=5) == pytest.approx(300.0)


def test_tuketim_normu_hesapla_yetersiz_yil_hesaplanamaz() -> None:
    seri = pd.Series([100.0, 200.0])
    assert kpi.tuketim_normu_hesapla(seri, yil_sayisi=5) is None


def test_kpi_11_arindirilmis_tuketim() -> None:
    # gerçek=1000, hdd=120 (norm=100, +20 fazla ısıtma ihtiyacı), beta=2 -> -40
    # cdd=50 (norm=50, fark yok), gamma=1 -> 0
    sonuc = kpi.kpi_11_arindirilmis_tuketim(
        tuketim_mwh=1000.0,
        hdd=120.0,
        cdd=50.0,
        hdd_norm=100.0,
        cdd_norm=50.0,
        beta=2.0,
        gamma=1.0,
    )
    assert sonuc == pytest.approx(960.0)


def test_kpi_12_norm_sapmasi() -> None:
    assert kpi.kpi_12_norm_sapmasi(
        arindirilmis=1100.0, tuketim_norm=1000.0
    ) == pytest.approx(10.0)
    assert kpi.kpi_12_norm_sapmasi(arindirilmis=1000.0, tuketim_norm=None) is None
    assert kpi.kpi_12_norm_sapmasi(arindirilmis=1000.0, tuketim_norm=0.0) is None


def test_kpi_cagr_bilinen_ornek() -> None:
    # dokumanlar/04_kpi_sozlesmeleri.md örneği: 2021->2025, n=4
    ilk, son, n = 100.0, 146.4, 4
    sonuc = kpi.kpi_cagr(ilk, son, n)
    assert sonuc is not None
    assert sonuc == pytest.approx(10.0, abs=0.1)  # ~%10 yıllık büyüme


def test_kpi_cagr_kenar_durumlar() -> None:
    assert kpi.kpi_cagr(None, 100.0, 4) is None
    assert kpi.kpi_cagr(100.0, None, 4) is None
    assert kpi.kpi_cagr(0.0, 100.0, 4) is None  # ilk<=0
    assert kpi.kpi_cagr(-10.0, 100.0, 4) is None  # ilk<0
    assert kpi.kpi_cagr(100.0, 110.0, 0) is None  # n<=0
