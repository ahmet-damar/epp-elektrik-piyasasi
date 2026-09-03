"""EPP — Golden KPI testi (G-1). Kaynak: worker/tests/golden/.

SENTETİK Eskişehir 202601 verisiyle worker/kpi.py çıktısını
golden/expected/kpi_expected.json ile karşılaştırır.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from worker import kpi

GOLDEN = Path(__file__).parent / "golden"
INPUT = GOLDEN / "input"


@pytest.fixture(scope="module")
def beklenen() -> dict:
    with (GOLDEN / "expected" / "kpi_expected.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def hesaplanan() -> dict:
    tuketim = kpi.yukle_tuketim(INPUT / "tuketim.csv").kabul
    uretim = kpi.yukle_uretim(INPUT / "uretim.csv").kabul
    abone = kpi.yukle_abone(INPUT / "abone.csv").kabul
    hava = pd.read_csv(INPUT / "hava_gunluk.csv")
    # 2026-09-03: kpi_13_yoy() artık DataFrame'lerin kendisini alıyor (grup
    # kümesi karşılaştırması için) — bkz. worker/kpi.py modül notu.
    gecen_yil = pd.read_csv(INPUT / "tuketim_gecen_yil.csv")

    toplam_tuketim = kpi.kpi_08_toplam_tuketim(tuketim)

    return {
        "KPI-01": kpi.kpi_01_kurulu_guc(uretim),
        "KPI-02": kpi.kpi_02_toplam_uretim(uretim),
        "KPI-03": kpi.kpi_03_yenilenebilir_pay(uretim),
        "KPI-06": kpi.kpi_06_hhi(uretim),
        "KPI-08": toplam_tuketim,
        "KPI-09_mesken": kpi.kpi_09_grup_payi(tuketim, "Mesken"),
        "KPI-10_mesken": kpi.kpi_10_abone_basi(tuketim, abone, "Mesken"),
        "KPI-13_yoy": kpi.kpi_13_yoy(tuketim, gecen_yil),
        "KPI-23_hdd": kpi.kpi_23_hdd(hava, hdd_baz_c=18),
        "KPI-24_cdd": kpi.kpi_24_cdd(hava, cdd_baz_c=22),
        "P0-2": kpi.p0_2_sanayi(tuketim),
    }


SKALER_KPI = [
    "KPI-01",
    "KPI-02",
    "KPI-03",
    "KPI-06",
    "KPI-08",
    "KPI-09_mesken",
    "KPI-10_mesken",
    "KPI-13_yoy",
    "KPI-23_hdd",
    "KPI-24_cdd",
]


@pytest.mark.parametrize("anahtar", SKALER_KPI)
def test_golden_kpi(hesaplanan: dict, beklenen: dict, anahtar: str) -> None:
    assert hesaplanan[anahtar] == pytest.approx(beklenen[anahtar], rel=0.005)


def test_golden_p0_2_sanayi_ayrimi(hesaplanan: dict, beklenen: dict) -> None:
    for alan, deger in beklenen["P0-2"].items():
        assert hesaplanan["P0-2"][alan] == pytest.approx(deger, rel=0.005)


def test_bozuk_negatif_tuketim_reddedilir() -> None:
    sonuc = kpi.yukle_tuketim(INPUT / "BOZUK_negatif_tuketim.csv")
    assert len(sonuc.kabul) == 0
    assert len(sonuc.red) == 1


def test_bozuk_bilinmeyen_grup_karantinaya_alinir() -> None:
    sonuc = kpi.yukle_tuketim(INPUT / "BOZUK_bilinmeyen_grup.csv")
    assert len(sonuc.kabul) == 0
    assert len(sonuc.karantina) == 1
    assert len(sonuc.red) == 0


def test_kpi_04_kaynak_payi(hesaplanan: dict) -> None:
    # kpi_04 golden fixture'da yok (kpi_expected.json kapsamıyor); Ek B formülüyle elle doğrulanır.
    uretim = kpi.yukle_uretim(INPUT / "uretim.csv").kabul
    paylar = kpi.kpi_04_kaynak_payi(uretim)
    assert paylar is not None
    assert paylar == {
        "Doğal Gaz": 45.5,
        "Rüzgar": 13.6,
        "Güneş": 3.4,
        "Hidrolik": 9.1,
        "Linyit": 28.4,
    }
    assert sum(paylar.values()) == pytest.approx(100.0, abs=0.2)


def test_kpi_05_kapasite_faktoru(hesaplanan: dict) -> None:
    uretim = kpi.yukle_uretim(INPUT / "uretim.csv").kabul
    saat_ocak = 31 * 24
    assert kpi.kpi_05_kapasite_faktoru(uretim, saat_ocak) == pytest.approx(59.1)
    assert kpi.kpi_05_kapasite_faktoru(uretim, 0) is None


def test_kpi_05_uretim_mwh_hic_yoksa_hesaplanamaz(hesaplanan: dict) -> None:
    """Gerçek DB verisinde (aylık EPDK raporu, il×kaynak grain) uretim_mwh
    tamamen NULL'dır (bkz. migration 20260819_0005) - bu durumda 0/(kurulu*saat)
    gibi yanıltıcı bir %0.0 DEĞİL, 'hesaplanamaz' (None) dönmeli. Faz 2
    dashboard'unu gerçek dosyayla doğrularken bulunan gerçek bir hataydı."""
    uretim = kpi.yukle_uretim(INPUT / "uretim.csv").kabul.copy()
    uretim["uretim_mwh"] = pd.NA
    assert kpi.kpi_05_kapasite_faktoru(uretim, 31 * 24) is None


def test_kpi_07_lisanssiz_pay_lisans_kolonu_yoksa_sifir(hesaplanan: dict) -> None:
    uretim = kpi.yukle_uretim(INPUT / "uretim.csv").kabul
    assert kpi.kpi_07_lisanssiz_pay(uretim) == 0.0
