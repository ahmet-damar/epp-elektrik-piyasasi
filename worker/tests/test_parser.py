"""EPP — Parser testleri (worker/parser.py).

Gerçek EPDK dosyası henüz repoda yok (dokumanlar/05_...: "v0.1 — Faz 0'da
gerçek 2016+ dosyalarla doğrulanacak"). Bu yüzden dokümandaki anchor/kolon
sözleşmesini birebir uygulayan SENTETİK bir xlsx üretip parser'ı ona karşı
test ediyoruz; uçtan uca doğruluğu da worker/tests/golden/ ile aynı
Eskişehir 202601 değerleriyle worker/kpi.py üzerinden çapraz kontrol ediyoruz.
"""

from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from worker import kpi, parser

GOLDEN_BEKLENEN = Path(__file__).parent / "golden" / "expected" / "kpi_expected.json"


def _sentetik_workbook() -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    t1 = wb.create_sheet("Tablo 1")
    t1.append(["Tablo 1 - Lisanslı Kurulu Güç (MWe)"])
    t1.append(["İLLER", "Doğal Gaz", "Rüzgar", "Güneş", "Hidrolik", "Linyit"])
    t1.append(["Eskişehir", 900.0, 300.0, 150.0, 200.0, 450.0])
    t1.append(["TÜRKİYE", 900.0, 300.0, 150.0, 200.0, 450.0])

    t2 = wb.create_sheet("Tablo 2")
    t2.append(["Tablo 2 - Lisanslı Üretim (MWh)"])
    t2.append(["İLLER", "Doğal Gaz", "Rüzgar", "Güneş", "Hidrolik", "Linyit"])
    t2.append(["Eskişehir", 400000.0, 120000.0, 30000.0, 80000.0, 250000.0])
    t2.append(["TÜRKİYE", 400000.0, 120000.0, 30000.0, 80000.0, 250000.0])

    t9 = wb.create_sheet("Tablo 9")
    t9.append(["Tablo 9 - Tüketici Sayısı"])
    t9.append(
        [
            "İLLER",
            "Aydınlatma",
            "Kamu ve Özel Hizmetler",
            "Mesken",
            "Sanayi",
            "Tarımsal Faaliyetler",
        ]
    )
    t9.append(["Eskişehir", 300, 4000, 250000, 1200, 800])
    t9.append(["TÜRKİYE", 300, 4000, 250000, 1200, 800])

    t11 = wb.create_sheet("Tablo 11")
    t11.append(["Tablo 11 - Tüketim (İletim/Dağıtım)"])
    t11.append(
        [
            "İLLER",
            "Aydınlatma",
            "Kamu ve Özel Hizmetler",
            "Mesken",
            "Sanayi-DAĞITIM",
            "Sanayi-İLETİM",
            "Tarımsal Faaliyetler",
        ]
    )
    # Turkce metin formati (nokta binlik, virgul ondalik) - parse_sayi metin dalini test eder
    t11.append(
        [
            "Eskişehir",
            "5.000,00",
            "60.000,00",
            "120.000,00",
            "90.000,00",
            "150.000,00",
            "20.000,00",
        ]
    )
    t11.append(
        [
            "TÜRKİYE",
            "5.000,00",
            "60.000,00",
            "120.000,00",
            "90.000,00",
            "150.000,00",
            "20.000,00",
        ]
    )

    t4 = wb.create_sheet("Tablo 4")
    t4.append(["Tablo 4 - Lisanssız Kurulu Güç (MWe)"])
    t4.append(["İLLER", "Güneş", "Rüzgar"])
    t4.append(["Eskişehir", 50.0, 10.0])
    t4.append(["TÜRKİYE", 50.0, 10.0])

    t5 = wb.create_sheet("Tablo 5")
    t5.append(["Tablo 5 - Lisanssız Üretim (MWh)"])
    t5.append(["İLLER", "Güneş", "Rüzgar"])
    t5.append(["Eskişehir", 5000.0, 1000.0])
    t5.append(["TÜRKİYE", 5000.0, 1000.0])

    t7 = wb.create_sheet("Tablo 7")
    t7.append(["Tablo 7 - Faturalanan Tüketim (Tür)"])
    t7.append(
        [
            "İLLER",
            "Aydınlatma",
            "Kamu ve Özel Hizmetler",
            "Mesken",
            "Sanayi",
            "Tarımsal Faaliyetler",
        ]
    )
    t7.append(["Eskişehir", 5000.0, 60000.0, 120000.0, 240000.0, 20000.0])
    t7.append(["TÜRKİYE", 5000.0, 60000.0, 120000.0, 240000.0, 20000.0])

    return wb


@pytest.fixture(scope="module")
def wb() -> openpyxl.Workbook:
    return _sentetik_workbook()


def test_tablo11_p0_2_ayri_satir(wb: openpyxl.Workbook) -> None:
    df = parser.tablo11_tuketim_oku(wb["Tablo 11"], 202601, "Tablo 11")
    assert len(df) == 6
    sanayi = df[df["grup"] == "Sanayi"]
    assert set(sanayi["baglanti"]) == {"iletim", "dagitim"}
    iletim = sanayi.loc[sanayi["baglanti"] == "iletim", "tuketim_mwh"].iloc[0]
    dagitim = sanayi.loc[sanayi["baglanti"] == "dagitim", "tuketim_mwh"].iloc[0]
    assert iletim == pytest.approx(150000.0)
    assert dagitim == pytest.approx(90000.0)
    assert df["il_kodu"].iloc[0] == 26  # Eskişehir plakası


def test_kaynak_matrisi_ve_birlestirme(wb: openpyxl.Workbook) -> None:
    kurulu = parser.tablo1_kurulu_guc_oku(wb["Tablo 1"], 202601, "Tablo 1")
    uretim_mwh = parser.tablo23_uretim_oku(wb["Tablo 2"], 202601, "Tablo 2")
    uretim = parser.uretim_birlestir(kurulu, uretim_mwh)

    assert len(uretim) == 5
    hidrolik = uretim[uretim["kaynak"] == "Hidrolik"].iloc[0]
    assert hidrolik["kurulu_guc_mw"] == pytest.approx(200.0)
    assert hidrolik["uretim_mwh"] == pytest.approx(80000.0)
    assert bool(hidrolik["yenilenebilir"]) is True

    dogal_gaz = uretim[uretim["kaynak"] == "Doğal Gaz"].iloc[0]
    assert bool(dogal_gaz["yenilenebilir"]) is False


def test_abone_matrisi(wb: openpyxl.Workbook) -> None:
    df = parser.tablo_abone_oku(wb["Tablo 9"], 202601, "Tablo 9")
    assert len(df) == 5
    mesken = df[df["grup"] == "Mesken"].iloc[0]
    assert mesken["abone_sayisi"] == pytest.approx(250000.0)


def test_lisanssiz_uretim_ve_birlestirme(wb: openpyxl.Workbook) -> None:
    kurulu = parser.tablo4_lisanssiz_kurulu_guc_oku(wb["Tablo 4"], 202601, "Tablo 4")
    uretim_mwh = parser.tablo56_lisanssiz_uretim_oku(wb["Tablo 5"], 202601, "Tablo 5")
    assert (kurulu["lisans"] == "Lisanssız").all()
    lisanssiz = parser.uretim_birlestir(kurulu, uretim_mwh)
    assert len(lisanssiz) == 2
    gunes = lisanssiz[lisanssiz["kaynak"] == "Güneş"].iloc[0]
    assert gunes["kurulu_guc_mw"] == pytest.approx(50.0)
    assert gunes["uretim_mwh"] == pytest.approx(5000.0)

    lisansli_kurulu = parser.tablo1_kurulu_guc_oku(wb["Tablo 1"], 202601, "Tablo 1")
    lisansli_uretim = parser.tablo23_uretim_oku(wb["Tablo 2"], 202601, "Tablo 2")
    lisansli = parser.uretim_birlestir(lisansli_kurulu, lisansli_uretim)

    tumu = pd.concat([lisansli, lisanssiz], ignore_index=True)
    assert kpi.kpi_02_toplam_uretim(tumu) == pytest.approx(886000.0)
    assert kpi.kpi_07_lisanssiz_pay(tumu) == pytest.approx(
        round(6000.0 / 886000.0 * 100, 1)
    )


def test_faturalanan_tuketim_tur_tablosu(wb: openpyxl.Workbook) -> None:
    df = parser.tablo7_faturalanan_tur_oku(wb["Tablo 7"], 202601)
    assert len(df) == 5  # Sanayi ayrımsız TEK satır (T11'in aksine)
    assert (df["baglanti"] == "dagitim").all()
    sanayi = df[df["grup"] == "Sanayi"].iloc[0]
    assert sanayi["tuketim_mwh"] == pytest.approx(240000.0)


def test_ucdan_uca_golden_kpi_ile_esler(wb: openpyxl.Workbook) -> None:
    """Parser çıktısı → kpi.py doğrulama+hesap → golden/expected/kpi_expected.json."""
    kurulu = parser.tablo1_kurulu_guc_oku(wb["Tablo 1"], 202601, "Tablo 1")
    uretim_mwh = parser.tablo23_uretim_oku(wb["Tablo 2"], 202601, "Tablo 2")
    uretim = kpi.dogrula_uretim(parser.uretim_birlestir(kurulu, uretim_mwh)).kabul
    abone = kpi.dogrula_abone(
        parser.tablo_abone_oku(wb["Tablo 9"], 202601, "Tablo 9")
    ).kabul
    tuketim = kpi.dogrula_tuketim(
        parser.tablo11_tuketim_oku(wb["Tablo 11"], 202601, "Tablo 11")
    ).kabul

    with GOLDEN_BEKLENEN.open(encoding="utf-8") as f:
        beklenen = json.load(f)

    assert kpi.kpi_01_kurulu_guc(uretim) == pytest.approx(beklenen["KPI-01"])
    assert kpi.kpi_02_toplam_uretim(uretim) == pytest.approx(beklenen["KPI-02"])
    assert kpi.kpi_03_yenilenebilir_pay(uretim) == pytest.approx(
        beklenen["KPI-03"], rel=0.005
    )
    assert kpi.kpi_06_hhi(uretim) == pytest.approx(beklenen["KPI-06"], rel=0.005)
    assert kpi.kpi_08_toplam_tuketim(tuketim) == pytest.approx(beklenen["KPI-08"])
    assert kpi.kpi_09_grup_payi(tuketim, "Mesken") == pytest.approx(
        beklenen["KPI-09_mesken"], rel=0.005
    )
    assert kpi.kpi_10_abone_basi(tuketim, abone, "Mesken") == pytest.approx(
        beklenen["KPI-10_mesken"]
    )
    p0_2 = kpi.p0_2_sanayi(tuketim)
    for alan, deger in beklenen["P0-2"].items():
        assert p0_2[alan] == pytest.approx(deger, rel=0.005)


@pytest.mark.parametrize(
    ("girdi", "beklenen"),
    [
        ("1.432,404", 1432.404),
        ("0,5", 0.5),
        ("", None),
        ("-", None),
        (None, None),
        (1200, 1200.0),
        (1200.5, 1200.5),
    ],
)
def test_parse_sayi(girdi: object, beklenen: float | None) -> None:
    sonuc = parser.parse_sayi(girdi)
    if beklenen is None:
        assert sonuc is None
    else:
        assert sonuc == pytest.approx(beklenen)


def test_normalize_label_turkce_sadelestirme() -> None:
    assert parser.normalize_label("Sanayi-İLETİM") == "SANAYI-ILETIM"
    assert parser.normalize_label("  Eskişehir  ") == "ESKISEHIR"
    assert parser.normalize_label(None) == ""


def test_il_kodu_bul() -> None:
    assert parser.il_kodu_bul("Eskişehir") == 26
    assert parser.il_kodu_bul("eskisehir") == 26
    assert parser.il_kodu_bul("Bilinmeyen İl XYZ") is None


def test_kaynak_esle() -> None:
    assert parser.kaynak_esle("Akarsu") == ("Hidrolik", True)
    assert parser.kaynak_esle("Barajlı") == ("Hidrolik", True)
    assert parser.kaynak_esle("İthal Kömür") == ("İthal Kömür", False)
    assert parser.kaynak_esle("Uzay Enerjisi") is None


def test_eksik_tablolari_bul() -> None:
    mevcut_sayfalar = ["Tablo 1", "Tablo 2", "Tablo 9", "Tablo 11"]
    gerekli = [f"Tablo {n}" for n in range(1, 14)]
    eksik = parser.eksik_tablolari_bul(mevcut_sayfalar, gerekli)
    assert eksik == [
        "Tablo 3",
        "Tablo 4",
        "Tablo 5",
        "Tablo 6",
        "Tablo 7",
        "Tablo 8",
        "Tablo 10",
        "Tablo 12",
        "Tablo 13",
    ]


def test_mutabakat_kontrol() -> None:
    assert parser.mutabakat_kontrol(1000.0, 1004.0) is True  # %0.4 sapma
    assert parser.mutabakat_kontrol(1000.0, 1010.0) is False  # %1.0 sapma
    assert parser.mutabakat_kontrol(0.0, 0.0) is True
