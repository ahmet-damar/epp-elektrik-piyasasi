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
    gecen_yil = pd.read_csv(INPUT / "tuketim_gecen_yil.csv")
    toplam_gecen_yil = float(gecen_yil["toplam_tuketim_mwh"].iloc[0])

    toplam_tuketim = kpi.kpi_08_toplam_tuketim(tuketim)

    return {
        "KPI-01": kpi.kpi_01_kurulu_guc(uretim),
        "KPI-02": kpi.kpi_02_toplam_uretim(uretim),
        "KPI-03": kpi.kpi_03_yenilenebilir_pay(uretim),
        "KPI-06": kpi.kpi_06_hhi(uretim),
        "KPI-08": toplam_tuketim,
        "KPI-09_mesken": kpi.kpi_09_grup_payi(tuketim, "Mesken"),
        "KPI-10_mesken": kpi.kpi_10_abone_basi(tuketim, abone, "Mesken"),
        "KPI-13_yoy": kpi.kpi_13_yoy(toplam_tuketim, toplam_gecen_yil),
        "KPI-23_hdd": kpi.kpi_23_hdd(hava),
        "KPI-24_cdd": kpi.kpi_24_cdd(hava),
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
