"""EPP — 2016 Word (.docx) EPDK aylık raporları: TEK SEFERLİK tarihsel
aktarım tarifi. Bkz. dokumanlar/08_word_2016_2022_kapsam.md (teşhis) ve
worker/scripts/word_2017.py (yapısal temel — bu dosya onun kopyası, YIL
BAZLI AYRI TARİF ilkesi bilinçli tercih). **2016, 2016-2022'nin SON ve EN
FARKLI yılı** — birkaç GENUINE yeni format sürprizi taşıyor (aşağıda).

**Ortam notu (2026-09-04):** Bu makinede pandas'ın derlenmiş bir bileşeni
Windows Akıllı Uygulama Denetimi (Değerlendirme modu) tarafından
engellenmişti — Miniconda ile (`C:\\Users\\adama\\miniconda3\\envs\\epp`,
conda-forge kanalı) çözüldü. Tüm dry-run/test/yükleme komutları bu
ortamın Python'ıyla çalıştırılmalı: `C:\\Users\\adama\\miniconda3\\envs\\
epp\\python.exe`.

**GECE-BOYU GÖZETİMSİZ ÇALIŞMA KURALLARI (Ahmet'in talimatı):**
- `pipeline.batch_onayla()` / `worker/scripts/onayla.py` BU DOSYADA HİÇ
  ÇAĞRILMAZ.
- Taksonomi kararı BAŞTAN dahil (RENAME, 2021/2022'de verildi) — 2016'da
  da AYNI eski taksonomi (Aydınlatma/Mesken/Sanayi/Tarımsal Sulama/
  Ticarethane) doğrulandı, tüm 12 ay için.

**2016'ya ÖZGÜ, dokumanlar/08'de teşhis edilen YENİ format sürprizleri:**
1. **T10 (Tüketici Sayısı) tablosu 2016'da HİÇ YOK** — 2017-2020'nin
   "il-only yapı" (tablo var ama grup kırılımı yok) sorunundan FARKLI:
   burada raporun kendisinde böyle bir tablo (ne başlık ne gövde) hiç
   basılmamış (tüm 12 ay, tam metin taraması ile doğrulandı — "Tüketici
   Sayı"/"Abone" kelimeleri hiçbir dosyada 0 eşleşme). `isle_ay()` T10
   tablosunu ARAMAYI da try/except içine alıyor (yalnız t10_oku()'yu
   değil — 2017-2020'de tablo VARDI, yalnız okurken hata veriyordu).
2. **T11'in arama metni DAHA SPESİFİK olmalı**: "Tablo 2.3 ... Tüketici
   Türü Bazında Dağılımı" (il kırılımı YOK, Karar 2'de zaten kapsam dışı
   olan bir özet tablo) da "Tüketici Türü Bazında Dağılımı" alt-dizisini
   TAŞIYOR — 2017-2022'nin kısa arama metni burada 2 aday bulur. Arama
   metni "İl ve Tüketici Türü Bazında Dağılımı" olarak GENİŞLETİLDİ (yalnız
   Tablo 2.4'e özgü).
3. **Ocak/Şubat/Mart 2016'da İstanbul T11 tablosunda İKİ AYRI satıra
   bölünmüş** ("İST. ANADOLU"/"İST. AVRUPA", "İSTANBUL AND."/"İSTANBUL
   AVR." gibi varyantlar — Nisan'dan itibaren tek "İSTANBUL" satırına
   birleşiyor). `t11_oku()` bu yüzden t4_oku()'daki AYNI dict-toplama
   desenine geçirildi (aynı il_kodu'na eşlenen birden fazla satır
   TOPLANIYOR, ayrı satır ÜRETİLMİYOR) — aksi halde fact_tuketim'in doğal
   anahtarı ihlal edilirdi. T4 tablosunda bu bölünme YOK (doğrulandı).
4. **Bazı aylarda (Ocak/Şubat/Haziran/Temmuz/Ağustos/Eylül) T4 tablosunun
   0. satırı gerçek kaynak adları DEĞİL, birleştirilmiş "Kaynak Türü"
   hücreleri taşıyor — gerçek kaynak adları 1. satırda.** `t4_oku()` bunu
   dinamik tespit ediyor (0. satırda "Kaynak Türü" metni varsa 1. satıra
   kayıyor) — diğer 6 ayda (Mart/Nisan/Mayıs/Ekim/Kasım/Aralık) 0. satır
   zaten doğrudan kaynak adları taşıyor, kod her iki durumu da kapsıyor.
5. **T4'ün Toplam kolonu bazı aylarda BOŞ başlıklı** (Ağustos'ta son kolon
   başlığı yalnızca boşluk) — metin arama yerine POZİSYONA güveniliyor
   (tüm 12 ayda toplam kolonu doğrulandı: hep SONUNCU kolon).
6. **Temmuz 2016'nın T11 tablosunda ADANA satırı KAYIP** — alfabetik
   sırada Adana'nın olması gereken yerde tablo kendi başlık satırını
   İKİNCİ KEZ tekrarlıyor (gerçek Adana verisi YOK, sayfa-sonu
   tekrarıyla ÜZERİNE YAZILMIŞ görünüyor — gerçek bir EPDK kaynak
   hatası). Kod TAHMİN ETMİYOR: başlık-tekrarı satırı atlanınca (81
   değil 80 il kalır) `t11_oku()`'nun kendi satır-sayısı doğrulaması
   ValueError fırlatır, ay `isle_ay()`'in dış try/except'i tarafından
   BEKLEMEDE işaretlenip atlanır (yalnız Temmuz T11 — T4 ayrı bir tablo/
   batch, etkilenmedi, doğrulandı).
7. **Kaynak alias — "Güneş (Yoğunlaştırılmış)"** (TAM kelime, kısaltma
   DEĞİL — 2017-2019'un "Güneş (Yoğunlş.)" kısaltmasından FARKLI bir
   varyant) Ocak-Mayıs arasında görülüyor, Ekim'den itibaren kısaltılmış
   "Güneş (Yoğunlş.)" biçimine dönüyor — HER İKİSİ de "Güneş"e eşleniyor.

Kullanım:
    python -m worker.scripts.word_2016 --ay 6                  # tek ay, gerçek yükleme
    python -m worker.scripts.word_2016                          # 2016'nın TÜMÜ
    python -m worker.scripts.word_2016 --dry-run                # yalnız parse, DB'ye YAZMA
    python -m worker.scripts.word_2016 --t4                     # T11/T10 yerine T4
"""

from __future__ import annotations

import argparse
import re
import sys
from io import BytesIO
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from docx import Document

from worker import ingest, kpi, pipeline
from worker.db import get_database_url  # import yan etkisi: .env yüklenir
from worker.parser import grup_esle as _excel_grup_esle
from worker.parser import il_kodu_bul, kaynak_esle, normalize_label, parse_sayi
from worker.scripts.word_ortak import (
    basliklari_topla,
    t4_tablosunu_bul,
    tek_aday_bul,
)

KLASOR_VARSAYILAN = Path(r"C:\Users\adama\Downloads\EPDK Verileri")

# ay(int) -> dosya adı. dokumanlar/08_word_2016_2022_kapsam.md'deki envanter
# taramasıyla bulundu (Ocak zaten 07'de çözülmüştü). Tüm 12 ay OKUNAKLI
# dosya adı taşıyor (2017/2018/2019'un opak hash'lerinden FARKLI) — hiçbir
# ay için çoklu-aday belirsizliği yok (yalnız bir "20XX Yılı Elek.Piy.Gel.
# Raporu" adlı YILLIK özet dosyası ayrıca var, manifestte YOK — aylık rapor
# ailesinden ayrı, dahil edilmedi).
MANIFEST_2016: dict[int, str] = {
    1: "_PortalAdmin_Uploads_Content_FastAccess_Elk_YayinRapor_Ocak_2016d3f8d660.docx",
    2: "_PortalAdmin_Uploads_Content_FastAccess_ELEKTRİK PİYASASI SEKTÖR RAPORU 2016 ŞUBAT55b7adfc.docx",
    3: "_PortalAdmin_Uploads_Content_FastAccess_ELEKTRİK PİYASASI SEKTÖR RAPORU 2016 MART32b357d4.docx",
    4: "_PortalAdmin_Uploads_Content_FastAccess_ELEKTRİK PİYASASI SEKTÖR RAPORU 2016 NİSAN07733b8f.docx",
    5: "_PortalAdmin_Uploads_Content_FastAccess_2016 Yılı Mayıs Ayı Elektrik Piyasası Sektör Raporu1a577a52.docx",
    6: "_PortalAdmin_Uploads_Content_FastAccess_2016 Yılı Haziran Ayı Elektrik Piyasası Sektör Raporu05577902.docx",
    7: "_PortalAdmin_Uploads_Content_FastAccess_2016 TEMMUZ RAPORU-23 09 2016-14 49b2082c83.docx",
    8: "_PortalAdmin_Uploads_Content_FastAccess_2016 AĞUSTOS RAPORU-17 10 20164321051d.docx",
    9: "_PortalAdmin_Uploads_Content_FastAccess_2016 Eylül Elektrik Piyasası Sektör Raporubb0ee889.docx",
    10: "_PortalAdmin_Uploads_Content_FastAccess_Elk_Ekim_2016SekRaporuf2e11446.docx",
    11: "_PortalAdmin_Uploads_Content_FastAccess_2016 yılı Kasım Ayı Elektrik Piyasası Sektör Raporub242c346.docx",
    12: "_PortalAdmin_Uploads_Content_FastAccess_2016 ARALIK RAPORU (2)af75a78a.docx",
}

# Taksonomi kararı UYGULANDI (RENAME, dokumanlar/08) — 2016'da da AYNI eski
# taksonomi doğrulandı. dokumanlar/08 devamı — Şubat 2016'nın grup başlıkları
# TAMAMEN BÜYÜK HARF ("TARIMSAL SULAMA", "TİCARETHANE" — diğer aylar mixed-
# case) — normal string eşitliğiyle YAKALANMAZ (Türkçe İ/I büyük/küçük harf
# dönüşümü Python'ın .upper()'ıyla tutarsız). Bu yüzden alias sözlüğü
# worker/parser.py:normalize_label() (Türkçe-güvenli BÜYÜK HARF + sadeleştirme)
# ile ÖNCEDEN normalize edilip aranıyor — 2017-2022'nin ham .upper()/plain-dict
# desenini burada BİLİNÇLİ OLARAK değiştiriyoruz.
_GRUP_TAKMA_ADLAR = {
    "Kamu ve Özel Hiz. Sek. ile Diğer": "Kamu ve Özel Hizmetler",
    "Kamu ve Özel Hizmetler Sektörü ile Diğer": "Kamu ve Özel Hizmetler",
    "Tarımsal Faaliyetler": "Tarımsal",
    "Ticarethane": "Kamu ve Özel Hizmetler",
    "Tarımsal Sulama": "Tarımsal",
}
_GRUP_TAKMA_ADLAR_NORM = {normalize_label(k): v for k, v in _GRUP_TAKMA_ADLAR.items()}
_ATLA_ETIKETLERI = {
    "Genel Toplam",
    "GENEL TOPLAM",
    "Toplam",
    "İl Toplam",
    "Türkiye",
    "TÜRKİYE",
    "Pay",
    "Pay(%)",
    "Pay (%)",
    "Pay\n(%)",
    "Payı",
    "Payı (%)",
}
_ATLA_ETIKETLERI_NORM = {normalize_label(e) for e in _ATLA_ETIKETLERI}


def grup_esle_zorunlu(metin: str) -> str | None:
    # 2016'da bazı kolon başlıkları iç satır-sonu taşıyor (örn.
    # "Tarımsal\n Sulama") — kaynak_esle_zorunlu()'daki AYNI normalize
    # deseni: iç boşluk/satır sonları TEK boşluğa indirgenir.
    temiz = " ".join(metin.split())
    if normalize_label(temiz) in _ATLA_ETIKETLERI_NORM:
        return None
    normalize_edilmis = normalize_label(temiz)
    if normalize_edilmis in _GRUP_TAKMA_ADLAR_NORM:
        return _GRUP_TAKMA_ADLAR_NORM[normalize_edilmis]
    grup = _excel_grup_esle(temiz)
    if grup is None:
        raise ValueError(
            f"Tanınmayan tüketici grubu etiketi: {temiz!r} — "
            "worker/scripts/word_2016.py: _GRUP_TAKMA_ADLAR'a eklenmeli mi "
            "kontrol et (yeni bir ay yeni bir kısaltma/varyant getirmiş olabilir)."
        )
    return grup


# dokumanlar/08 devamı — 2016'da "Güneş (Yoğunlaştırılmış)" ay ay FARKLI
# kısaltmalarla yazılmış (Ocak/Mart-Mayıs tam kelime, Haziran "Yoğun.",
# Temmuz/Ağustos "Yoğunl.", Kasım/Aralık "Yoğunlş." — hepsi AYNI kaynağı
# ifade ediyor, EPDK'nın kendi şablonu ay ay tutarsız). Ekim'de ayrıca
# "Güneş (Fotovoltaik)" (worker/parser.py:kaynak_esle() zaten tanıyor)
# "Güneş (F.voltaik)" olarak KISALTILMIŞ. t4_oku() hepsini kanonik
# "Güneş"e TOPLAR.
_KAYNAK_TAKMA_ADLAR: dict[str, str] = {
    "Güneş (Yoğunlş.)": "Güneş",
    "Güneş (Yoğunlaştırılmış)": "Güneş",
    "Güneş (Yoğun.)": "Güneş",
    "Güneş (Yoğunl.)": "Güneş",
    "Güneş (F.voltaik)": "Güneş",
}
_KAYNAK_ATLA_ETIKETLERI = {"Genel Toplam", "Toplam", "İl Toplam"}
TUM_IL_KODLARI = set(range(1, 82))


def kaynak_esle_zorunlu(metin: str) -> str | None:
    temiz = " ".join(metin.split())
    if temiz in _KAYNAK_ATLA_ETIKETLERI:
        return None
    if temiz in _KAYNAK_TAKMA_ADLAR:
        return _KAYNAK_TAKMA_ADLAR[temiz]
    eslesme = kaynak_esle(temiz)
    if eslesme is None:
        raise ValueError(
            f"Tanınmayan kaynak türü etiketi: {temiz!r} — "
            "worker/scripts/word_2016.py: _KAYNAK_TAKMA_ADLAR'a eklenmeli mi kontrol et."
        )
    return eslesme[0]


# dokumanlar/08 devamı — Ocak/Şubat/Mart 2016'da T11 tablosunda İstanbul
# İKİ AYRI satıra bölünmüş (Nisan'dan itibaren tek "İSTANBUL" satırına
# birleşiyor). Her iki yarı da AYNI il_kodu'na (İstanbul) eşlenir,
# t11_oku()'nun dict-toplama mantığı ikisini TEK satıra toplar.
_IL_ADI_DUZELT: dict[str, str] = {
    "İST. ANADOLU": "İstanbul",
    "İST. AVRUPA": "İstanbul",
    "İSTANBUL AND.": "İstanbul",
    "İSTANBUL AVR.": "İstanbul",
}

_BILINEN_ANOMALI_SATIRLAR: set[str] = set()


def _il_adi_temizle(il_adi_ham: str) -> str:
    temiz = re.sub(r"[\n\r\t]", "", il_adi_ham).rstrip("* ").strip()
    return _IL_ADI_DUZELT.get(temiz, temiz)


_BILINEN_ETIKET_HATALARI: dict[tuple[int, int, str], tuple[str, int]] = {}


def _ay_yil_dogrula_kapak(
    kapak_baslik: str, beklenen_ay_adi: str, beklenen_yil: int, ay: int
) -> None:
    """word_2020.py:_ay_yil_dogrula_kapak() ile BİREBİR AYNI mantık. (Not:
    Kasım 2016'nın kapağında "Piyafsası" yazım hatası var — "Piyasası"
    değil — ama regex yalnız "... Yılı {Ay} Ayı" kısmını aradığından bu
    zararsız, doğrulamayı etkilemiyor.)"""
    m = re.search(r"(20\d\d)\s+Yılı\s+(\w+)\s+Ayı", kapak_baslik)
    if not m:
        raise ValueError(f"Kapak başlığından ay/yıl çıkarılamadı: {kapak_baslik!r}")
    bulunan_yil, bulunan_ay = int(m.group(1)), m.group(2)
    if bulunan_ay == beklenen_ay_adi and bulunan_yil == beklenen_yil:
        return
    bilinen = _BILINEN_ETIKET_HATALARI.get((ay, beklenen_yil, "KAPAK"))
    if bilinen == (beklenen_ay_adi, beklenen_yil):
        print(
            f"  [BİLİNEN KAYNAK HATASI] Kapak: {bulunan_ay} {bulunan_yil} "
            f"diyor ama beklenen {beklenen_ay_adi} {beklenen_yil} — devam ediliyor."
        )
        return
    raise ValueError(
        f"MANIFEST_2016 uyuşmazlığı! beklenen={beklenen_ay_adi} {beklenen_yil}, "
        f"kapağın kendi başlığı={bulunan_ay} {bulunan_yil} (başlık: {kapak_baslik!r})"
    )


def t11_oku(tbl, tarih_id: int) -> pd.DataFrame:
    """T11-karşılığı: wide format. Karar 2: Sanayi HARİÇ.

    word_2017.py:t11_oku()'dan FARKLI: 2016 Ocak/Şubat/Mart'ta İstanbul iki
    AYRI satıra bölündüğünden (bkz. modül notu), aynı il_kodu'na eşlenen
    birden fazla satır OLABİLİR — bu yüzden t4_oku()'daki AYNI
    il-başına-grup-toplamı (dict) deseni kullanılıyor, kolon sayısı kadar
    satır DOĞRUDAN değil."""
    baslik_satir = [c.text.strip() for c in tbl.rows[0].cells]
    grup_kolonlari: list[tuple[int, str]] = []
    for idx, hucre in enumerate(baslik_satir):
        if idx == 0:
            continue
        grup = grup_esle_zorunlu(hucre)
        if grup is None or grup == "Sanayi":
            continue
        grup_kolonlari.append((idx, grup))
    if not grup_kolonlari:
        raise ValueError(f"T11: hiç grup kolonu bulunamadı, başlık={baslik_satir}")

    il_toplamlari: dict[tuple[int, str], float] = {}
    for row in tbl.rows[1:]:
        hucreler = [c.text.strip() for c in row.cells]
        il_adi_ham = _il_adi_temizle(hucreler[0])
        # dokumanlar/08 devamı — Temmuz 2016'da ADANA'nın olması gereken
        # yerde tablo kendi başlık satırını ("İLLER") İKİNCİ KEZ
        # tekrarlıyor (gerçek Adana verisi kaynakta YOK) — "GENEL TOPLAM"/
        # "TOPLAM" ile AYNI şekilde atlanır. Bu durumda toplam il sayısı
        # 81'in altında kalır, aşağıdaki satır-sayısı doğrulaması bunu
        # yakalar (ay BEKLEMEDE işaretlenir, TAHMİN EDİLMEZ).
        if not il_adi_ham or il_adi_ham.upper() in (
            "GENEL TOPLAM",
            "TOPLAM",
            "İLLER",
            "İL",
        ):
            continue
        il_kodu = il_kodu_bul(il_adi_ham)
        if il_kodu is None:
            raise ValueError(f"T11: il_kodu bulunamadı: {il_adi_ham!r}")
        for kolon_idx, grup in grup_kolonlari:
            deger = parse_sayi(hucreler[kolon_idx])
            anahtar = (il_kodu, grup)
            il_toplamlari[anahtar] = il_toplamlari.get(anahtar, 0.0) + (
                deger if deger is not None else 0.0
            )

    satirlar = [
        {
            "il_kodu": il_kodu,
            "tarih_id": tarih_id,
            "grup": grup,
            "baglanti": "dagitim",
            "tuketim_mwh": deger,
        }
        for (il_kodu, grup), deger in il_toplamlari.items()
    ]
    df = pd.DataFrame(
        satirlar, columns=["il_kodu", "tarih_id", "grup", "baglanti", "tuketim_mwh"]
    )
    beklenen = 81 * len(grup_kolonlari)
    if len(df) != beklenen:
        raise ValueError(
            f"T11: beklenen satır {beklenen} (81 il × {len(grup_kolonlari)} grup), "
            f"gerçek {len(df)} — bir il eksik/kayıp olabilir (dokumanlar/08, "
            "Temmuz 2016 örneği gibi), TAHMİN EDİLMEDİ."
        )
    return df


def t4_oku(tbl, tarih_id: int) -> pd.DataFrame:
    """T4-karşılığı: il×kaynak matrisi, Lisanssız.

    word_2017.py:t4_oku()'dan FARKLI iki nokta (dokumanlar/08):
    (a) bazı aylarda 0. satır gerçek kaynak adları DEĞİL, birleştirilmiş
    "Kaynak Türü" hücreleri taşıyor — gerçek başlık 1. satırda, dinamik
    tespit ediliyor; (b) Toplam kolonu bazı aylarda BOŞ başlıklı, metin
    yerine POZİSYONA (hep sonuncu kolon) güveniliyor."""
    baslik_satir = [c.text.strip() for c in tbl.rows[0].cells]
    veri_baslangic = 1
    if any(h == "Kaynak Türü" for h in baslik_satir[1:]):
        # dokumanlar/08 devamı — Ocak/Şubat/Haziran/Temmuz/Ağustos/Eylül'de
        # 0. satır birleştirilmiş "Kaynak Türü" hücreleri (gerçek kaynak
        # adları 1. satırda) — diğer 6 ayda 0. satır zaten doğrudan kaynak
        # adları taşıyor.
        baslik_satir = [c.text.strip() for c in tbl.rows[1].cells]
        veri_baslangic = 2

    # dokumanlar/08 devamı — Toplam kolonunun başlığı bazı aylarda BOŞ
    # (örn. Ağustos) — metin arama yerine pozisyona güveniliyor (tüm 12
    # ayda doğrulandı: toplam kolonu hep SONUNCU kolon).
    toplam_kolon_idx = len(baslik_satir) - 1

    kaynak_kolonlari: list[tuple[int, str]] = []
    for idx, hucre in enumerate(baslik_satir):
        if idx == 0 or idx == toplam_kolon_idx:
            continue
        kaynak = kaynak_esle_zorunlu(hucre)
        if kaynak is None:
            continue
        kaynak_kolonlari.append((idx, kaynak))
    if not kaynak_kolonlari:
        raise ValueError(f"T4: hiç kaynak kolonu bulunamadı, başlık={baslik_satir}")

    satirlar = []
    gorulen_iller: set[int] = set()
    tum_kaynaklar = sorted({kaynak for _, kaynak in kaynak_kolonlari})
    genel_toplam_deger: float | None = None
    for row in tbl.rows[veri_baslangic:]:
        hucreler = [c.text.strip() for c in row.cells]
        il_adi_ham = _il_adi_temizle(hucreler[0])
        if not il_adi_ham:
            continue
        if il_adi_ham.upper() in ("GENEL TOPLAM", "TOPLAM"):
            genel_toplam_deger = parse_sayi(hucreler[toplam_kolon_idx])
            continue
        if il_adi_ham.upper() in ("İLLER", "İL"):
            continue
        if il_adi_ham in _BILINEN_ANOMALI_SATIRLAR:
            print(
                f"  [BİLİNEN KAYNAK ANOMALİSİ] T4: {il_adi_ham!r} satırı atlandı (il_kodu yok, küçük değer)"
            )
            continue
        il_kodu = il_kodu_bul(il_adi_ham)
        if il_kodu is None:
            raise ValueError(f"T4: il_kodu bulunamadı: {il_adi_ham!r}")
        gorulen_iller.add(il_kodu)
        il_toplam: dict[str, float] = dict.fromkeys(tum_kaynaklar, 0.0)
        for kolon_idx, kaynak in kaynak_kolonlari:
            deger = parse_sayi(hucreler[kolon_idx])
            il_toplam[kaynak] += deger if deger is not None else 0.0
        for kaynak, deger in il_toplam.items():
            satirlar.append(
                {
                    "il_kodu": il_kodu,
                    "tarih_id": tarih_id,
                    "kaynak": kaynak,
                    "lisans": "Lisanssız",
                    "kurulu_guc_mw": deger,
                }
            )

    eksik_iller = TUM_IL_KODLARI - gorulen_iller
    for il_kodu in sorted(eksik_iller):
        for kaynak in tum_kaynaklar:
            satirlar.append(
                {
                    "il_kodu": il_kodu,
                    "tarih_id": tarih_id,
                    "kaynak": kaynak,
                    "lisans": "Lisanssız",
                    "kurulu_guc_mw": 0.0,
                }
            )

    df = pd.DataFrame(
        satirlar, columns=["il_kodu", "tarih_id", "kaynak", "lisans", "kurulu_guc_mw"]
    )
    if genel_toplam_deger is None:
        raise ValueError("T4: 'Genel Toplam' satırı bulunamadı — doğrulama yapılamadı")
    hesaplanan = float(df["kurulu_guc_mw"].sum())
    fark = abs(hesaplanan - genel_toplam_deger)
    tolerans = max(0.5, abs(genel_toplam_deger) * 0.001)
    if fark > tolerans:
        raise ValueError(
            f"T4: hesaplanan toplam {hesaplanan:.2f} MW, tablonun kendi Genel "
            f"Toplam'ı {genel_toplam_deger:.2f} MW — fark {fark:.2f} MW toleransı "
            f"({tolerans:.2f}) aşıyor"
        )
    return df


def isle_ay(
    conn,
    *,
    klasor: Path,
    ay: int,
    actor_name: str,
    dry_run: bool = False,
) -> pipeline.IslemSonucu | None:
    """word_2020.py:isle_ay() ile BENZER akış — T10 burada tablo olarak HİÇ
    yok, bu yüzden T10 ARAMASI da (yalnız okuması değil) try/except içinde."""
    dosya_adi = MANIFEST_2016[ay]
    yol = klasor / dosya_adi
    yil = 2016
    tarih_id = yil * 100 + ay
    ay_adi = ingest.AY_ADLARI[ay]
    ay_yil = f"{ay_adi} {yil}"
    source_period = f"{yil}-{ay:02d}"

    print(f"\n=== {ay_yil} — {dosya_adi} ===")

    if not dry_run:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ib.batch_id, ib.status FROM ingestion_batch ib
                JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
                WHERE sa.source_type = 'epdk_aylik_word' AND sa.source_period = %s
                  AND ib.parser_version = %s AND ib.status != 'failed'
                ORDER BY ib.batch_id
                """,
                (source_period, "word-2016-v1"),
            )
            mevcut = cur.fetchall()
        if mevcut:
            print(f"  [ATLA] {source_period} zaten işlenmiş: {mevcut}")
            return None

    icerik = yol.read_bytes()
    doc = Document(BytesIO(icerik))
    basliklar = basliklari_topla(doc)

    kapak_baslik = basliklar[0][1] if basliklar else ""
    _ay_yil_dogrula_kapak(kapak_baslik, ay_adi, yil, ay)
    print(f"  Kapak başlık: {kapak_baslik!r} (ay/yıl doğrulandı)")

    # dokumanlar/08 devamı — "Tablo 2.3 ... Tüketici Türü Bazında Dağılımı"
    # (il kırılımı YOK) da bu alt-diziyi taşıdığından arama metni "İl ve
    # Tüketici Türü Bazında Dağılımı" olarak GENİŞLETİLDİ (yalnız Tablo
    # 2.4'e özgü, tek aday kaldığı doğrulandı — tüm 12 ay).
    t11_tbl, t11_baslik = tek_aday_bul(
        basliklar,
        icerir=["İl ve Tüketici Türü Bazında Dağılımı"],
        etiket="T11",
    )
    print(f"  T11 başlık: {t11_baslik!r}")

    tuketim_ham = t11_oku(t11_tbl, tarih_id)
    print(
        f"  T11: {len(tuketim_ham)} satır, grup={sorted(tuketim_ham['grup'].unique())}, "
        f"toplam={tuketim_ham['tuketim_mwh'].sum():,.2f} MWh"
    )

    # dokumanlar/08 devamı — T10 (Tüketici Sayısı) tablosu 2016'da hiçbir
    # ayda YOK (2017-2020'nin "tablo var, grup kırılımı yok" sorunundan
    # FARKLI — burada başlık aramasının KENDİSİ 0 aday bulur, ValueError
    # fırlatır). Tüm 12 ay için önceden doğrulandı (dokumanlar/08). Yine de
    # "asla tahmin etme" ilkesi gereği KÖRÜ KÖRÜNE atlanmıyor — arama
    # gerçekten yapılıyor; beklenmedik şekilde bir aday BULUNURSA (teşhisle
    # ÇELİŞEN bir durum) sessizce yok sayılmaz, GÜRÜLTÜLÜ biçimde
    # başarısız olunur (ay BEKLEMEDE işaretlenir, araştırılması gerekir).
    try:
        tek_aday_bul(basliklar, icerir=["Tüketici Sayısı"], etiket="T10")
    except ValueError:
        print(
            "  [T10 KAYNAKTA YOK] 2016 raporunda Tüketici Sayısı tablosu hiç "
            "basılmamış (dokumanlar/08) — kapsam_disi olarak işaretlenecek."
        )
    else:
        raise ValueError(
            "T10: 2016 için 'Tüketici Sayısı' içeren bir tablo BULUNDU — "
            "dokumanlar/08'deki teşhisle (tüm 12 ayda tablo yok) ÇELİŞİYOR, "
            "kod güncellenmeden bu ay işlenemez."
        )

    if dry_run:
        print("  [DRY-RUN] DB'ye yazılmadı.")
        return None

    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik_word",
        dosya_adi=dosya_adi,
        icerik=icerik,
        donem_tipi="aylik",
        source_period=source_period,
        uploaded_by=None,
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, "word-2016-v1", "1")
    if not ingest.batch_sahiplen(conn, batch_id):
        print(f"  [ATLA] batch_id={batch_id} zaten sahiplenilmiş/işlenmiş.")
        return None

    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)

    sonuc = pipeline.IslemSonucu(batch_id=batch_id)
    audit_tablolar: dict[str, dict[str, object]] = {}

    dogrulanan_t = kpi.dogrula_tuketim(tuketim_ham)
    yuklenen_t, atlanan_t = ingest.fact_tuketim_yukle(
        conn, dogrulanan_t.kabul, batch_id
    )
    sonuc.tablolar["fact_tuketim"] = pipeline.TabloSonucu(
        toplam=len(tuketim_ham),
        red=len(dogrulanan_t.red),
        karantina=len(dogrulanan_t.karantina),
        yuklenen=yuklenen_t,
        atlanan=atlanan_t,
    )
    audit_tablolar["fact_tuketim"] = {
        "toplam": len(tuketim_ham),
        "red": len(dogrulanan_t.red),
        "karantina": len(dogrulanan_t.karantina),
        "yuklenen": yuklenen_t,
        "atlanan": atlanan_t,
        "red_satirlari": dogrulanan_t.red.to_dict("records"),
    }
    audit_tablolar["fact_abone"] = {
        "toplam": 0,
        "not": "kaynakta yok — 2016 raporunda Tüketici Sayısı tablosu hiç "
        "basılmamış, aşağıda kapsam_disi ile işaretlendi.",
    }

    if dogrulanan_t.red.shape[0] or dogrulanan_t.karantina.shape[0]:
        print(
            f"  [DİKKAT] fact_tuketim: red={len(dogrulanan_t.red)} karantina={len(dogrulanan_t.karantina)}"
        )

    toplam_satir = len(tuketim_ham)
    toplam_yuklenen = yuklenen_t
    toplam_atlanan = toplam_satir - toplam_yuklenen

    ingest.batch_durumu_guncelle(
        conn,
        batch_id,
        "running",
        total_row_count=toplam_satir,
        accepted_row_count=toplam_yuklenen,
        rejected_row_count=toplam_atlanan,
    )
    ingest.audit_log_yaz(
        conn,
        table_name="ingestion_batch",
        record_id=batch_id,
        action_type="INSERT",
        actor_name=actor_name,
        payload={
            "olay": "ingest_tamamlandi",
            "tarih_id": tarih_id,
            "kaynak": "word_2016",
            "tablolar": audit_tablolar,
            "not": "T13/T1-karşılığı bu turda YOK (Karar 1 & 3, aşağıda kapsam_disi "
            "ile işaretlendi). T4-karşılığı AYRI bir batch'te — bkz. isle_ay_t4().",
        },
    )

    pipeline.kapsam_disi_isaretle(
        conn,
        tarih_id=tarih_id,
        fact_tablosu="fact_serbest_tuketici",
        sebep="Word (.docx) kaynağında Serbest Tüketici tablosu hiç bulunmuyor "
        "(dokumanlar/08_word_2016_2022_kapsam.md Bulgu 3).",
        karar_referansi="Karar 1",
    )
    pipeline.kapsam_disi_isaretle(
        conn,
        tarih_id=tarih_id,
        fact_tablosu="fact_abone",
        sebep="Word (.docx) kaynağında 2016 raporlarında Tüketici Sayısı tablosu "
        "hiç basılmamış (2017-2020'nin il-only yapısından FARKLI — tablo yok) "
        "(dokumanlar/08_word_2016_2022_kapsam.md).",
        karar_referansi="08_word_2016_2022_kapsam.md",
    )

    uygun, sebep = pipeline.otomatik_onaya_uygun(sonuc)
    print(f"  otomatik_onaya_uygun() = {uygun}" + (f" ({sebep})" if sebep else ""))
    print(
        "  [NOT] onayla ÇAĞRILMADI (gece-boyu kural) — batch running/is_active=false kalıyor."
    )
    return sonuc


def isle_ay_t4(
    conn,
    *,
    klasor: Path,
    ay: int,
    actor_name: str,
    dry_run: bool = False,
) -> pipeline.IslemSonucu | None:
    """T4-karşılığı (fact_uretim, Lisanssız) için AYRı batch — word_2017.py:
    isle_ay_t4() ile BİREBİR AYNI mantık."""
    dosya_adi = MANIFEST_2016[ay]
    yol = klasor / dosya_adi
    yil = 2016
    tarih_id = yil * 100 + ay
    ay_adi = ingest.AY_ADLARI[ay]
    source_period = f"{yil}-{ay:02d}"
    parser_version = "word-2016-t4-v1"

    print(f"\n=== T4 {ay_adi} {yil} — {dosya_adi} ===")

    if not dry_run:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ib.batch_id, ib.status FROM ingestion_batch ib
                JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
                WHERE sa.source_type = 'epdk_aylik_word' AND sa.source_period = %s
                  AND ib.parser_version = %s AND ib.status != 'failed'
                ORDER BY ib.batch_id
                """,
                (source_period, parser_version),
            )
            mevcut = cur.fetchall()
        if mevcut:
            print(f"  [ATLA] T4 {source_period} zaten işlenmiş: {mevcut}")
            return None

    icerik = yol.read_bytes()
    doc = Document(BytesIO(icerik))
    basliklar = basliklari_topla(doc)

    t4_tbl, t4_baslik = t4_tablosunu_bul(basliklar)
    print(f"  T4 başlık: {t4_baslik!r}")

    uretim_ham = t4_oku(t4_tbl, tarih_id)
    print(
        f"  T4: {len(uretim_ham)} satır, kaynak={sorted(uretim_ham['kaynak'].unique())}, "
        f"toplam={uretim_ham['kurulu_guc_mw'].sum():,.2f} MW (Genel Toplam ile doğrulandı)"
    )

    if dry_run:
        print("  [DRY-RUN] DB'ye yazılmadı.")
        return None

    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik_word",
        dosya_adi=dosya_adi,
        icerik=icerik,
        donem_tipi="aylik",
        source_period=source_period,
        uploaded_by=None,
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, parser_version, "1")
    if not ingest.batch_sahiplen(conn, batch_id):
        print(f"  [ATLA] batch_id={batch_id} zaten sahiplenilmiş/işlenmiş.")
        return None

    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)

    sonuc = pipeline.IslemSonucu(batch_id=batch_id)
    dogrulanan = kpi.dogrula_uretim(uretim_ham)
    yuklenen, atlanan = ingest.fact_uretim_yukle(conn, dogrulanan.kabul, batch_id)
    sonuc.tablolar["fact_uretim"] = pipeline.TabloSonucu(
        toplam=len(uretim_ham),
        red=len(dogrulanan.red),
        karantina=0,
        yuklenen=yuklenen,
        atlanan=atlanan,
    )
    audit_tablolar = {
        "fact_uretim": {
            "toplam": len(uretim_ham),
            "red": len(dogrulanan.red),
            "yuklenen": yuklenen,
            "atlanan": atlanan,
            "red_satirlari": dogrulanan.red.to_dict("records"),
        }
    }

    if dogrulanan.red.shape[0]:
        print(f"  [DİKKAT] fact_uretim: red={len(dogrulanan.red)}")

    ingest.batch_durumu_guncelle(
        conn,
        batch_id,
        "running",
        total_row_count=len(uretim_ham),
        accepted_row_count=yuklenen,
        rejected_row_count=len(uretim_ham) - yuklenen,
    )
    ingest.audit_log_yaz(
        conn,
        table_name="ingestion_batch",
        record_id=batch_id,
        action_type="INSERT",
        actor_name=actor_name,
        payload={
            "olay": "ingest_tamamlandi",
            "tarih_id": tarih_id,
            "kaynak": "word_2016_t4",
            "tablolar": audit_tablolar,
            "not": "Yalnız T4 (Lisanssız) - T1 (Lisanslı) kaynakta yok (Karar 3), "
            "aşağıda kapsam_disi ile işaretlendi.",
        },
    )

    pipeline.kapsam_disi_isaretle(
        conn,
        tarih_id=tarih_id,
        fact_tablosu="fact_uretim",
        nitelik="lisans_durumu=Lisanslı",
        sebep="Word (.docx) kaynağında Lisanslı kurulu güç için il×kaynak birleşik "
        "tablo yok (dokumanlar/08_word_2016_2022_kapsam.md Bulgu 2).",
        karar_referansi="Karar 3",
    )

    uygun, sebep = pipeline.otomatik_onaya_uygun(sonuc)
    print(f"  otomatik_onaya_uygun() = {uygun}" + (f" ({sebep})" if sebep else ""))
    print(
        "  [NOT] onayla ÇAĞRILMADI (gece-boyu kural) — batch running/is_active=false kalıyor."
    )
    return sonuc


def main() -> int:
    ap = argparse.ArgumentParser(
        description="EPP: 2016 Word raporlarını yükle (tek seferlik)"
    )
    ap.add_argument("--ay", type=int, choices=range(1, 13), help="Yalnız bu ayı işle")
    ap.add_argument("--klasor", type=Path, default=KLASOR_VARSAYILAN)
    ap.add_argument("--actor", default="manual-cli:word-2016")
    ap.add_argument(
        "--dry-run", action="store_true", help="Yalnız parse et, DB'ye YAZMA"
    )
    ap.add_argument("--t4", action="store_true", help="T11/T10 yerine YALNIZ T4'ü işle")
    # KESİN KURAL: --onayla YOK, BİLİNÇLİ OLARAK.
    args = ap.parse_args()

    aylar = [args.ay] if args.ay else sorted(MANIFEST_2016)
    isleyici = isle_ay_t4 if args.t4 else isle_ay

    if args.dry_run:
        for ay in aylar:
            try:
                isleyici(
                    None, klasor=args.klasor, ay=ay, actor_name=args.actor, dry_run=True
                )
            except Exception as e:  # noqa: BLE001 - gece-boyu kural: bir ay hata verirse BEKLEMEDE say, sıradakine geç
                print(f"  [BEKLEMEDE] {ingest.AY_ADLARI[ay]} 2016 dry-run'da hata: {e}")
        return 0

    import psycopg

    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        for ay in aylar:
            try:
                sonuc = isleyici(conn, klasor=args.klasor, ay=ay, actor_name=args.actor)
                conn.commit()
            except Exception as e:  # noqa: BLE001 - gece-boyu kural: bir ay hata verirse BEKLEMEDE say, sıradakine geç
                conn.rollback()
                print(
                    f"  [BEKLEMEDE] {ingest.AY_ADLARI[ay]} 2016 işlenirken hata oluştu, "
                    f"bu ay ATLANDI (ROLLBACK), sıradaki aya geçiliyor: {e}"
                )
                continue
            if sonuc is None:
                continue
            # KESİN KURAL: onayla.py / pipeline.batch_onayla() BURADA ÇAĞRILMAZ.
    return 0


if __name__ == "__main__":
    sys.exit(main())
