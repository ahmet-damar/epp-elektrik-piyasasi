"""EPP — worker/jobs/fetch_weather.py saf fonksiyon testleri (DB/ağ gerektirmez)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from worker.jobs import fetch_weather as fw


def test_hedef_tarih_id_normal_ay() -> None:
    assert fw._hedef_tarih_id(date(2026, 8, 30)) == 202607


def test_hedef_tarih_id_yil_basinda_gecen_yil_aralik() -> None:
    assert fw._hedef_tarih_id(date(2026, 1, 15)) == 202512


def test_ay_araligi_subat_artik_yil_degil() -> None:
    assert fw._ay_araligi(202602) == ("2026-02-01", "2026-02-28")


def test_ay_araligi_subat_artik_yil() -> None:
    assert fw._ay_araligi(202402) == ("2024-02-01", "2024-02-29")


def test_ay_araligi_aralik() -> None:
    assert fw._ay_araligi(202612) == ("2026-12-01", "2026-12-31")


def test_gunluk_degerler_none_degerleri_filtreler() -> None:
    gunluk = {"daily": {"temperature_2m_mean": [1.0, None, 3.0]}}
    assert fw._gunluk_degerler(gunluk, "temperature_2m_mean") == [1.0, 3.0]


def test_gunluk_degerler_anahtar_yoksa_bos_liste() -> None:
    assert fw._gunluk_degerler({"daily": {}}, "yok_boyle_bir_sey") == []


def test_aylik_ozet_cikar_tam_veri() -> None:
    gunluk = {
        "daily": {
            "temperature_2m_mean": [0.0, 10.0, 20.0],  # ort=10.0
            "shortwave_radiation_sum": [5.0, 5.0, 5.0],  # toplam=15.0
            "wind_speed_10m_mean": [2.0, 4.0, 6.0],  # ort=4.0
        }
    }
    ozet = fw._aylik_ozet_cikar(gunluk, hdd_baz_c=18.0, cdd_baz_c=22.0)
    assert ozet["t_ort"] == pytest.approx(10.0)
    # HDD = (18-0)+(18-10)+(18-20 -> 0) = 18+8+0 = 26
    assert ozet["hdd"] == pytest.approx(26.0)
    # CDD = (0-22->0)+(10-22->0)+(20-22->0) = 0
    assert ozet["cdd"] == pytest.approx(0.0)
    assert ozet["radyasyon"] == pytest.approx(15.0)
    assert ozet["ruzgar"] == pytest.approx(4.0)


def test_aylik_ozet_cikar_sicaklik_yoksa_hepsi_none() -> None:
    gunluk: dict[str, Any] = {"daily": {"temperature_2m_mean": []}}
    ozet = fw._aylik_ozet_cikar(gunluk, hdd_baz_c=18.0, cdd_baz_c=22.0)
    assert ozet == {
        "t_ort": None,
        "hdd": None,
        "cdd": None,
        "radyasyon": None,
        "ruzgar": None,
    }


def test_aylik_ozet_cikar_radyasyon_ruzgar_eksik_digerleri_dolu() -> None:
    """Open-Meteo bazı değişkenleri döndürmezse (ör. API değişikliği) t_ort/
    hdd/cdd yine hesaplanmalı, yalnız o alanlar None kalmalı."""
    gunluk = {"daily": {"temperature_2m_mean": [15.0, 25.0]}}
    ozet = fw._aylik_ozet_cikar(gunluk, hdd_baz_c=18.0, cdd_baz_c=22.0)
    assert ozet["t_ort"] == pytest.approx(20.0)
    assert ozet["radyasyon"] is None
    assert ozet["ruzgar"] is None
