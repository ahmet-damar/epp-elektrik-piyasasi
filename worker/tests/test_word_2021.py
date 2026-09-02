"""EPP — word_2021.py regresyon testleri (worker/scripts/word_2021.py).

worker/tests/test_word_2022.py ile AYNI yöntem (synthetic in-memory docx
tabloları, DATABASE_URL bağımsız) — bkz. o dosyanın modül notu. word_2021
2022'den farklı olarak TEK şablon (12 ay boyunca eski taksonomi, hiç
geçiş yok) — bu yüzden testler daha basit: yalnız "her ay engellenir"
davranışını ve T4/il-adı-düzeltmesini doğrular.
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
)

TUM_ILLER = [_IL_ADI_KANONIK[kod] for kod in sorted(_IL_ADI_KANONIK)]
assert len(TUM_ILLER) == 81


def test_grup_esle_zorunlu_eski_takson_tum_yil_kasitli_engellenir() -> None:
    """dokumanlar/08 — 2021'in TÜM 12 ayı eski taksonomi kullanıyor
    (mekanik taramayla doğrulandı, 2022'nin aksine hiç geçiş yok) — bu
    yüzden 'Ticarethane'/'Tarımsal Sulama' HER ay için KASITLI engellenmeli."""
    with pytest.raises(ValueError, match="KASITLI"):
        grup_esle_zorunlu("Ticarethane")
    with pytest.raises(ValueError, match="KASITLI"):
        grup_esle_zorunlu("Tarımsal Sulama")


def test_grup_esle_zorunlu_kanonik_ve_atla_calisir() -> None:
    assert grup_esle_zorunlu("Aydınlatma") == "Aydınlatma"
    assert grup_esle_zorunlu("Sanayi") == "Sanayi"
    assert grup_esle_zorunlu("Genel Toplam") is None


def test_kaynak_esle_zorunlu_bilinen_kaynaklar() -> None:
    assert kaynak_esle_zorunlu("Rüzgar") is not None
    assert kaynak_esle_zorunlu("Toplam") is None


def test_il_adi_temizle_kuthahya_tekrarlayan_kaynak_hatasi() -> None:
    """dokumanlar/08 — 'Küthahya' yazım hatası 2022 Ocak/Şubat'ta VE 2021
    Kasım/Aralık'ta TEKRAR bulundu (tek seferlik değil, EPDK kaynağında
    tekrarlayan bir hata)."""
    assert _il_adi_temizle("Küthahya") == "Kütahya"


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
    """word_2021.py'ye özel senaryo — Küthahya (Kütahya'nın yanlış yazımı)
    tabloda GERÇEKTEN bu hatalı adla geçiyor, yine de doğru il_kodu'na
    eşlenmeli (eksik il olarak 0'lanmak yerine)."""
    baslik = ["İLLER", "Biyokütle", "Toplam"]
    satirlar = [baslik, ["Küthahya", "12,5", "12,5"], ["Genel Toplam", "12,5", "12,5"]]
    tbl = _tablo_ekle(satirlar)

    df = t4_oku(tbl, tarih_id=202111)

    kutahya_kodu = next(kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "Kütahya")
    assert df[df["il_kodu"] == kutahya_kodu]["kurulu_guc_mw"].eq(12.5).all()
    assert df["il_kodu"].nunique() == 81
