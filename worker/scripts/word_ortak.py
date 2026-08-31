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

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


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
