"""EPP — word_2018.py regresyon testleri (worker/scripts/word_2018.py).

worker/tests/test_word_2020.py ile AYNI yöntem (synthetic in-memory docx
tabloları, DATABASE_URL bağımsız). word_2018'a özgü farklar: T4'te "Güneş"
iki AYRI kolona bölünmüş (toplanmalı) + il adlarında satır-içi satır sonu
kırılması (yalnız satır sonu kaldırılır, gerçek boşluklar korunur).
"""

from __future__ import annotations

import pytest
from docx import Document

from worker.parser import _IL_ADI_KANONIK
from worker.scripts.word_2018 import (
    _ay_yil_dogrula_kapak,
    _il_adi_temizle,
    grup_esle_zorunlu,
    kaynak_esle_zorunlu,
    t4_oku,
    t10_oku,
    t11_oku,
)

TUM_ILLER = [_IL_ADI_KANONIK[kod] for kod in sorted(_IL_ADI_KANONIK)]
assert len(TUM_ILLER) == 81


def test_grup_esle_zorunlu_taksonomi_karari_bastan_uygulu() -> None:
    assert grup_esle_zorunlu("Ticarethane") == "Kamu ve Özel Hizmetler"
    assert grup_esle_zorunlu("Tarımsal Sulama") == "Tarımsal"
    assert grup_esle_zorunlu("Genel Toplam") is None


def test_kaynak_esle_zorunlu_gunes_varyantlari_toplanacak_sekilde_esler() -> None:
    """dokumanlar/08 — 2018'un T4 tablosunda 'Güneş' iki AYRI kolona
    bölünmüş: 'Güneş (Fotovoltaik)' (worker/parser.py zaten tanıyor) ve
    'Güneş (Yoğunlş.)' (burada eklendi) — ikisi de AYNI kanonik 'Güneş'e
    eşlenmeli (t4_oku() bunları TOPLAR, bkz. aşağıdaki test)."""
    assert kaynak_esle_zorunlu("Güneş (Fotovoltaik)") == "Güneş"
    assert kaynak_esle_zorunlu("Güneş (Yoğunlş.)") == "Güneş"


def test_kaynak_esle_zorunlu_ic_bosluk_normalize_edilir() -> None:
    """dokumanlar/08 — Ekim 2018'da bazı kolon başlıkları satır-içi satır
    sonu taşıyor (örn. 'Güneş \\n(Yoğunlş.)') — eşleme öncesi normalize
    edilmeli."""
    assert kaynak_esle_zorunlu("Güneş \n(Yoğunlş.)") == "Güneş"


def test_il_adi_temizle_satir_ici_satir_sonu_kaldirilir_bosluk_korunur() -> None:
    """dokumanlar/08 — Ekim 2018'da bazı il adları ORTADAN satır sonuyla
    bölünmüş (örn. 'DÜZC\\nE') — yalnız satır sonu kaldırılmalı, gerçek
    boşluklu metinler (örn. t4_oku()'nun aradığı 'Genel Toplam') BOZULMAMALI."""
    assert _il_adi_temizle("DÜZC\nE") == "DÜZCE"
    assert _il_adi_temizle("Genel Toplam") == "Genel Toplam"
    assert _il_adi_temizle("Adıyaman* ") == "Adıyaman"


def test_ay_yil_dogrula_kapak_normal_uyusma_gecer() -> None:
    _ay_yil_dogrula_kapak(
        "2018 Yılı Ekim Ayı Elektrik Piyasası Genel Görünümü", "Ekim", 2018, ay=10
    )
    with pytest.raises(ValueError, match="MANIFEST_2018 uyuşmazlığı"):
        _ay_yil_dogrula_kapak(
            "2018 Yılı Eylül Ayı Elektrik Piyasası Genel Görünümü", "Ekim", 2018, ay=10
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

    df = t11_oku(tbl, tarih_id=201806)

    assert len(df) == 81 * 4
    assert "Sanayi" not in set(df["grup"])


def test_t10_oku_il_only_yapida_hata_verir() -> None:
    satirlar = [
        [
            "İl Adı",
            "2018\nOcak",
            "2018\nOcak",
            "Değişim (%)",
            "İl Adı",
            "2018\nOcak",
            "2018\nOcak",
            "Değişim (%)",
        ],
        [
            "İSTANBUL",
            "7.898.584",
            "7.901.894",
            "0,04",
            "EDİRNE",
            "256.165",
            "264.204",
            "3,14",
        ],
    ]
    tbl = _tablo_ekle(satirlar)

    with pytest.raises(ValueError, match="'Tüketici Türü'"):
        t10_oku(tbl, tarih_id=201801, hedef_ay_yil="Ocak 2018")


def test_t4_oku_gunes_varyantlari_tek_satira_toplanir() -> None:
    """dokumanlar/08 — 'Güneş (Fotovoltaik)' ve 'Güneş (Yoğunlş.)' AYRI
    kolonlar olsa da, t4_oku() bunları TEK 'Güneş' satırına TOPLAMALI —
    fact_uretim'in doğal anahtarında {il,tarih,kaynak,lisans} tekil olmalı,
    aynı il için iki ayrı 'Güneş' satırı ÜRETİLMEMELİ."""
    baslik = ["İLLER", "Güneş (Fotovoltaik)", "Güneş (Yoğunlş.)", "Hidrolik", "Toplam"]
    satirlar = [
        baslik,
        ["Eskişehir", "3,0", "2,0", "1,0", "6,0"],
        ["Genel Toplam", "3,0", "2,0", "1,0", "6,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    df = t4_oku(tbl, tarih_id=201801)

    eskisehir_kodu = next(
        kod for kod, ad in _IL_ADI_KANONIK.items() if ad == "Eskişehir"
    )
    eskisehir_satirlari = df[df["il_kodu"] == eskisehir_kodu]
    # Tek 'Güneş' satırı olmalı (3,0+2,0=5,0), iki AYRI satır DEĞİL
    gunes_satirlari = eskisehir_satirlari[eskisehir_satirlari["kaynak"] == "Güneş"]
    assert len(gunes_satirlari) == 1
    assert gunes_satirlari["kurulu_guc_mw"].iloc[0] == pytest.approx(5.0)
    assert float(df["kurulu_guc_mw"].sum()) == pytest.approx(6.0)


def test_t4_oku_bilinen_anomali_satiri_atlanir_veri_uydurulmaz() -> None:
    """dokumanlar/08 — Ağustos/Eylül 2018'in T4 tablosunda EPDK'nın kendi
    kaynağında "BOŞ-VERİ-ŞEHİR" adlı, hiçbir gerçek il_kodu'na eşlenemeyen
    FAZLADAN bir satır var (81 gerçek ilin YANINDA). t4_oku() bu satırı
    AÇIKÇA atlamalı (TAHMİN ETMEMELİ) — Genel Toplam'ın kendi toleransı
    (~%0,1) bu küçük farkı zaten kapsıyor."""
    baslik = ["İLLER", "Biyokütle", "Toplam"]
    satirlar = [
        baslik,
        ["Eskişehir", "10,0", "10,0"],
        ["BOŞ-VERİ-ŞEHİR", "3,0", "3,0"],
        # Genel Toplam, atlanan satırın (3,0) DAHİL olduğu gerçek EPDK
        # değeri — t4_oku() bu satırı atlayınca hesaplanan (10,0) ile
        # Genel Toplam (13,0) arasında 3,0'lık bir fark oluşur, tolerans
        # (max(0.5, 13*0.001)=0.5) bunu KARŞILAMAZ — testte KASITLI olarak
        # gerçek Ağustos/Eylül 2018'deki gibi tolerans İÇİNDE bir fark
        # kurgulanmadı, bu yüzden ValueError beklenmeli (aşağıya bkz.).
        ["Genel Toplam", "13,0", "13,0"],
    ]
    tbl = _tablo_ekle(satirlar)

    # Küçük ölçekte (13 MW toplam) 3 MW'lık fark tolerans dışı kalır —
    # gerçek Ağustos 2018'de toplam ~5000 MW olduğundan 3,34 MW fark
    # tolerans (~5 MW) İÇİNDE kalıyordu. Bu test yalnız satırın GERÇEKTEN
    # atlandığını (uydurulmadığını) doğruluyor, tolerans matematiğini DEĞİL.
    with pytest.raises(ValueError, match="Genel"):
        t4_oku(tbl, tarih_id=201808)
