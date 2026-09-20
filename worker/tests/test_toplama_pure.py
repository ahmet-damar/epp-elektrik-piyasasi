"""EPP — `worker/toplama.py`'nin DB gerektirmeyen (salt aritmetik)
fonksiyonlarının testi. (`Claude outputs/PROMPT_TOPLAMA_KATMANI_2026-09-19.md`)"""

from __future__ import annotations

import pytest

from worker import toplama


def test_dikis_araligi_iki_tarafi_da_kapsiyorsa_true() -> None:
    """Madde 8 — 2025→2026 dikişi: aralık HER İKİ tarafı da içeriyorsa
    (örn. 2025-06'dan 2026-06'ya) True dönmeli."""
    assert toplama.donem_araligi_dikis_iceriyor_mu(202506, 202606) is True


def test_dikis_araligi_yalniz_2025_ise_false() -> None:
    assert toplama.donem_araligi_dikis_iceriyor_mu(202501, 202512) is False


def test_dikis_araligi_yalniz_2026_ise_false() -> None:
    assert toplama.donem_araligi_dikis_iceriyor_mu(202601, 202612) is False


def test_dikis_araligi_tam_sinirda() -> None:
    """202512/202601 sınırının KENDİSİ — dahil olmalı (<=/>=), aralık
    tam dikişin iki ucunu kapsıyor."""
    assert toplama.donem_araligi_dikis_iceriyor_mu(202512, 202601) is True


def test_grain_dogrula_bilinmeyen_deger_hata_verir() -> None:
    with pytest.raises(ValueError):
        toplama._grain_dogrula("ay_yarim")  # type: ignore[arg-type]


def test_tarih_araligina_ayir_yillik_tarih_id_reddedilir() -> None:
    """Toplama katmanı yalnız AYLIK tarih_id kabul eder — YYYY00
    (yıllık) girdisi tanımsız, açıkça reddedilmeli."""
    with pytest.raises(ValueError):
        toplama._tarih_araligina_ayir(202400, 202412)


def test_ay_ekle_yil_devrini_dogru_isler() -> None:
    assert toplama._ay_ekle(202412, 1) == 202501
    assert toplama._ay_ekle(202501, -11) == 202402
