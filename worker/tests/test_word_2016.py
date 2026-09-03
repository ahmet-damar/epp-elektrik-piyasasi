"""EPP — word_2016.py regresyon testleri (worker/scripts/word_2016.py).

worker/tests/test_word_2017.py ile AYNI yöntem (synthetic in-memory docx
tabloları, DATABASE_URL bağımsız). word_2016'ya özgü farklar: T11'de
İstanbul'un bazı aylarda iki AYRI satıra bölünmesi (aynı il_kodu'na TOPLANIR),
T4'te bazı ayların 0. satırının birleştirilmiş "Kaynak Türü" placeholder'ı
taşıması (gerçek başlık 1. satırda), T4'ün Toplam kolonunun bazı aylarda BOŞ
başlıklı olması (pozisyona güvenilir), grup etiketlerinin bazı aylarda
TAMAMEN BÜYÜK HARF olması (Türkçe-güvenli normalize_label ile eşlenir) ve
Temmuz 2016'da TEK bir ilin (Adana) tablonun kendi Genel Toplam satırından
TÜRETİLMESİ (dokumanlar/08 — tahmin değil, matematiksel çıkarım; t11_oku()
artık `(df, turetilmis_kayitlari)` tuple'ı döner).
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

    df, turetilmis = t11_oku(tbl, tarih_id=201609)

    assert len(df) == 81 * 4
    assert "Sanayi" not in set(df["grup"])
    assert turetilmis is None  # 81 ilin hepsi mevcut, türetme YOK


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

    df, turetilmis = t11_oku(tbl, tarih_id=201601)

    assert len(df) == 81 * 4  # İstanbul tek il olarak sayılmalı, 82 değil
    assert turetilmis is None  # 81 ilin hepsi mevcut (İstanbul toplanmış), türetme YOK
    istanbul_kodu = next(kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "İstanbul")
    istanbul_satirlari = df[df["il_kodu"] == istanbul_kodu]
    assert len(istanbul_satirlari) == 4  # tek satır/grup, iki AYRI değil
    aydinlatma = istanbul_satirlari[istanbul_satirlari["grup"] == "Aydınlatma"]
    assert aydinlatma["tuketim_mwh"].iloc[0] == pytest.approx(2.0)  # 1,0+1,0 TOPLANMIŞ


def test_t11_oku_tek_il_eksikse_genel_toplamdan_turetilir() -> None:
    """dokumanlar/08 — Temmuz 2016'da ADANA satırı kaynakta GERÇEKTEN kayıp
    (başlık tekrarıyla üzerine yazılmış), ama tablo kendi Genel Toplam
    satırını basıyor. TEK il eksikken + Genel Toplam satırı VARKEN
    t11_oku() artık TAHMİN ETMEZ ama TÜRETİR (kaynağın kendi Genel
    Toplam'ından diğer 80 ilin farkı — matematiksel çıkarım, dokumanlar/08).
    80 il sabit değer taşıyor, Genel Toplam bu 80'in toplamı + rastgele bir
    'Adana payı' (10/20/30/40) olacak şekilde kurulmuş; türetilen değerin
    tam olarak bu paya eşit olduğu doğrulanıyor."""
    baslik = [
        "İLLER",
        "Aydınlatma",
        "Mesken",
        "Sanayi",
        "Tarımsal Sulama",
        "Ticarethane",
    ]
    satirlar = [baslik]
    diger_iller = [il for il in TUM_ILLER if il != "Adana"]
    assert len(diger_iller) == 80
    for il in diger_iller:
        satirlar.append([il, "1,0", "2,0", "999,0", "3,0", "4,0"])
    # Adana satırı yerine sayfa-sonu başlık tekrarı (gerçek kaynak deseni)
    satirlar.append(["İLLER", "", "", "", "", ""])
    # Genel Toplam = 80 ilin toplamı + Adana payı (10,0 / 20,0 / 999*80+x / 30,0 / 40,0)
    satirlar.append(["Genel Toplam", "90,0", "180,0", "80019,0", "270,0", "360,0"])
    tbl = _tablo_ekle(satirlar)

    df, turetilmis = t11_oku(tbl, tarih_id=201607)

    assert len(df) == 81 * 4  # artık TAM 81 il (Adana türetildi)
    assert turetilmis is not None
    assert len(turetilmis) == 4  # Sanayi hariç 4 grup

    adana_kodu = next(kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "Adana")
    adana_satirlari = df[df["il_kodu"] == adana_kodu]
    assert len(adana_satirlari) == 4
    beklenen = {
        "Aydınlatma": 10.0,
        "Mesken": 20.0,
        "Tarımsal": 30.0,
        "Kamu ve Özel Hizmetler": 40.0,  # Ticarethane RENAME
    }
    for grup, beklenen_deger in beklenen.items():
        satir = adana_satirlari[adana_satirlari["grup"] == grup]
        assert satir["tuketim_mwh"].iloc[0] == pytest.approx(beklenen_deger)

    # turetilmis_kayitlari da AYNI değerleri taşımalı (audit_log'a gidecek)
    turetilen_gruplar = {k["grup"]: k["tuketim_mwh"] for k in turetilmis}
    for grup, beklenen_deger in beklenen.items():
        assert turetilen_gruplar[grup] == pytest.approx(beklenen_deger)
        assert all(k["il_kodu"] == adana_kodu for k in turetilmis)


def test_t11_oku_iki_il_eksikse_hala_tahmin_etmez_hata_verir() -> None:
    """Güvenlik ağı — 2+ il eksikken payı dağıtmanın matematiksel bir yolu
    YOK, türetme YAPILMAMALI, ValueError fırlatılmalı (regresyon riski en
    yüksek nokta)."""
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
        if il in ("Adana", "Bursa"):
            continue  # İKİ il eksik
        satirlar.append([il, "1,0", "2,0", "999,0", "3,0", "4,0"])
    satirlar.append(["Genel Toplam", "790,0", "1580,0", "78921,0", "2370,0", "3160,0"])
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="beklenen satır"):
        t11_oku(tbl, tarih_id=201607)


def test_t11_oku_genel_toplam_yoksa_tek_il_eksik_bile_hata_verir() -> None:
    """Güvenlik ağı — Genel Toplam satırı hiç yoksa türetme için gerekli
    çapa da yok, TEK il eksik olsa bile ValueError (türetme için Genel
    Toplam ZORUNLU)."""
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
            continue  # eksik, ama Genel Toplam satırı da HİÇ yok
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
