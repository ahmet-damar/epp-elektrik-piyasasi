"""EPP — word_2021.py regresyon testleri (worker/scripts/word_2021.py).

worker/tests/test_word_2022.py ile AYNI yöntem (synthetic in-memory docx
tabloları, DATABASE_URL bağımsız) — bkz. o dosyanın modül notu.
"""

from __future__ import annotations

import pytest
from docx import Document

from worker.parser import _IL_ADI_KANONIK
from worker.scripts.word_2021 import (
    _ay_yil_dogrula,
    _il_adi_temizle,
    grup_esle_zorunlu,
    kaynak_esle_zorunlu,
    t4_oku,
    t10_oku,
    t11_oku,
)

TUM_ILLER = [_IL_ADI_KANONIK[kod] for kod in sorted(_IL_ADI_KANONIK)]
assert len(TUM_ILLER) == 81


def test_grup_esle_zorunlu_taksonomi_karari_uygulandi() -> None:
    """dokumanlar/08 — 2026-09-03 (madde 1/2a): mevsimsellik doğrulaması
    RENAME lehine sonuçlandı, "Ticarethane"/"Tarımsal Sulama" artık
    kanonik gruplara alias'lanıyor (ValueError FIRLAMAMALI)."""
    assert grup_esle_zorunlu("Ticarethane") == "Kamu ve Özel Hizmetler"
    assert grup_esle_zorunlu("Tarımsal Sulama") == "Tarımsal"


def test_grup_esle_zorunlu_kanonik_ve_atla_calisir() -> None:
    assert grup_esle_zorunlu("Aydınlatma") == "Aydınlatma"
    assert grup_esle_zorunlu("Sanayi") == "Sanayi"
    assert grup_esle_zorunlu("Genel Toplam") is None
    assert grup_esle_zorunlu("Pay\n(%)") is None
    assert grup_esle_zorunlu("Payı") is None


def test_grup_esle_zorunlu_gercekten_bilinmeyen_etiket_hata_verir() -> None:
    with pytest.raises(ValueError, match="Tanınmayan"):
        grup_esle_zorunlu("Bilinmeyen Grup XYZ")


def test_kaynak_esle_zorunlu_bilinen_kaynaklar() -> None:
    assert kaynak_esle_zorunlu("Rüzgar") is not None
    assert kaynak_esle_zorunlu("Toplam") is None


def test_il_adi_temizle_bilinen_yazim_hatalari_duzeltilir() -> None:
    """dokumanlar/08 — 2021'e özgü 3 il-adı yazım/kısaltma hatası: Küthahya
    (Kütahya, 2022'de de tekrarlayan aynı hata), AFYONK. (Afyonkarahisar),
    K.MARAŞ (Kahramanmaraş) + HAKKÂRİ (inceltmeli eski yazım, 2023'te de
    görülmüştü)."""
    assert _il_adi_temizle("Küthahya") == "Kütahya"
    assert _il_adi_temizle("AFYONK.") == "Afyonkarahisar"
    assert _il_adi_temizle("K.MARAŞ") == "Kahramanmaraş"
    assert _il_adi_temizle("HAKKÂRİ") == "HAKKARİ"


def test_ay_yil_dogrula_2021de_bilinen_etiket_hatasi_yok() -> None:
    """2022'nin aksine (Nisan etiket hatası) 2021'in 12 ayının HİÇBİRİNDE
    bilinen bir etiket hatası bulunmadı (dokumanlar/08) — normal uyuşma
    geçmeli, YENİ bir istisna mekanizması TETİKLENMEMELİ."""
    _ay_yil_dogrula(
        "Tablo 2.4 Haziran 2021 Döneminde ...", "Haziran", 2021, "T11", ay=6
    )
    with pytest.raises(ValueError, match="MANIFEST_2021 uyuşmazlığı"):
        _ay_yil_dogrula(
            "Tablo 2.4 Mayıs 2021 Döneminde ...", "Haziran", 2021, "T11", ay=6
        )


def _tablo_ekle(satirlar: list[list[str]]):  # type: ignore[no-untyped-def]
    doc = Document()
    tbl = doc.add_table(rows=len(satirlar), cols=len(satirlar[0]))
    for i, satir in enumerate(satirlar):
        for j, deger in enumerate(satir):
            tbl.rows[i].cells[j].text = deger
    return tbl


def test_t4_oku_kuthahya_duzeltmesiyle_81_il_tamamlanir() -> None:
    baslik = ["İLLER", "Biyokütle", "Toplam"]
    satirlar = [baslik, ["Küthahya", "12,5", "12,5"], ["Genel Toplam", "12,5", "12,5"]]
    tbl = _tablo_ekle(satirlar)

    df = t4_oku(tbl, tarih_id=202111)

    kutahya_kodu = next(kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "Kütahya")
    assert df[df["il_kodu"] == kutahya_kodu]["kurulu_guc_mw"].eq(12.5).all()
    assert df["il_kodu"].nunique() == 81


def test_t11_oku_alias_ile_sanayi_haric_dogru_toplam() -> None:
    """T11 artık "Ticarethane"/"Tarımsal Sulama" kolonlarını da kanonik
    gruplara eşleyip yükleyebilmeli (taksonomi kararı UYGULANDI)."""
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
        satirlar.append([il, "10,0", "20,0", "999,0", "5,0", "8,0", "1042,0"])
    tbl = _tablo_ekle(satirlar)

    df = t11_oku(tbl, tarih_id=202105)

    assert len(df) == 81 * 4  # Sanayi HARİÇ
    assert set(df["grup"]) == {
        "Aydınlatma",
        "Mesken",
        "Tarımsal",
        "Kamu ve Özel Hizmetler",
    }
    assert df[df["grup"] == "Tarımsal"]["tuketim_mwh"].eq(5.0).all()
    assert df[df["grup"] == "Kamu ve Özel Hizmetler"]["tuketim_mwh"].eq(8.0).all()


def test_t10_oku_il_only_yapida_hata_verir_grup_uydurmaz() -> None:
    """dokumanlar/08 — 2021 Ekim'e kadar T10 tablosu YAPISAL OLARAK
    il-ONLY (grup boyutu hiç yok, iki il yan yana). t10_oku bu durumda
    grup UYDURMAMALI, ValueError fırlatmalı — isle_ay() bunu yakalayıp
    T10'u o ay için 'kaynakta yok' sayar, T11 etkilenmez."""
    satirlar = [
        ["", "", "2020", "2020", "2021", "2021", ""],
        ["İl Adı", "", "Ocak", "Ocak", "Ocak", "Ocak", ""],
        ["İSTANBUL", "8.081.123", "8.203.045", "1,51", "EDİRNE", "286.631", "280.776"],
    ]
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError):
        t10_oku(tbl, tarih_id=202101, hedef_ay_yil="Ocak 2021")
