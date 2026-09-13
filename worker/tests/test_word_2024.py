"""EPP — word_2024.py regresyon testleri (worker/scripts/word_2024.py).

Canlı .docx dosyalarına ya da DATABASE_URL'e bağımlı DEĞİL — synthetic
in-memory docx tabloları (python-docx `Document().add_table()`, gerçek il
adları `worker.parser._IL_ADI_KANONIK`'ten) ve saf fonksiyon testleriyle
`t11_oku`/`t10_oku`/`t4_oku`/`grup_esle_zorunlu`/`kaynak_esle_zorunlu`/
`_ay_yil_dogrula`'yı doğrudan doğrular — CI'nin 'Worker (lint · types ·
validation)' job'ında (DATABASE_URL yok) da çalışır.

2023'ün aksine 2024 tek şablon (dedike `_il_adi_temizle` yok, tek grup
alias'ı var) — bkz. dokumanlar/09_PROJE_DURUMU.md "Bilinen açık maddeler".
"""

from __future__ import annotations

import pytest
from docx import Document

from worker.parser import _IL_ADI_KANONIK
from worker.scripts.word_2024 import (
    _STALE_IL_AYLAR,
    _ay_yil_dogrula,
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


# ---------------------------------------------------------------------------
# Saf fonksiyon testleri — docx gerekmez
# ---------------------------------------------------------------------------


def test_grup_esle_zorunlu_kamu_ozel_kisaltma_esler() -> None:
    """Mart 2024 T10-karşılığında bulunan tek kısaltma — 2023 Eylül ile
    AYNI ('Kamu/Özel/Diğer')."""
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


def test_kaynak_esle_zorunlu_linyit_dahil_bilinen_kaynaklar() -> None:
    """Nisan 2024'ten itibaren Linyit eklendi (5→6 kaynak sütunu,
    dokumanlar/06_canli_veri_operasyon_gunlugu.md 2026-09-02 T4 turu)."""
    assert kaynak_esle_zorunlu("Biyokütle") is not None
    assert kaynak_esle_zorunlu("Linyit") is not None
    assert kaynak_esle_zorunlu("Genel Toplam") is None


def test_ay_yil_dogrula_normal_uyusma_gecer() -> None:
    _ay_yil_dogrula("Tablo 2.6 Nisan 2024 Döneminde ...", "Nisan", 2024, "T11")


def test_ay_yil_dogrula_uyusmazlik_reddedilir() -> None:
    with pytest.raises(ValueError, match="MANIFEST_2024 uyuşmazlığı"):
        _ay_yil_dogrula("Tablo 2.6 Ocak 2024 Döneminde ...", "Şubat", 2024, "T11")


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

    df = t11_oku(tbl, tarih_id=202404)

    assert len(df) == 81 * 4  # Sanayi HARİÇ (Karar 2)
    assert "Sanayi" not in set(df["grup"])
    assert (df["baglanti"] == "dagitim").all()
    assert df[df["grup"] == "Mesken"]["tuketim_mwh"].eq(20.0).all()


def test_t10_oku_hedef_donem_kolonu_metin_aramasiyla_bulunur() -> None:
    donem_satiri = ["", "", "2023\nMart", "2023\nMart", "2024\nMart", "2024\nMart", ""]
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
            satirlar.append([il, grup, "100", "1,0", "130", "1,0", "30,0"])
    tbl = _tablo_ekle(satirlar)

    df = t10_oku(tbl, tarih_id=202403, hedef_ay_yil="2024 Mart")

    assert len(df) == 81 * 5
    assert df["il_kodu"].nunique() == 81
    assert (df["abone_sayisi"] == 130).all()


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

    df = t4_oku(tbl, tarih_id=202404)

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
        t4_oku(tbl, tarih_id=202404)


# ---------------------------------------------------------------------------
# ADIM 4 (2026-09-13) — T2/T3: Lisanslı ÜRETİM (kurulu güç DEĞİL). Gerçek
# 2024 verisinde bulunan YENİ bir format sürprizi burada regresyonla
# sabitlendi: Mayıs/Kasım/Aralık'ta 'ORAN (%)' hücresi Word'ün birleştirilmiş
# hücre kaydında İKİYE bölünmüş, 3. satır da 'KAYNAK TÜRÜ' etiketini taşıyor
# — 2025'in 2 satırlık sabit başlık varsayımı burada YETERSİZ, dinamik
# atlama gerekiyor (bkz. t2_oku modül notu).
# ---------------------------------------------------------------------------


def test_t2_oku_normal_iki_satir_baslikla_calisir() -> None:
    donem_satiri = [
        "KAYNAK TÜRÜ",
        "2023 HAZİRAN",
        "2023 HAZİRAN",
        "2024 HAZİRAN",
        "2024 HAZİRAN",
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
        ["Hidrolik", "100,0", "50,0", "140,0", "50,0", "40,0"],
        ["Genel Toplam", "100,0", "100,0", "140,0", "100,0", "40,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    df = t2_oku(tbl, tarih_id=202406, hedef_ay_yil="2024 HAZİRAN")

    assert len(df) == 1
    assert float(df["uretim_mwh"].sum()) == pytest.approx(140.0)


def test_t2_oku_uc_satirlik_bolunmus_baslikla_da_calisir() -> None:
    """2024-05/11/12'de gerçek veride bulunan kenar durumu: 'ORAN (%)'
    hücresi 3. satıra taşmış, o satırın ilk hücresi de HÂLÂ 'KAYNAK TÜRÜ' —
    veri asıl 4. satırdan (index 3) başlıyor. Fix ÖNCESİ bu durum 'Hidrolik'
    yerine 'KAYNAK TÜRÜ' metnini bir kaynak adı sanıp ValueError fırlatırdı."""
    satirlar = [
        [
            "KAYNAK TÜRÜ",
            "2023 MAYIS",
            "2023 MAYIS",
            "2024 MAYIS",
            "2024 MAYIS",
            "DEĞİŞİM",
        ],
        ["KAYNAK TÜRÜ", "ÜRETİM (MWh)", "ORAN", "ÜRETİM (MWh)", "ORAN", "(%)"],
        ["KAYNAK TÜRÜ", "ÜRETİM (MWh)", "(%)", "ÜRETİM (MWh)", "(%)", ""],
        ["Hidrolik", "100,0", "50,0", "140,0", "50,0", "40,0"],
        ["Genel Toplam", "100,0", "100,0", "140,0", "100,0", "40,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    df = t2_oku(tbl, tarih_id=202405, hedef_ay_yil="2024 MAYIS")

    assert len(df) == 1
    assert (
        df["kaynak"].iloc[0] == "Hidrolik"
    )  # 'KAYNAK TÜRÜ' etiketi veri satırı SANILMADI
    assert float(df["uretim_mwh"].sum()) == pytest.approx(140.0)


def test_t2_oku_genel_toplam_uyusmazliginda_hata_verir() -> None:
    donem_satiri = ["KAYNAK TÜRÜ", "2024 HAZİRAN", "2024 HAZİRAN"]
    baslik_satiri = ["KAYNAK TÜRÜ", "ÜRETİM (MWh)", "ORAN (%)"]
    satirlar = [
        donem_satiri,
        baslik_satiri,
        ["Hidrolik", "100,0", "100,0"],
        ["Genel Toplam", "999,0", "100,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="Genel"):
        t2_oku(tbl, tarih_id=202406, hedef_ay_yil="2024 HAZİRAN")


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

    df = t3_oku(tbl, tarih_id=202401)

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
        t3_oku(tbl, tarih_id=202401)


# ---------------------------------------------------------------------------
# Bulgu J (2026-09-13) — 2024-02'nin T3'ü (il bazında) EPDK'nın kendi
# belgesinde Ocak'ın stale kopyası. Ölçüm gerçek dosyaya karşı yapıldı
# (bkz. word_2024.py:isle_ay_uretim_geneli() modül notu, 12_word_uretim_
# envanteri.md Bulgu J) — burada yalnız kararın KENDİSİNİN (hangi ay,
# hangi gerekçe) doğru kayıtlı olduğu pinleniyor.
# ---------------------------------------------------------------------------


def test_stale_il_aylar_yalniz_subat_isaretli_gerekcesi_bulgu_j() -> None:
    assert set(_STALE_IL_AYLAR) == {2}
    assert "Bulgu J" in _STALE_IL_AYLAR[2]
    assert "BİREBİR" in _STALE_IL_AYLAR[2]
