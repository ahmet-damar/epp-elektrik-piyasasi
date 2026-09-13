"""EPP — word_2020.py regresyon testleri (worker/scripts/word_2020.py).

worker/tests/test_word_2021.py ile AYNI yöntem (synthetic in-memory docx
tabloları, DATABASE_URL bağımsız). word_2020'ye özgü fark: ay/yıl
doğrulaması T11 başlığından değil KAPAK paragrafından yapılıyor, T10
tablosu TÜM yıl yapısal olarak il-ONLY.
"""

from __future__ import annotations

import pytest
from docx import Document

from worker.parser import _IL_ADI_KANONIK
from worker.scripts.word_2020 import (
    _ay_yil_dogrula_kapak,
    _il_adi_temizle,
    grup_esle_zorunlu,
    kaynak_esle_zorunlu,
    t2_oku,
    t3_oku,
    t4_oku,
    t10_oku,
    t11_oku,
)

TUM_ILLER = [_IL_ADI_KANONIK[kod] for kod in sorted(_IL_ADI_KANONIK)]
assert len(TUM_ILLER) == 81


def test_grup_esle_zorunlu_taksonomi_karari_baştan_uygulu() -> None:
    """2021/2022'de verilen taksonomi kararı (RENAME) 2020'ye baştan
    dahil edildi — ValueError FIRLAMAMALI."""
    assert grup_esle_zorunlu("Ticarethane") == "Kamu ve Özel Hizmetler"
    assert grup_esle_zorunlu("Tarımsal Sulama") == "Tarımsal"
    assert grup_esle_zorunlu("Aydınlatma") == "Aydınlatma"
    assert grup_esle_zorunlu("Genel Toplam") is None


def test_kaynak_esle_zorunlu_bilinen_kaynaklar() -> None:
    assert kaynak_esle_zorunlu("Hidrolik") is not None
    assert kaynak_esle_zorunlu("Toplam") is None


def test_il_adi_temizle_yildizli_ekleri_temizler() -> None:
    assert _il_adi_temizle("İstanbul") == "İstanbul"
    assert _il_adi_temizle("Adıyaman* ") == "Adıyaman"


def test_ay_yil_dogrula_kapak_normal_uyusma_gecer() -> None:
    """dokumanlar/08 — 2020'nin T11 başlığı ay/yıl İÇERMİYOR (2016'nın
    erken aylarındaki AYNI sorun), bu yüzden kapak paragrafından
    doğrulanıyor: '{Yıl} Yılı {Ay} Ayı Elektrik Piyasası Genel Görünümü'."""
    _ay_yil_dogrula_kapak(
        "2020 Yılı Haziran Ayı Elektrik Piyasası Genel Görünümü", "Haziran", 2020, ay=6
    )


def test_ay_yil_dogrula_kapak_uyusmazlik_reddedilir() -> None:
    with pytest.raises(ValueError, match="MANIFEST_2020 uyuşmazlığı"):
        _ay_yil_dogrula_kapak(
            "2020 Yılı Mayıs Ayı Elektrik Piyasası Genel Görünümü",
            "Haziran",
            2020,
            ay=6,
        )


def _tablo_ekle(satirlar: list[list[str]]):  # type: ignore[no-untyped-def]
    doc = Document()
    tbl = doc.add_table(rows=len(satirlar), cols=len(satirlar[0]))
    for i, satir in enumerate(satirlar):
        for j, deger in enumerate(satir):
            tbl.rows[i].cells[j].text = deger
    return tbl


def test_t11_oku_81_il_dogru_toplam_ve_sanayi_haric() -> None:
    baslik = [
        "İller",
        "Aydınlatma",
        "Mesken",
        "Sanayi",
        "Tarımsal Sulama",
        "Ticarethane",
        "Genel Toplam",
    ]
    satirlar = [baslik]
    for il in TUM_ILLER:
        satirlar.append([il, "1,0", "2,0", "999,0", "3,0", "4,0", "1009,0"])
    tbl = _tablo_ekle(satirlar)

    df = t11_oku(tbl, tarih_id=202006)

    assert len(df) == 81 * 4
    assert "Sanayi" not in set(df["grup"])
    assert set(df["grup"]) == {
        "Aydınlatma",
        "Mesken",
        "Tarımsal",
        "Kamu ve Özel Hizmetler",
    }


def test_t10_oku_il_only_yapida_hata_verir_grup_uydurmaz() -> None:
    """dokumanlar/08 — 2020'nin TÜM 12 ayında T10 tablosu YAPISAL OLARAK
    il-ONLY (grup boyutu hiç yok, iki il yan yana) — t10_oku grup
    UYDURMAMALI, ValueError fırlatmalı."""
    satirlar = [
        [
            "İl Adı",
            "2019\nOcak",
            "2020\nOcak",
            "Değişim (%)",
            "İl Adı",
            "2019\nOcak",
            "2020\nOcak",
            "Değişim (%)",
        ],
        [
            "İSTANBUL",
            "7.901.865",
            "8.081.123",
            "2,27",
            "EDİRNE",
            "264.204",
            "286.631",
            "8,49",
        ],
    ]
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="'Tüketici Türü'"):
        t10_oku(tbl, tarih_id=202001, hedef_ay_yil="Ocak 2020")


def test_t4_oku_eksik_il_acikca_sifirlanir() -> None:
    baslik = ["İLLER", "Biyokütle", "Toplam"]
    satirlar = [baslik, ["Eskişehir", "3,0", "3,0"], ["Genel Toplam", "3,0", "3,0"]]
    tbl = _tablo_ekle(satirlar)

    df = t4_oku(tbl, tarih_id=202001)

    assert df["il_kodu"].nunique() == 81
    assert float(df["kurulu_guc_mw"].sum()) == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# ADIM 4 (2026-09-13) — T2/T3: Lisanslı ÜRETİM (kurulu güç DEĞİL). 2020'nin
# 12 ayının TAMAMI gerçek dosyaya karşı kontrol edildi — Bulgu I/M sınıfı bir
# sürpriz (bölünmüş başlık, â/Â varyantı) GÖRÜLMEDİ, hepsi düz 2-satır, tüm
# kaynak etiketleri (DOĞAL GAZ/RÜZGAR/... dahil) worker/parser.py'ye zaten
# tanıdık.
# ---------------------------------------------------------------------------


def test_t2_oku_hedef_donem_kolonu_yil_once_buyuk_harfle_bulunur() -> None:
    donem_satiri = [
        "KAYNAK TÜRÜ",
        "2019 HAZİRAN",
        "2019 HAZİRAN",
        "2020 HAZİRAN",
        "2020 HAZİRAN",
        "DEĞİŞİM\n(%)",
    ]
    baslik_satiri = [
        "KAYNAK TÜRÜ",
        "ÜRETİM (MWh)",
        "ORAN (%)",
        "ÜRETİM (MWh)",
        "ORAN (%)",
        "DEĞİŞİM\n(%)",
    ]
    satirlar = [
        donem_satiri,
        baslik_satiri,
        ["HİDROLİK", "100,0", "50,0", "140,0", "50,0", "40,0"],
        ["RÜZGAR", "100,0", "50,0", "140,0", "50,0", "40,0"],
        ["Genel Toplam", "200,0", "100,0", "280,0", "100,0", "40,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    df = t2_oku(tbl, tarih_id=202006, hedef_ay_yil="2020 HAZİRAN")

    assert len(df) == 2
    assert float(df["uretim_mwh"].sum()) == pytest.approx(280.0)


def test_t2_oku_genel_toplam_uyusmazliginda_hata_verir() -> None:
    donem_satiri = ["KAYNAK TÜRÜ", "2020 HAZİRAN", "2020 HAZİRAN"]
    baslik_satiri = ["KAYNAK TÜRÜ", "ÜRETİM (MWh)", "ORAN (%)"]
    satirlar = [
        donem_satiri,
        baslik_satiri,
        ["HİDROLİK", "100,0", "100,0"],
        ["Genel Toplam", "999,0", "100,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="Genel"):
        t2_oku(tbl, tarih_id=202006, hedef_ay_yil="2020 HAZİRAN")


def test_t3_oku_iki_sutunlu_blok_birlesir_ve_eksik_il_sifirlanir() -> None:
    baslik = ["İLLER", "ÜRETİM (MWh)", "ORAN (%)", "İLLER", "ÜRETİM (MWh)", "ORAN (%)"]
    satirlar = [baslik]
    diger_iller = [il for il in TUM_ILLER if il != "Kilis"]
    assert len(diger_iller) == 80
    for i in range(0, 80, 2):
        satirlar.append(
            [diger_iller[i], "10,0", "1,0", diger_iller[i + 1], "10,0", "1,0"]
        )
    satirlar.append(["", "", "", "Genel Toplam", "800,0", "100,0"])
    tbl = _tablo_ekle(satirlar)

    df = t3_oku(tbl, tarih_id=202001)

    assert len(df) == 81
    assert df["il_kodu"].nunique() == 81
    kilis_kodu = next(kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "Kilis")
    assert df[df["il_kodu"] == kilis_kodu]["uretim_mwh"].eq(0.0).all()
    assert float(df["uretim_mwh"].sum()) == pytest.approx(800.0)


def test_t3_oku_genel_toplam_uyusmazliginda_hata_verir() -> None:
    baslik = ["İLLER", "ÜRETİM (MWh)", "ORAN (%)", "İLLER", "ÜRETİM (MWh)", "ORAN (%)"]
    satirlar = [baslik]
    for i in range(0, 80, 2):
        satirlar.append([TUM_ILLER[i], "10,0", "1,0", TUM_ILLER[i + 1], "10,0", "1,0"])
    satirlar.append(["", "", "", "Genel Toplam", "9999,0", "100,0"])
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="Genel"):
        t3_oku(tbl, tarih_id=202001)
