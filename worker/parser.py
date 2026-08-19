"""EPP — EPDK aylık ek (xlsx) anchor-tabanlı parser (Faz 0).

Kaynak: dokumanlar/05_kaynak_dosya_sozlesmesi.md (Ek F).
Parser sabit hücreye güvenmez; değişmez etiketleri (tablo başlığı, sütun adı,
'TÜRKİYE' satırı) arar. NOT (dokumanlar/05_...): "v0.1 — Faz 0'da gerçek 2016+
dosyalarla doğrulanacak" — bu modül henüz gerçek EPDK dosyalarıyla
doğrulanmadı; yalnızca sentetik test fixture'ları ile test edilmiştir.

Bu ilk sürüm T1 (kurulu güç), T2/T3 (üretim), T9/T10 (abone) ve T11
(P0-2 kritik: tüketim iletim/dağıtım) tablolarını kapsar. T4-T8, T12, T13
sonraki iterasyonda eklenecektir.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

# ---------------------------------------------------------------------------
# Normalizasyon (dokumanlar/05_kaynak_dosya_sozlesmesi.md — Çapa Tabanlı Okuma)
# ---------------------------------------------------------------------------

_TR_SADE = str.maketrans(
    {
        "ç": "C",
        "Ç": "C",
        "ğ": "G",
        "Ğ": "G",
        "ı": "I",
        "İ": "I",
        "i": "I",
        "ö": "O",
        "Ö": "O",
        "ş": "S",
        "Ş": "S",
        "ü": "U",
        "Ü": "U",
    }
)


def normalize_label(deger: object) -> str:
    """Trim + BÜYÜK harf + Türkçe sadeleştir (İ→I). Eşleme/çapa arama içindir."""
    if deger is None:
        return ""
    metin = str(deger).translate(_TR_SADE).upper()
    return " ".join(metin.split())


def parse_sayi(deger: object) -> float | None:
    """'1.432,404' → 1432.404. Boş hücre → None (0 DEĞİL)."""
    if deger is None:
        return None
    if isinstance(deger, int | float):
        return float(deger)
    metin = str(deger).strip()
    if metin in ("", "-", "—", "n/a", "N/A"):
        return None
    metin = metin.replace(".", "").replace(",", ".")
    try:
        return float(metin)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# İl plaka kodu (81 il — resmi plaka numaralandırması)
# ---------------------------------------------------------------------------

_IL_PLAKA_HAM: dict[str, int] = {
    "Adana": 1,
    "Adıyaman": 2,
    "Afyonkarahisar": 3,
    "Ağrı": 4,
    "Amasya": 5,
    "Ankara": 6,
    "Antalya": 7,
    "Artvin": 8,
    "Aydın": 9,
    "Balıkesir": 10,
    "Bilecik": 11,
    "Bingöl": 12,
    "Bitlis": 13,
    "Bolu": 14,
    "Burdur": 15,
    "Bursa": 16,
    "Çanakkale": 17,
    "Çankırı": 18,
    "Çorum": 19,
    "Denizli": 20,
    "Diyarbakır": 21,
    "Edirne": 22,
    "Elazığ": 23,
    "Erzincan": 24,
    "Erzurum": 25,
    "Eskişehir": 26,
    "Gaziantep": 27,
    "Giresun": 28,
    "Gümüşhane": 29,
    "Hakkari": 30,
    "Hatay": 31,
    "Isparta": 32,
    "Mersin": 33,
    "İstanbul": 34,
    "İzmir": 35,
    "Kars": 36,
    "Kastamonu": 37,
    "Kayseri": 38,
    "Kırklareli": 39,
    "Kırşehir": 40,
    "Kocaeli": 41,
    "Konya": 42,
    "Kütahya": 43,
    "Malatya": 44,
    "Manisa": 45,
    "Kahramanmaraş": 46,
    "Mardin": 47,
    "Muğla": 48,
    "Muş": 49,
    "Nevşehir": 50,
    "Niğde": 51,
    "Ordu": 52,
    "Rize": 53,
    "Sakarya": 54,
    "Samsun": 55,
    "Siirt": 56,
    "Sinop": 57,
    "Sivas": 58,
    "Tekirdağ": 59,
    "Tokat": 60,
    "Trabzon": 61,
    "Tunceli": 62,
    "Şanlıurfa": 63,
    "Uşak": 64,
    "Van": 65,
    "Yozgat": 66,
    "Zonguldak": 67,
    "Aksaray": 68,
    "Bayburt": 69,
    "Karaman": 70,
    "Kırıkkale": 71,
    "Batman": 72,
    "Şırnak": 73,
    "Bartın": 74,
    "Ardahan": 75,
    "Iğdır": 76,
    "Yalova": 77,
    "Karabük": 78,
    "Kilis": 79,
    "Osmaniye": 80,
    "Düzce": 81,
}

IL_PLAKA: dict[str, int] = {
    normalize_label(ad): kod for ad, kod in _IL_PLAKA_HAM.items()
}


def il_kodu_bul(il_adi: object) -> int | None:
    return IL_PLAKA.get(normalize_label(il_adi))


# ---------------------------------------------------------------------------
# Kaynak Türü Eşleme (dokumanlar/05_kaynak_dosya_sozlesmesi.md)
# ---------------------------------------------------------------------------

KAYNAK_ESLEME: dict[str, tuple[str, bool]] = {
    normalize_label(etiket): (kanonik, yenilenebilir)
    for etiketler, kanonik, yenilenebilir in [
        (["Akarsu", "Barajlı", "Hidrolik"], "Hidrolik", True),
        (["Rüzgar"], "Rüzgar", True),
        (["Güneş"], "Güneş", True),
        (["Jeotermal"], "Jeotermal", True),
        (["Biyokütle"], "Biyokütle", True),
        (["Doğal Gaz", "LNG"], "Doğal Gaz", False),
        (["İthal Kömür"], "İthal Kömür", False),
        (["Linyit"], "Linyit", False),
        (["Taş Kömürü"], "Taş Kömürü", False),
        (["Asfaltit"], "Asfaltit", False),
        (["Fuel Oil"], "Fuel Oil", False),
    ]
    for etiket in etiketler
}


def kaynak_esle(etiket: object) -> tuple[str, bool] | None:
    return KAYNAK_ESLEME.get(normalize_label(etiket))


# ---------------------------------------------------------------------------
# Çapa (Anchor) arama
# ---------------------------------------------------------------------------


def bul_capa(ws: Worksheet, etiket: str, min_row: int = 1) -> tuple[int, int] | None:
    """Normalize edilmiş hücre değeri `etiket`i içeren ilk hücrenin (satır, sütun) konumu."""
    hedef = normalize_label(etiket)
    if not hedef:
        return None
    for row in ws.iter_rows(min_row=min_row):
        for cell in row:
            if hedef in normalize_label(cell.value):
                return (cell.row, cell.column)
    return None


def _satirda_kolon_bul(
    ws: Worksheet, satir: int, etiket: str, min_col: int = 1, max_col: int = 60
) -> int | None:
    hedef = normalize_label(etiket)
    if not hedef:
        return None
    for col in range(min_col, max_col + 1):
        if hedef in normalize_label(ws.cell(row=satir, column=col).value):
            return col
    return None


_DURDURMA_ETIKETLERI = {"TURKIYE", "GENEL TOPLAM", "TOPLAM"}


def _il_matrisi_oku(
    ws: Worksheet,
    tablo_etiketi: str,
    il_kolon_etiketi: str = "İLLER",
) -> tuple[int, int] | None:
    """Tablo çapasını ve altındaki 'İLLER' başlık satırını bulur → (baslik_satir, il_sutun)."""
    capa = bul_capa(ws, tablo_etiketi)
    if capa is None:
        return None
    tablo_satir, _ = capa
    for satir in range(tablo_satir, tablo_satir + 10):
        kolon = _satirda_kolon_bul(ws, satir, il_kolon_etiketi)
        if kolon is not None:
            return (satir, kolon)
    return None


def _veri_satirlarini_gez(ws: Worksheet, baslik_satir: int, il_sutun: int):
    """(satir_no, il_adi) ikililerini 'TÜRKİYE/TOPLAM' veya boş hücreye kadar üretir."""
    satir = baslik_satir + 1
    while True:
        il_deger = ws.cell(row=satir, column=il_sutun).value
        if il_deger is None or str(il_deger).strip() == "":
            return
        if normalize_label(il_deger) in _DURDURMA_ETIKETLERI:
            return
        yield satir, str(il_deger).strip()
        satir += 1


# ---------------------------------------------------------------------------
# T11 — Tüketim (İLETİM/DAĞITIM) — P0-2 KRİTİK
# ---------------------------------------------------------------------------

_T11_GRUP_KOLONLARI = [
    ("Aydınlatma", "Aydınlatma", "dagitim"),
    ("Kamu", "Kamu ve Özel Hizmetler", "dagitim"),
    ("Mesken", "Mesken", "dagitim"),
    ("Sanayi-DAGITIM", "Sanayi", "dagitim"),
    ("Sanayi-ILETIM", "Sanayi", "iletim"),
    ("Tarımsal", "Tarımsal", "dagitim"),
]


def tablo11_tuketim_oku(
    ws: Worksheet, tarih_id: int, tablo_etiketi: str = "Tablo 11"
) -> pd.DataFrame:
    """T11: il × (Aydınlatma, Kamu, Mesken, Sanayi-DAĞITIM, Sanayi-İLETİM, Tarımsal).

    P0-2: Sanayi-DAĞITIM ve Sanayi-İLETİM AYRI satır (grup='Sanayi', baglanti farklı).
    """
    konum = _il_matrisi_oku(ws, tablo_etiketi)
    if konum is None:
        return pd.DataFrame(
            columns=["il", "il_kodu", "tarih_id", "grup", "baglanti", "tuketim_mwh"]
        )
    baslik_satir, il_sutun = konum

    kolon_indeksleri = [
        (_satirda_kolon_bul(ws, baslik_satir, arama_etiketi), grup, baglanti)
        for arama_etiketi, grup, baglanti in _T11_GRUP_KOLONLARI
    ]

    satirlar = []
    for satir_no, il_adi in _veri_satirlarini_gez(ws, baslik_satir, il_sutun):
        for kolon, grup, baglanti in kolon_indeksleri:
            if kolon is None:
                continue
            deger = parse_sayi(ws.cell(row=satir_no, column=kolon).value)
            satirlar.append(
                {
                    "il": il_adi,
                    "il_kodu": il_kodu_bul(il_adi),
                    "tarih_id": tarih_id,
                    "grup": grup,
                    "baglanti": baglanti,
                    "tuketim_mwh": deger,
                }
            )
    return pd.DataFrame(
        satirlar,
        columns=["il", "il_kodu", "tarih_id", "grup", "baglanti", "tuketim_mwh"],
    )


# ---------------------------------------------------------------------------
# T9/T10 — Tüketici sayısı (Abone)
# ---------------------------------------------------------------------------

_ABONE_GRUP_KOLONLARI = [
    ("Aydınlatma", "Aydınlatma"),
    ("Kamu", "Kamu ve Özel Hizmetler"),
    ("Mesken", "Mesken"),
    ("Sanayi", "Sanayi"),
    ("Tarımsal", "Tarımsal"),
]


def tablo_abone_oku(
    ws: Worksheet, tarih_id: int, tablo_etiketi: str = "Tablo 9"
) -> pd.DataFrame:
    """T9/T10: il × tüketici grubu → abone_sayisi (baglanti ayrımı YOK, dokumanlar/03)."""
    konum = _il_matrisi_oku(ws, tablo_etiketi)
    if konum is None:
        return pd.DataFrame(
            columns=["il", "il_kodu", "tarih_id", "grup", "abone_sayisi"]
        )
    baslik_satir, il_sutun = konum

    kolon_indeksleri = [
        (_satirda_kolon_bul(ws, baslik_satir, arama_etiketi), grup)
        for arama_etiketi, grup in _ABONE_GRUP_KOLONLARI
    ]

    satirlar = []
    for satir_no, il_adi in _veri_satirlarini_gez(ws, baslik_satir, il_sutun):
        for kolon, grup in kolon_indeksleri:
            if kolon is None:
                continue
            deger = parse_sayi(ws.cell(row=satir_no, column=kolon).value)
            satirlar.append(
                {
                    "il": il_adi,
                    "il_kodu": il_kodu_bul(il_adi),
                    "tarih_id": tarih_id,
                    "grup": grup,
                    "abone_sayisi": deger,
                }
            )
    return pd.DataFrame(
        satirlar, columns=["il", "il_kodu", "tarih_id", "grup", "abone_sayisi"]
    )


# ---------------------------------------------------------------------------
# T1 (kurulu güç) + T2/T3 (üretim) — il × kaynak matrisi
# ---------------------------------------------------------------------------


def _kaynak_matrisi_oku(
    ws: Worksheet, tablo_etiketi: str, tarih_id: int, deger_kolon_adi: str
) -> pd.DataFrame:
    konum = _il_matrisi_oku(ws, tablo_etiketi)
    if konum is None:
        return pd.DataFrame(
            columns=[
                "il",
                "il_kodu",
                "tarih_id",
                "kaynak",
                "yenilenebilir",
                deger_kolon_adi,
            ]
        )
    baslik_satir, il_sutun = konum

    kaynak_kolonlari = []
    for col in range(il_sutun + 1, il_sutun + 40):
        baslik_deger = ws.cell(row=baslik_satir, column=col).value
        if baslik_deger is None or str(baslik_deger).strip() == "":
            continue
        eslesme = kaynak_esle(baslik_deger)
        if eslesme is not None:
            kaynak_kolonlari.append((col, *eslesme))

    satirlar = []
    for satir_no, il_adi in _veri_satirlarini_gez(ws, baslik_satir, il_sutun):
        for kolon, kaynak, yenilenebilir in kaynak_kolonlari:
            deger = parse_sayi(ws.cell(row=satir_no, column=kolon).value)
            satirlar.append(
                {
                    "il": il_adi,
                    "il_kodu": il_kodu_bul(il_adi),
                    "tarih_id": tarih_id,
                    "kaynak": kaynak,
                    "yenilenebilir": yenilenebilir,
                    deger_kolon_adi: deger,
                }
            )
    return pd.DataFrame(
        satirlar,
        columns=[
            "il",
            "il_kodu",
            "tarih_id",
            "kaynak",
            "yenilenebilir",
            deger_kolon_adi,
        ],
    )


def tablo1_kurulu_guc_oku(
    ws: Worksheet, tarih_id: int, tablo_etiketi: str = "Tablo 1"
) -> pd.DataFrame:
    """T1: il × kaynak → kurulu_guc_mw (lisanslı)."""
    return _kaynak_matrisi_oku(ws, tablo_etiketi, tarih_id, "kurulu_guc_mw")


def tablo23_uretim_oku(
    ws: Worksheet, tarih_id: int, tablo_etiketi: str = "Tablo 2"
) -> pd.DataFrame:
    """T2/T3: il × kaynak → uretim_mwh (lisanslı)."""
    return _kaynak_matrisi_oku(ws, tablo_etiketi, tarih_id, "uretim_mwh")


def uretim_birlestir(kurulu_df: pd.DataFrame, uretim_df: pd.DataFrame) -> pd.DataFrame:
    """T1 (kurulu güç) ve T2/T3 (üretim) çıktısını fact_uretim şekline birleştirir."""
    ortak = ["il", "il_kodu", "tarih_id", "kaynak", "yenilenebilir"]
    return kurulu_df.merge(uretim_df, on=ortak, how="outer")


# ---------------------------------------------------------------------------
# Doğrulama yardımcıları (dokumanlar/05_kaynak_dosya_sozlesmesi.md — Doğrulama)
# ---------------------------------------------------------------------------


def eksik_tablolari_bul(
    wb_sheet_names: list[str], gerekli_tablolar: list[str]
) -> list[str]:
    """13 tablo mevcut mu; eksikse batch reddi (etiket eşleşmesi, sayfa adı üzerinden)."""
    mevcut = {normalize_label(ad) for ad in wb_sheet_names}
    return [t for t in gerekli_tablolar if normalize_label(t) not in mevcut]


def mutabakat_kontrol(hesaplanan: float, resmi: float, tolerans: float = 0.005) -> bool:
    """İl toplamı ↔ 'TÜRKİYE' satırı ±%0,5 mutabakat kontrolü."""
    if resmi == 0:
        return hesaplanan == 0
    return abs(hesaplanan - resmi) / abs(resmi) <= tolerans
