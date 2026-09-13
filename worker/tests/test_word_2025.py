"""EPP — word_2025.py regresyon testleri (worker/scripts/word_2025.py).

Canlı .docx dosyalarına ya da DATABASE_URL'e bağımlı DEĞİL — synthetic
in-memory docx tabloları (python-docx `Document().add_table()`, gerçek il
adları `worker.parser._IL_ADI_KANONIK`'ten) ve saf fonksiyon testleriyle
`t11_oku`/`t10_oku`/`t4_oku`/`grup_esle_zorunlu`/`kaynak_esle_zorunlu`/
`_il_adi_temizle`/`_ay_yil_dogrula`'yı doğrudan doğrular — CI'nin
'Worker (lint · types · validation)' job'ında (DATABASE_URL yok) da çalışır.

2025 tek şablon (12 ayın tamamı ön-taramada kontrol edildi) — tek grup
alias'ı (2024 Mart ile aynı); `_il_adi_temizle` 2025'te fiilen tetiklenmedi
ama ucuz bir önlem olarak duruyor (bkz. modül notu). Bu dosya
dokumanlar/09_PROJE_DURUMU.md'nin "Bilinen açık maddeler" listesindeki
son maddeyi (word_2023/2024/2025 regresyon testi) kapatır.
"""

from __future__ import annotations

import pytest
from docx import Document

from worker.parser import _IL_ADI_KANONIK
from worker.scripts.word_2025 import (
    _ay_yil_dogrula,
    _il_adi_temizle,
    grup_esle_zorunlu,
    kaynak_esle_zorunlu,
    t2_oku,
    t3_oku,
    t4_oku,
    t5_oku,
    t10_oku,
    t11_oku,
)

TUM_ILLER = [_IL_ADI_KANONIK[kod] for kod in sorted(_IL_ADI_KANONIK)]
assert len(TUM_ILLER) == 81


# ---------------------------------------------------------------------------
# Saf fonksiyon testleri — docx gerekmez
# ---------------------------------------------------------------------------


def test_grup_esle_zorunlu_kamu_ozel_kisaltma_esler() -> None:
    assert grup_esle_zorunlu("Kamu/Özel/Diğer") == "Kamu ve Özel Hizmetler"


def test_grup_esle_zorunlu_kanonik_gruplar_direkt_esler() -> None:
    assert grup_esle_zorunlu("Aydınlatma") == "Aydınlatma"
    assert grup_esle_zorunlu("Mesken") == "Mesken"
    assert grup_esle_zorunlu("Sanayi") == "Sanayi"
    assert grup_esle_zorunlu("Tarımsal Faaliyetler") == "Tarımsal"
    assert (
        grup_esle_zorunlu("Kamu ve Özel Hizmetler Sektörü ile Diğer")
        == "Kamu ve Özel Hizmetler"
    )


def test_grup_esle_zorunlu_atla_etiketleri_none_doner() -> None:
    assert grup_esle_zorunlu("Genel Toplam") is None
    assert grup_esle_zorunlu("Pay") is None


def test_grup_esle_zorunlu_bilinmeyen_etiket_hata_verir() -> None:
    with pytest.raises(ValueError, match="Tanınmayan tüketici grubu"):
        grup_esle_zorunlu("Hiç Bilinmeyen Bir Grup")


def test_kaynak_esle_zorunlu_bilinen_kaynaklar() -> None:
    assert kaynak_esle_zorunlu("Biyokütle") is not None
    assert kaynak_esle_zorunlu("Linyit") is not None
    assert kaynak_esle_zorunlu("Genel Toplam") is None


def test_kaynak_esle_zorunlu_ruzgar_inceltme_isaretiyle_de_esler() -> None:
    """T5 (Lisanssız üretim) tablosu 'Rüzgâr' (â) yazıyor, T2/T4 'RÜZGAR'/
    'Rüzgar' (â'sız) — gerçek 2025 verisinde bulundu (ADIM 4 kod turu),
    ikisi de AYNI kanonik değere eşlemeli."""
    assert kaynak_esle_zorunlu("Rüzgâr") == "Rüzgar"
    assert kaynak_esle_zorunlu("RÜZGAR") == "Rüzgar"


def test_il_adi_temizle_ucuz_onlem_normal_isimleri_bozmaz() -> None:
    """2025'te fiilen tetiklenmedi ama fonksiyon 2023'ün dipnot/inceltme
    düzeltmelerini hâlâ uyguluyor — normal il adlarını bozmadığı
    doğrulanmalı."""
    assert _il_adi_temizle("İstanbul") == "İstanbul"
    assert _il_adi_temizle("Adıyaman* ") == "Adıyaman"
    assert _il_adi_temizle("HAKKÂRİ") == "HAKKARİ"


def test_ay_yil_dogrula_normal_uyusma_gecer() -> None:
    _ay_yil_dogrula("Tablo 2.6 Nisan 2025 Döneminde ...", "Nisan", 2025, "T11")


def test_ay_yil_dogrula_uyusmazlik_reddedilir() -> None:
    with pytest.raises(ValueError, match="MANIFEST_2025 uyuşmazlığı"):
        _ay_yil_dogrula("Tablo 2.6 Ocak 2025 Döneminde ...", "Şubat", 2025, "T11")


# ---------------------------------------------------------------------------
# Yapısal testler — synthetic in-memory docx tabloları
# ---------------------------------------------------------------------------


def _tablo_ekle(satirlar: list[list[str]]):  # type: ignore[no-untyped-def]
    doc = Document()
    satir_sayisi, kolon_sayisi = len(satirlar), len(satirlar[0])
    tbl = doc.add_table(rows=satir_sayisi, cols=kolon_sayisi)
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
        "Tarımsal Faaliyetler",
        "Kamu ve Özel Hizmetler Sektörü ile Diğer",
        "Genel Toplam",
        "Pay",
    ]
    satirlar = [baslik]
    for il in TUM_ILLER:
        satirlar.append([il, "10,0", "20,0", "999,0", "5,0", "8,0", "1042,0", "1,0"])
    tbl = _tablo_ekle(satirlar)

    df = t11_oku(tbl, tarih_id=202504)

    assert len(df) == 81 * 4  # Sanayi HARİÇ (Karar 2)
    assert "Sanayi" not in set(df["grup"])
    assert (df["baglanti"] == "dagitim").all()
    assert df[df["grup"] == "Mesken"]["tuketim_mwh"].eq(20.0).all()


def test_t10_oku_hedef_donem_kolonu_metin_aramasiyla_bulunur() -> None:
    """Nisan 2025'te bulunan 5-illik toplu 'Aydınlatma' kırmızı-satır
    deseni (bkz. dokumanlar/06_canli_veri_operasyon_gunlugu.md,
    2026-09-02 devam) t10_oku'nun kendisini etkilemiyor — yalnız
    kırmızı-satır incelemesi/aktivasyon aşamasında ele alınıyor, bu
    testin kapsamı dışında."""
    donem_satiri = [
        "",
        "",
        "2024\nNisan",
        "2024\nNisan",
        "2025\nNisan",
        "2025\nNisan",
        "",
    ]
    baslik_satiri = [
        "İl Adı",
        "Tüketici Türü",
        "Sayı",
        "Pay(%)",
        "Sayı",
        "Pay(%)",
        "Değişim (%)",
    ]
    satirlar = [donem_satiri, baslik_satiri]
    gruplar = [
        "Aydınlatma",
        "Mesken",
        "Sanayi",
        "Tarımsal Faaliyetler",
        "Kamu/Özel/Diğer",
    ]
    for il in TUM_ILLER:
        for grup in gruplar:
            satirlar.append([il, grup, "100", "1,0", "140", "1,0", "40,0"])
    tbl = _tablo_ekle(satirlar)

    df = t10_oku(tbl, tarih_id=202504, hedef_ay_yil="2025 Nisan")

    assert len(df) == 81 * 5
    assert df["il_kodu"].nunique() == 81
    assert (df["abone_sayisi"] == 140).all()


def test_t4_oku_eksik_il_acikca_sifirlanir_ve_genel_toplam_dogrulanir() -> None:
    baslik = [
        "İLLER",
        "Biyokütle",
        "Doğal Gaz",
        "Güneş",
        "Hidrolik",
        "Rüzgar",
        "Linyit",
        "Toplam",
    ]
    satirlar = [baslik]
    satirlar.append(["Eskişehir", "1,0", "2,0", "3,0", "4,0", "5,0", "6,0", "21,0"])
    satirlar.append(["Ankara", "0,0", "0,0", "10,0", "0,0", "0,0", "0,0", "10,0"])
    satirlar.append(["Genel Toplam", "1,0", "2,0", "13,0", "4,0", "5,0", "6,0", "31,0"])
    tbl = _tablo_ekle(satirlar)

    df = t4_oku(tbl, tarih_id=202504)

    assert df["il_kodu"].nunique() == 81
    assert float(df["kurulu_guc_mw"].sum()) == pytest.approx(31.0)
    mugla_kodu = next(kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "Muğla")
    assert df[df["il_kodu"] == mugla_kodu]["kurulu_guc_mw"].eq(0.0).all()


def test_t4_oku_genel_toplam_uyusmazliginda_hata_verir() -> None:
    baslik = ["İLLER", "Biyokütle", "Toplam"]
    satirlar = [
        baslik,
        ["Eskişehir", "5,0", "5,0"],
        ["Genel Toplam", "5,0", "999,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="Genel"):
        t4_oku(tbl, tarih_id=202504)


# ---------------------------------------------------------------------------
# ADIM 4 (2026-09-13) — T2/T3/T5: Lisanslı/Lisanssız ÜRETİM (kurulu güç
# DEĞİL). Gerçek 2025 verisine karşı bulunan iki format sürprizi burada
# regresyonla sabitlendi: (1) T2'nin dönem satırı T10'dan FARKLI sırada/
# büyük-harfle ('2025 HAZİRAN', T10'un 'Haziran 2025'i DEĞİL), (2) T3'te
# üretimi sıfıra yakın bir il (2025-01'de Kilis) satır olarak hiç
# görünmeyebiliyor (T4'ün Bulgu 5 madde 4'üyle AYNI desen).
# ---------------------------------------------------------------------------


def test_t2_oku_yil_once_buyuk_harf_donem_satiriyla_dogru_kolonu_bulur() -> None:
    """T2'nin gerçek 2025 dönem satırı '2025 HAZİRAN' gibi (yıl-önce,
    TÜM-BÜYÜK, Türkçe noktalı İ) — T10'un 'Haziran 2025'inden (ay-önce,
    başlık-harf) FARKLI. word_ortak.py:hedef_donem_kolonu_bul()'ün
    normalize_label tabanlı karşılaştırması bunu doğru buluyor mu, YANLIŞ
    (bir yıl kaymış) bir kolona DÜŞMEDEN doğrulanır."""
    donem_satiri = [
        "KAYNAK TÜRÜ",
        "2024 HAZİRAN",
        "2024 HAZİRAN",
        "2025 HAZİRAN",
        "2025 HAZİRAN",
        "DEĞİŞİM\n(%)",
    ]
    baslik_satiri = [
        "KAYNAK TÜRÜ",
        "ÜRETİM (MWh)",
        "ORAN\n (%)",
        "ÜRETİM (MWh)",
        "ORAN \n(%)",
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

    df = t2_oku(tbl, tarih_id=202506, hedef_ay_yil="2025 HAZİRAN")

    assert len(df) == 2
    assert set(df["kaynak"]) == {"Hidrolik", "Rüzgar"}
    assert (df["lisans"] == "Lisanslı").all()
    # 2024 kolonuna (100,0/100,0) DEĞİL, 2025 kolonuna (140,0/140,0) düşmeli
    assert float(df["uretim_mwh"].sum()) == pytest.approx(280.0)


def test_t2_oku_genel_toplam_uyusmazliginda_hata_verir() -> None:
    donem_satiri = ["KAYNAK TÜRÜ", "2025 HAZİRAN", "2025 HAZİRAN"]
    baslik_satiri = ["KAYNAK TÜRÜ", "ÜRETİM (MWh)", "ORAN (%)"]
    satirlar = [
        donem_satiri,
        baslik_satiri,
        ["Hidrolik", "100,0", "100,0"],
        ["Genel Toplam", "999,0", "100,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="Genel"):
        t2_oku(tbl, tarih_id=202506, hedef_ay_yil="2025 HAZİRAN")


def test_t3_oku_iki_sutunlu_blok_birlesir_ve_eksik_il_sifirlanir() -> None:
    """Bulgu F (iki-sütunlu sayfa düzeni) + gerçek 2025-01 verisinde
    bulunan 'üretimi sıfıra yakın bir il satır olarak hiç görünmüyor'
    kenar durumu (T4'teki Bulgu 5 madde 4 ile AYNI desen) - burada
    kasıtlı olarak son il (81.) eksik bırakılıyor, 0.0 ile tamamlanmalı."""
    baslik = ["İLLER", "ÜRETİM (MWh)", "ORAN (%)", "İLLER", "ÜRETİM (MWh)", "ORAN (%)"]
    satirlar = [baslik]
    # 80 il, sol+sağ karışık - 81.'yi (Kilis) KASITLI OLARAK atla
    diger_iller = [il for il in TUM_ILLER if il != "Kilis"]
    assert len(diger_iller) == 80
    for i in range(0, 80, 2):
        satirlar.append(
            [diger_iller[i], "10,0", "1,0", diger_iller[i + 1], "10,0", "1,0"]
        )
    satirlar.append(["", "", "", "Genel Toplam", "800,0", "100,0"])
    tbl = _tablo_ekle(satirlar)

    df = t3_oku(tbl, tarih_id=202501)

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
        t3_oku(tbl, tarih_id=202501)


def test_t5_oku_brut_kolonu_kullanilir_ihtiyac_fazlasi_degil() -> None:
    """Bulgu D (Karar 4): 2018+ tanımı 'Brüt Lisanssız Üretim Miktarı'
    kolonudur - AYNI tabloda duran 'İhtiyaç Fazlası Satın Alınan Enerji
    Miktarı' (dar bir alt-küme) KARIŞTIRILMAMALI. Bu test, iki kolonun
    KASITLI OLARAK farklı değerler taşıdığı bir tabloda doğru kolonun
    seçildiğini kanıtlıyor."""
    baslik = [
        "Kaynak Türü",
        "İhtiyaç Fazlası \nSatın Alınan\n Enerji Miktarı (MWh)",
        "Oran\n(%)",
        "Brüt Lisanssız Üretim Miktarı (MWh)",
        "Oran\n(%)",
        "İhtiyaç Fazlası \nSatın Alınan \nEnerji Miktarı\n İçin Yapılan \nÖdeme Miktarı \n(TL)",
        "Oran\n(%)",
    ]
    satirlar = [
        baslik,
        ["Güneş", "100,0", "50,0", "300,0", "60,0", "9999,0", "100,0"],
        ["Rüzgâr", "100,0", "50,0", "200,0", "40,0", "0,0", "0,0"],
        ["Genel Toplam", "200,0", "100,0", "500,0", "100,0", "9999,0", "100,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    df = t5_oku(tbl, tarih_id=202506)

    assert len(df) == 2
    assert (df["lisans"] == "Lisanssız").all()
    assert set(df["kaynak"]) == {"Güneş", "Rüzgar"}  # Rüzgâr -> Rüzgar
    # 500,0 (Brüt) olmalı, 200,0 (İhtiyaç Fazlası) DEĞİL
    assert float(df["uretim_mwh"].sum()) == pytest.approx(500.0)


def test_t5_oku_genel_toplam_uyusmazliginda_hata_verir() -> None:
    baslik = [
        "Kaynak Türü",
        "İhtiyaç Fazlası Satın Alınan Enerji Miktarı (MWh)",
        "Oran(%)",
        "Brüt Lisanssız Üretim Miktarı (MWh)",
        "Oran(%)",
    ]
    satirlar = [
        baslik,
        ["Güneş", "100,0", "100,0", "300,0", "100,0"],
        ["Genel Toplam", "100,0", "100,0", "9999,0", "100,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="Genel"):
        t5_oku(tbl, tarih_id=202506)
