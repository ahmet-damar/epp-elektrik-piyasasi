"""EPP — Word (.docx) EPDK raporları için ORTAK çekirdek yardımcılar.

Bu modül TEK SEFERLİK bir tarihsel veri aktarımının bir parçasıdır —
worker/parser.py (kalıcı Excel parser) DEĞİL. Kod, gelecekte hiç
görmeyeceği bir formatla karşılaşmayacak; bu yüzden burada YALNIZCA
gerçekten yıl-bağımsız olan (tablo/paragraf gezinme, sayısal/il eşleme)
kısım var. Sütun düzeni, tablo başlık metinleri gibi format-spesifik bilgi
BURADA DEĞİL, her yılın kendi tarifinde (örn. worker/scripts/word_2024.py).

Bkz. dokumanlar/07_word_parser_kapsam.md — "Mimari Kapsam Netliği" ve
Bulgu 1/2 (neden bu ayrım, neden metin arama sabit index yerine).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from docx.document import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from worker.parser import parse_sayi


def gez(document: Document):
    """document.element.body içindeki paragraf/tablo elemanlarını SIRAYLA
    (orijinal doküman sırasında) döndürür. python-docx'in resmi API'si
    (document.tables) bu sırayı vermez — bkz. Bulgu 1."""
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def basliklari_topla(document: Document) -> list[tuple[Table, str]]:
    """Her tablonun HEMEN ÖNCEKİ dolu paragraf metnini döndürür — metin
    aramasıyla tablo bulmanın temeli (bkz. Bulgu 2: sabit index'e ASLA
    güvenilmez, Word'ün kendi "Tablo N.M" alan-kodu numaralandırması
    boş render edilebiliyor)."""
    sonuc: list[tuple[Table, str]] = []
    son_metin = ""
    for item in gez(document):
        if isinstance(item, Paragraph):
            if item.text.strip():
                son_metin = item.text.strip()
        elif isinstance(item, Table):
            sonuc.append((item, son_metin))
    return sonuc


def tek_aday_bul(
    basliklar: list[tuple[Table, str]],
    *,
    icerir: list[str],
    icermez: list[str] = (),  # type: ignore[assignment]
    regex_disla: str | None = None,
    etiket: str = "",
) -> tuple[Table, str]:
    """`basliklar` içinden TÜM `icerir` alt-dizilerini taşıyan, HİÇBİR
    `icermez` alt-dizisini taşımayan ve (varsa) regex_disla'ya UYMAYAN tam
    olarak 1 aday bulmayı ZORUNLU kılar. Birden fazla/hiç aday bulunursa
    ValueError fırlatır — sessizce yanlış tabloyu almak yerine gürültülü
    başarısızlık ("göz açık tut, sessizce geçme" ilkesi)."""
    adaylar = []
    for tbl, baslik in basliklar:
        if not all(s in baslik for s in icerir):
            continue
        if any(s in baslik for s in icermez):
            continue
        if regex_disla and re.search(regex_disla, baslik):
            continue
        adaylar.append((tbl, baslik))
    if len(adaylar) != 1:
        adaylar_str = "\n".join(f"  - {b!r}" for _, b in adaylar) or "  (yok)"
        raise ValueError(
            f"{etiket}: TAM 1 aday beklenirdi, {len(adaylar)} bulundu:\n{adaylar_str}"
        )
    return adaylar[0]


def hedef_donem_kolonu_bul(
    donem_satiri: list[str],
    baslik_satiri: list[str],
    hedef_ay_yil: str,
    baslik_iceren: str,
) -> int:
    """Dönemler-arası-karşılaştırma tablolarında (T10/T9-karşılığı gibi)
    hedef döneme ait kolonu METİN aramasıyla bulur. Hücre metni
    '2024\\nMart' gibi satır-içi kesik/ters sıralı olabilir (gerçek veride
    doğrulandı) — kelime bazlı, sırasız karşılaştırma yapılır."""
    hedef_kelimeler = set(hedef_ay_yil.split())
    for idx, (donem, baslik) in enumerate(zip(donem_satiri, baslik_satiri)):
        donem_kelimeler = set(donem.split())
        if hedef_kelimeler.issubset(donem_kelimeler) and baslik_iceren in baslik:
            return idx
    raise ValueError(
        f"Hedef dönem {hedef_ay_yil!r} için {baslik_iceren!r} içeren kolon bulunamadı.\n"
        f"donem_satiri={donem_satiri}\nbaslik_satiri={baslik_satiri}"
    )


def t4_tablosunu_bul(basliklar: list[tuple[Table, str]]) -> tuple[Table, str]:
    """T4-karşılığı (fact_uretim, Lisanssız): 'Lisanssız Elektrik Kurulu
    Gücünün İllere ve Kaynaklara Göre Dağılımı (MW)' — il×kaynak BİRLEŞİK
    tek tablo. Bkz. dokumanlar/07_word_parser_kapsam.md Bulgu 5: 4 farklı
    yıl/şablonda (2023 iki şablonu + 2024 + 2025) bu başlık METNİ birebir
    aynı bulundu — yıl bağımsız, EPDK'nın rapor formatının sabit bir
    parçası (yalnız tablo NUMARASI ve kaynak kolon SIRASI/SAYISI değişken,
    bkz. word_2023.py/word_2024.py/word_2025.py'deki t4_oku()).

    T1'in (Lisanslı) BÖYLE bir birleşik tablosu YOK (Bulgu 5, madde 1) —
    bu fonksiyon T1 için KULLANILMAZ, Karar 3 gereği T1 tamamen kapsam
    dışı."""
    return tek_aday_bul(
        basliklar,
        icerir=["Lisanssız Elektrik Kurulu Gücünün İllere ve Kaynaklara Göre Dağılımı"],
        etiket="T4",
    )


def grup_kolonlarini_coz(
    baslik_satir: list[str], grup_esle_zorunlu: Callable[[str], str | None]
) -> list[tuple[int, str]]:
    """T11 (il×grup) tablosunun başlık (0.) satırından grup kolonlarını
    çözer — TÜM gruplar (Sanayi DAHİL), 0. kolon (İl/İller başlığı)
    ATLANIR. Her yılın t11_oku()'sunda AYNEN tekrarlanan (ve `grup ==
    "Sanayi"` filtresiyle Karar 2'ye uydurulan) döngünün TEK, PAYLAŞILAN
    hâli — bkz. dokumanlar/06_canli_veri_operasyon_gunlugu.md 2026-09-05
    kaydı: iki ayrı yerde iki farklı sütun→grup eşlemesi OLUŞMASIN diye
    (kullanıcı talebi) hem t11_oku() hem genel_toplam_satirini_oku() bunu
    çağırır. Hangi grubun hangi amaçla (fact_tuketim'e mi, ülke geneli
    tabloya mı) kullanılacağına dair hiçbir İŞ KURALI burada YOK — yalnız
    metin→grup eşlemesi."""
    grup_kolonlari: list[tuple[int, str]] = []
    for idx, hucre in enumerate(baslik_satir):
        if idx == 0:
            continue
        grup = grup_esle_zorunlu(hucre)
        if grup is None:
            continue
        grup_kolonlari.append((idx, grup))
    if not grup_kolonlari:
        raise ValueError(f"Hiç grup kolonu bulunamadı, başlık={baslik_satir}")
    return grup_kolonlari


def genel_toplam_satirini_oku(
    tbl: Table, grup_esle_zorunlu: Callable[[str], str | None]
) -> dict[str, float]:
    """T11 tablosunun (il×grup — fact_tuketim için ZATEN bulunmuş/okunacak
    AYNI Table nesnesi) KENDİ "Genel Toplam" satırından, TÜM gruplar
    (Sanayi DAHİL) için ülke geneli tek-ay tüketim değerini okur.

    Karar 2 (dokumanlar/07_word_parser_kapsam.md) bu fonksiyonu HİÇ
    ETKİLEMEZ — fact_tuketim'e hiçbir şey yazmaz, yalnız ayrı bir ülke-
    geneli tablo için veri üretir.

    KRİTİK — çağıranın t11_oku()'suyla AYNI sütun→grup eşlemesini
    (`grup_kolonlarini_coz`, dolayısıyla AYNI `_GRUP_TAKMA_ADLAR`) ve
    AYNI `worker.parser.parse_sayi()` Türkçe sayı ayrıştırıcısını (nokta
    binlik, virgül ondalık) kullanır — iki farklı yerde iki farklı
    eşleme/ayrıştırma mantığı OLUŞTURULMAZ (kullanıcı talebi, 2026-09-05).

    "Genel Toplam" satırı, t11_oku()'nun il-toplama döngüsünün (bu satırı
    kendi amacı için ATLADIĞI/filtrelediği) dışında, HAM `tbl.rows`
    üzerinden AYRICA aranır — o döngünün ürettiği filtrelenmiş bir ara
    veri yapısına GÜVENİLMEZ (kullanıcı talebi: bu satırın il-eşlemesi
    sırasında elenmediğinden BAĞIMSIZ olarak emin olunması gerekiyordu).

    120 ayın (2016-2025) TAMAMINDA gerçek docx'lere karşı doğrulandı —
    her ayda tam 1 "Genel Toplam"/"Toplam" satırı bulundu, sıfır hata."""
    baslik_satir = [c.text.strip() for c in tbl.rows[0].cells]
    grup_kolonlari = grup_kolonlarini_coz(baslik_satir, grup_esle_zorunlu)

    for row in tbl.rows[1:]:
        hucreler = [c.text.strip() for c in row.cells]
        etiket = re.sub(r"[\n\r\t]", "", hucreler[0]).strip().upper()
        if etiket in ("GENEL TOPLAM", "TOPLAM"):
            degerler: dict[str, float] = {}
            for idx, grup in grup_kolonlari:
                deger = parse_sayi(hucreler[idx])
                if deger is None:
                    raise ValueError(
                        f"Ülke geneli: 'Genel Toplam' satırında {grup!r} için "
                        f"sayısal olmayan değer: {hucreler[idx]!r} (tam satır: {hucreler})"
                    )
                degerler[grup] = deger
            return degerler

    raise ValueError(
        "Ülke geneli: T11 tablosunda 'Genel Toplam'/'Toplam' satırı bulunamadı — "
        "bu satır ZORUNLU (tahmin edilmez, dokumanlar/06_canli_veri_operasyon_gunlugu.md)."
    )
