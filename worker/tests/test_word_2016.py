"""EPP — word_2016.py regresyon testleri (worker/scripts/word_2016.py).

worker/tests/test_word_2017.py ile AYNI yöntem (synthetic in-memory docx
tabloları, DATABASE_URL bağımsız). word_2016'ya özgü farklar: T11'de
İstanbul'un bazı aylarda iki AYRI satıra bölünmesi (aynı il_kodu'na TOPLANIR),
T4'te bazı ayların 0. satırının birleştirilmiş "Kaynak Türü" placeholder'ı
taşıması (gerçek başlık 1. satırda), T4'ün Toplam kolonunun bazı aylarda BOŞ
başlıklı olması (pozisyona güvenilir) ve grup etiketlerinin bazı aylarda
TAMAMEN BÜYÜK HARF olması (Türkçe-güvenli normalize_label ile eşlenir).
"""

from __future__ import annotations

import pytest
from docx import Document

from worker.parser import _IL_ADI_KANONIK
from worker.scripts.word_2016 import (
    _ay_yil_dogrula_kapak,
    _il_adi_temizle,
    grup_esle_zorunlu,
    kaynak_esle_zorunlu,
    t4_oku,
    t11_oku,
)

TUM_ILLER = [_IL_ADI_KANONIK[kod] for kod in sorted(_IL_ADI_KANONIK)]
assert len(TUM_ILLER) == 81


def test_grup_esle_zorunlu_taksonomi_karari_bastan_uygulu() -> None:
    assert grup_esle_zorunlu("Ticarethane") == "Kamu ve Özel Hizmetler"
    assert grup_esle_zorunlu("Tarımsal Sulama") == "Tarımsal"
    assert grup_esle_zorunlu("Genel Toplam") is None


def test_grup_esle_zorunlu_buyuk_harf_turkce_guvenli_normalize_edilir() -> None:
    """dokumanlar/08 — Şubat 2016'nın grup başlıkları TAMAMEN BÜYÜK HARF
    ("TARIMSAL SULAMA", "TİCARETHANE") — ham Python .upper()/plain-dict
    karşılaştırması Türkçe İ/I dönüşümünü YANLIŞ yapar, worker/parser.py:
    normalize_label() ile normalize edilmesi gerekir."""
    assert grup_esle_zorunlu("TARIMSAL SULAMA") == "Tarımsal"
    assert grup_esle_zorunlu("TİCARETHANE") == "Kamu ve Özel Hizmetler"


def test_grup_esle_zorunlu_ic_bosluk_normalize_edilir() -> None:
    assert grup_esle_zorunlu("Tarımsal\n Sulama") == "Tarımsal"


def test_kaynak_esle_zorunlu_gunes_varyantlari_hepsi_esler() -> None:
    """dokumanlar/08 — 2016'da 'Güneş (Yoğunlaştırılmış)' ay ay FARKLI
    kısaltmalarla yazılmış, hepsi kanonik 'Güneş'e eşlenmeli."""
    assert kaynak_esle_zorunlu("Güneş (Fotovoltaik)") == "Güneş"
    assert kaynak_esle_zorunlu("Güneş (Yoğunlaştırılmış)") == "Güneş"
    assert kaynak_esle_zorunlu("Güneş (Yoğun.)") == "Güneş"
    assert kaynak_esle_zorunlu("Güneş (Yoğunl.)") == "Güneş"
    assert kaynak_esle_zorunlu("Güneş (Yoğunlş.)") == "Güneş"
    assert kaynak_esle_zorunlu("Güneş (F.voltaik)") == "Güneş"


def test_il_adi_temizle_istanbul_bolunmus_varyantlari_kanonige_esler() -> None:
    """dokumanlar/08 — Ocak/Şubat/Mart 2016'da İstanbul T11 tablosunda İKİ
    AYRI satıra bölünmüş, ay ay FARKLI etiketlerle ('İST. ANADOLU'/
    'İST. AVRUPA', 'İSTANBUL AND.'/'İSTANBUL AVR.') — hepsi kanonik
    'İstanbul'a eşlenmeli (t11_oku() bunları TOPLAR, bkz. aşağıdaki test)."""
    assert _il_adi_temizle("İST. ANADOLU") == "İstanbul"
    assert _il_adi_temizle("İST. AVRUPA") == "İstanbul"
    assert _il_adi_temizle("İSTANBUL AND.") == "İstanbul"
    assert _il_adi_temizle("İSTANBUL AVR. ") == "İstanbul"


def test_ay_yil_dogrula_kapak_normal_uyusma_gecer() -> None:
    _ay_yil_dogrula_kapak(
        "2016 Yılı Ekim Ayı Elektrik Piyasası Genel Görünümü", "Ekim", 2016, ay=10
    )
    with pytest.raises(ValueError, match="MANIFEST_2016 uyuşmazlığı"):
        _ay_yil_dogrula_kapak(
            "2016 Yılı Eylül Ayı Elektrik Piyasası Genel Görünümü", "Ekim", 2016, ay=10
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
        "İLLER",
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

    df = t11_oku(tbl, tarih_id=201609)

    assert len(df) == 81 * 4
    assert "Sanayi" not in set(df["grup"])


def test_t11_oku_istanbul_bolunmus_satirlari_tek_satira_toplanir() -> None:
    """dokumanlar/08 — Ocak/Şubat/Mart 2016'da İstanbul 'İST. ANADOLU' ve
    'İST. AVRUPA' diye İKİ satıra bölünmüş — t11_oku() bunları TEK
    İstanbul satırına TOPLAMALI (fact_tuketim'in {il,tarih,grup,baglanti}
    doğal anahtarı tekil olmalı, iki ayrı İstanbul satırı ÜRETİLMEMELİ)."""
    baslik = [
        "İLLER",
        "Aydınlatma",
        "Mesken",
        "Sanayi",
        "Tarımsal Sulama",
        "Ticarethane",
    ]
    satirlar = [baslik]
    for il in TUM_ILLER:
        if il == "İstanbul":
            satirlar.append(["İST. ANADOLU", "1,0", "2,0", "999,0", "3,0", "4,0"])
            satirlar.append(["İST. AVRUPA", "1,0", "2,0", "999,0", "3,0", "4,0"])
        else:
            satirlar.append([il, "1,0", "2,0", "999,0", "3,0", "4,0"])
    tbl = _tablo_ekle(satirlar)

    df = t11_oku(tbl, tarih_id=201601)

    assert len(df) == 81 * 4  # İstanbul tek il olarak sayılmalı, 82 değil
    istanbul_kodu = next(kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "İstanbul")
    istanbul_satirlari = df[df["il_kodu"] == istanbul_kodu]
    assert len(istanbul_satirlari) == 4  # tek satır/grup, iki AYRI değil
    aydinlatma = istanbul_satirlari[istanbul_satirlari["grup"] == "Aydınlatma"]
    assert aydinlatma["tuketim_mwh"].iloc[0] == pytest.approx(2.0)  # 1,0+1,0 TOPLANMIŞ


def test_t11_oku_eksik_il_tahmin_etmez_hata_verir() -> None:
    """dokumanlar/08 — Temmuz 2016'da ADANA satırı kaynakta GERÇEKTEN kayıp
    (başlık tekrarıyla üzerine yazılmış). t11_oku() TAHMİN ETMEMELİ, 81
    ilin altında kalınca ValueError fırlatmalı (ay BEKLEMEDE işaretlenir)."""
    baslik = [
        "İLLER",
        "Aydınlatma",
        "Mesken",
        "Sanayi",
        "Tarımsal Sulama",
        "Ticarethane",
    ]
    satirlar = [baslik]
    for il in TUM_ILLER:
        if il == "Adana":
            satirlar.append(["İLLER", "", "", "", "", ""])  # başlık tekrarı, veri YOK
        else:
            satirlar.append([il, "1,0", "2,0", "999,0", "3,0", "4,0"])
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="beklenen satır"):
        t11_oku(tbl, tarih_id=201607)


def test_t4_oku_iki_satirli_baslik_dinamik_tespit_edilir() -> None:
    """dokumanlar/08 — Ocak/Şubat/Haziran/Temmuz/Ağustos/Eylül 2016'da T4
    tablosunun 0. satırı gerçek kaynak adları DEĞİL, birleştirilmiş
    'Kaynak Türü' hücreleri taşıyor — gerçek başlık 1. satırda."""
    satirlar = [
        ["İller", "Kaynak Türü", "Kaynak Türü", "Genel Toplam"],
        ["İller", "Biyokütle", "Hidrolik", "Genel Toplam"],
        ["Eskişehir", "3,0", "2,0", "5,0"],
        ["Genel Toplam", "3,0", "2,0", "5,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    df = t4_oku(tbl, tarih_id=201601)

    eskisehir_kodu = next(
        kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "Eskişehir"
    )
    satir = df[(df["il_kodu"] == eskisehir_kodu) & (df["kaynak"] == "Biyokütle")]
    assert satir["kurulu_guc_mw"].iloc[0] == pytest.approx(3.0)


def test_t4_oku_bos_basslikli_toplam_kolonu_pozisyonla_bulunur() -> None:
    """dokumanlar/08 — Ağustos 2016'da Toplam kolonunun başlığı BOŞ (yalnız
    boşluk) — metin arama yerine pozisyona (hep sonuncu kolon) güvenilir."""
    satirlar = [
        ["İLLER", "Biyokütle", "Hidrolik", " "],
        ["Eskişehir", "3,0", "2,0", "5,0"],
        ["Genel Toplam", "3,0", "2,0", "5,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    df = t4_oku(tbl, tarih_id=201608)

    assert float(df["kurulu_guc_mw"].sum()) == pytest.approx(5.0)


def test_t4_oku_gunes_varyantlari_tek_satira_toplanir() -> None:
    baslik = [
        "İLLER",
        "Güneş (Fotovoltaik)",
        "Güneş (Yoğunlaştırılmış)",
        "Hidrolik",
        "Toplam",
    ]
    satirlar = [
        baslik,
        ["Eskişehir", "3,0", "2,0", "1,0", "6,0"],
        ["Genel Toplam", "3,0", "2,0", "1,0", "6,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    df = t4_oku(tbl, tarih_id=201601)

    eskisehir_kodu = next(
        kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "Eskişehir"
    )
    gunes_satirlari = df[(df["il_kodu"] == eskisehir_kodu) & (df["kaynak"] == "Güneş")]
    assert len(gunes_satirlari) == 1
    assert gunes_satirlari["kurulu_guc_mw"].iloc[0] == pytest.approx(5.0)
