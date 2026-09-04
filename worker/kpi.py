"""EPP — KPI hesaplama motoru (Faz 0 + Faz 3 hava normalizasyonu).

Kaynak: dokumanlar/04_kpi_sozlesmeleri.md (Ek B), dokumanlar/05_kaynak_dosya_sozlesmesi.md (Ek F).
Girdi: is_active kabul edilmiş (dogrulanmis) DataFrame'ler. Veri kalite
kurallari (red/karantina) bu modulun dogrula_* fonksiyonlarinda uygulanir.

Faz 3 (KPI-11/12/25/26): tüm fonksiyonlar SAF kalır (bu modül hiç DB'ye
bağlanmaz) — geçmiş yıl/ay serilerini (regresyon girdisi, norm hesapları)
DB'den çekmek worker/analytics.py'nin sorumluluğu. Yeterli geçmiş veri
yoksa (β/γ regresyonu, hava/tüketim normu, CAGR) fonksiyonlar sahte bir
değer ÜRETMEZ, None ('hesaplanamaz') döner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# dokumanlar/05_kaynak_dosya_sozlesmesi.md — Tüketici Grubu Eşleme
GECERLI_GRUPLAR = {
    "Mesken",
    "Sanayi",
    "Tarımsal",
    "Aydınlatma",
    "Kamu ve Özel Hizmetler",
}

# fact_serbest_tuketici.tur — gerçek T13 değerleri (2026-08-30 doğrulandı,
# bkz. migration 20260819_0006 ve dokumanlar/03_veri_modeli.md)
GECERLI_TURLER = {
    "Serbest Tuketici",
    "ST Olma Hakki Bulunmayan Aboneler",
    "ST Olma Hakkini Kullanmayan Aboneler",
}

# OD-1: HDD/CDD baz sıcaklıkları koda GÖMÜLMEZ — kpi_23_hdd/kpi_24_cdd
# parametre olarak alır, çağıran (worker/analytics.py) sistem_parametre'den
# okur (bkz. migration 20260819_0004: hdd_baz_c=18, cdd_baz_c=22).


@dataclass
class DogrulamaSonucu:
    """Veri kalite kurallarından (dokumanlar/02_srs_ozet.md) geçen satır kümeleri."""

    kabul: pd.DataFrame
    red: pd.DataFrame
    karantina: pd.DataFrame


def dogrula_tuketim(df: pd.DataFrame) -> DogrulamaSonucu:
    red_mask = df["tuketim_mwh"] < 0
    karantina_mask = ~df["grup"].isin(GECERLI_GRUPLAR) & ~red_mask
    kabul_mask = ~red_mask & ~karantina_mask
    return DogrulamaSonucu(
        kabul=df[kabul_mask].reset_index(drop=True),
        red=df[red_mask].reset_index(drop=True),
        karantina=df[karantina_mask].reset_index(drop=True),
    )


def dogrula_uretim(df: pd.DataFrame) -> DogrulamaSonucu:
    """uretim_mwh sütunu bazı kaynaklarda hiç yok (T1/T4'ün ham çıktısında il×kaynak
    grain'inde uretim_mwh mevcut değil, bkz. worker/parser.py modül notu) — sütun
    yoksa negatiflik kontrolünden muaf tutulur, kurulu_guc_mw yine de kontrol edilir."""
    uretim_negatif = df["uretim_mwh"] < 0 if "uretim_mwh" in df.columns else False
    red_mask = uretim_negatif | (df["kurulu_guc_mw"] < 0)
    kabul_mask = ~red_mask
    return DogrulamaSonucu(
        kabul=df[kabul_mask].reset_index(drop=True),
        red=df[red_mask].reset_index(drop=True),
        karantina=df.iloc[0:0],
    )


def dogrula_abone(df: pd.DataFrame) -> DogrulamaSonucu:
    red_mask = df["abone_sayisi"] < 0
    karantina_mask = ~df["grup"].isin(GECERLI_GRUPLAR) & ~red_mask
    kabul_mask = ~red_mask & ~karantina_mask
    return DogrulamaSonucu(
        kabul=df[kabul_mask].reset_index(drop=True),
        red=df[red_mask].reset_index(drop=True),
        karantina=df[karantina_mask].reset_index(drop=True),
    )


def dogrula_serbest_tuketici(df: pd.DataFrame) -> DogrulamaSonucu:
    """T13: negatif tuketim_mwh/tuketici_sayisi → red; bilinmeyen tur/grup → karantina."""
    red_mask = (df["tuketim_mwh"] < 0) | (df["tuketici_sayisi"] < 0)
    karantina_mask = (
        ~df["tur"].isin(GECERLI_TURLER) | ~df["grup"].isin(GECERLI_GRUPLAR)
    ) & ~red_mask
    kabul_mask = ~red_mask & ~karantina_mask
    return DogrulamaSonucu(
        kabul=df[kabul_mask].reset_index(drop=True),
        red=df[red_mask].reset_index(drop=True),
        karantina=df[karantina_mask].reset_index(drop=True),
    )


def yukle_tuketim(yol: str | Path) -> DogrulamaSonucu:
    return dogrula_tuketim(pd.read_csv(yol))


def yukle_uretim(yol: str | Path) -> DogrulamaSonucu:
    return dogrula_uretim(pd.read_csv(yol))


def yukle_abone(yol: str | Path) -> DogrulamaSonucu:
    return dogrula_abone(pd.read_csv(yol))


# ---------------------------------------------------------------------------
# Üretim & Kapasite (Ek B)
# ---------------------------------------------------------------------------


def kpi_01_kurulu_guc(uretim: pd.DataFrame) -> float:
    if uretim.empty:
        return 0.0
    return float(uretim["kurulu_guc_mw"].sum())


def kpi_02_toplam_uretim(uretim: pd.DataFrame) -> float:
    if uretim.empty:
        return 0.0
    return float(uretim["uretim_mwh"].sum())


def kpi_03_yenilenebilir_pay(uretim: pd.DataFrame) -> float | None:
    toplam = float(uretim["uretim_mwh"].sum()) if not uretim.empty else 0.0
    if toplam == 0:
        return None
    yen = float(uretim.loc[uretim["yenilenebilir"], "uretim_mwh"].sum())
    return round(yen / toplam * 100, 1)


def kpi_06_hhi(uretim: pd.DataFrame) -> float | None:
    toplam = float(uretim["uretim_mwh"].sum()) if not uretim.empty else 0.0
    if toplam == 0:
        return None
    paylar = uretim.groupby("kaynak")["uretim_mwh"].sum() / toplam
    return round(float((paylar**2).sum()), 3)


def kpi_04_kaynak_payi(uretim: pd.DataFrame) -> dict[str, float] | None:
    toplam = float(uretim["uretim_mwh"].sum()) if not uretim.empty else 0.0
    if toplam == 0:
        return None
    paylar = uretim.groupby("kaynak")["uretim_mwh"].sum() / toplam * 100
    return {str(kaynak): round(float(deger), 1) for kaynak, deger in paylar.items()}


def kpi_05_kapasite_faktoru(uretim: pd.DataFrame, saat: float) -> float | None:
    """uretim_mwh bu grain'de (il×kaynak) aylık EPDK raporunda hiç mevcut
    değil (bkz. migration 20260819_0005, worker/parser.py modül notu) —
    sütun tamamen boşsa (gerçek DB verisi) 'hesaplanamaz' (None) döner,
    aksi halde 0/(kurulu*saat) gibi yanıltıcı bir %0.0 gösterilirdi."""
    kurulu = float(uretim["kurulu_guc_mw"].sum()) if not uretim.empty else 0.0
    if kurulu == 0 or saat <= 0:
        return None
    if uretim.empty or uretim["uretim_mwh"].isna().all():
        return None
    uretim_toplam = float(uretim["uretim_mwh"].sum())
    return round(uretim_toplam / (kurulu * saat) * 100, 1)


def kpi_07_lisanssiz_pay(uretim: pd.DataFrame) -> float | None:
    toplam = float(uretim["uretim_mwh"].sum()) if not uretim.empty else 0.0
    if toplam == 0:
        return None
    if "lisans" not in uretim.columns:
        return 0.0
    lisanssiz = float(uretim.loc[uretim["lisans"] == "Lisanssız", "uretim_mwh"].sum())
    return round(lisanssiz / toplam * 100, 1)


# ---------------------------------------------------------------------------
# Tüketim (Ek B)
# ---------------------------------------------------------------------------


def kpi_08_toplam_tuketim(tuketim: pd.DataFrame) -> float:
    if tuketim.empty:
        return 0.0
    return float(tuketim["tuketim_mwh"].sum())


def kpi_09_grup_payi(tuketim: pd.DataFrame, grup: str) -> float | None:
    toplam = float(tuketim["tuketim_mwh"].sum()) if not tuketim.empty else 0.0
    if toplam == 0:
        return None
    grup_toplam = float(tuketim.loc[tuketim["grup"] == grup, "tuketim_mwh"].sum())
    return round(grup_toplam / toplam * 100, 1)


def kpi_10_abone_basi(
    tuketim: pd.DataFrame, abone: pd.DataFrame, grup: str
) -> float | None:
    abone_sayisi = float(abone.loc[abone["grup"] == grup, "abone_sayisi"].sum())
    if abone_sayisi == 0:
        return None
    grup_tuketim = float(tuketim.loc[tuketim["grup"] == grup, "tuketim_mwh"].sum())
    return grup_tuketim / abone_sayisi


def kpi_13_yoy(simdi: pd.DataFrame, gecen_yil: pd.DataFrame | None) -> float | None:
    """Tüketim YoY (yıl-yıl değişim, %). `simdi`/`gecen_yil`:
    `analytics.tuketim_getir()` şekli (en az `grup`, `tuketim_mwh` kolonları).

    **Kapsam uyuşmazlığında `None` döner (2026-09-03, KPI-25/26 ile AYNI
    disiplin uygulandı):** iki dönemin GRUP KÜMESİ (örn. Sanayi'nin biri
    içerip diğerinin içermemesi) birebir aynı DEĞİLSE karşılaştırma
    anlamsızdır — "4 grup" ile "5 grup"u karşılaştırmak sahte bir sayı
    üretir (kanıt: 2025-06 Sanayi'siz/2026-06 Sanayi'li karşılaştırması
    %+70,9 veriyordu, Sanayi her iki taraftan da çıkarılınca %+2,2 — asıl
    büyüme bu). `worker/analytics.py:yillik_tuketim_serisi_getir()`/
    `yillik_yenilenebilir_kurulu_guc_serisi_getir()`'in "kapsamı
    uyuşmayan yılı seriye hiç katma" ilkesiyle AYNI kök nedene AYNI
    çözüm — bu modülün genel "sahte değer üretmeme" kuralı (bkz. modül
    notu)."""
    if gecen_yil is None or gecen_yil.empty or simdi.empty:
        return None  # 'hesaplanamaz' (geçen yıl verisi yok)

    simdi_gruplari = set(simdi["grup"].unique())
    gecen_yil_gruplari = set(gecen_yil["grup"].unique())
    if simdi_gruplari != gecen_yil_gruplari:
        return None  # 'hesaplanamaz' (grup kümesi uyuşmuyor — bkz. yukarıdaki not)

    simdi_toplam = float(simdi["tuketim_mwh"].sum())
    gecen_yil_toplam = float(gecen_yil["tuketim_mwh"].sum())
    if not gecen_yil_toplam:
        return None
    return round((simdi_toplam - gecen_yil_toplam) / gecen_yil_toplam * 100, 1)


# ---------------------------------------------------------------------------
# Hava Türetimleri (KPI-23/24, Faz 0'dan production) + KPI-11/12 (Faz 3)
# ---------------------------------------------------------------------------


def kpi_23_hdd(hava: pd.DataFrame, hdd_baz_c: float) -> float:
    return float((hdd_baz_c - hava["t_ort"]).clip(lower=0).sum())


def kpi_24_cdd(hava: pd.DataFrame, cdd_baz_c: float) -> float:
    return float((hava["t_ort"] - cdd_baz_c).clip(lower=0).sum())


_MIN_REGRESYON_GOZLEM = 12


def beta_gamma_tahmin_et(
    gecmis: pd.DataFrame, min_gozlem: int = _MIN_REGRESYON_GOZLEM
) -> tuple[float, float, float] | None:
    """KPI-11'in β/γ katsayılarını geçmiş (tuketim_mwh, hdd, cdd) gözlemleri
    üzerinde basit OLS ile tahmin eder: tuketim_mwh ~ β·hdd + γ·cdd + sabit.
    gecmis: aynı il, farklı dönemler (satır=dönem). Yeterli gözlem yoksa
    (< min_gozlem, varsayılan 12 ay) None ('hesaplanamaz') döner — sahte
    katsayı ÜRETİLMEZ. Döner: (beta, gamma, sabit)."""
    if gecmis.empty:
        return None
    gecerli = gecmis.dropna(subset=["tuketim_mwh", "hdd", "cdd"])
    if len(gecerli) < min_gozlem:
        return None
    X = np.column_stack(
        [gecerli["hdd"].to_numpy(), gecerli["cdd"].to_numpy(), np.ones(len(gecerli))]
    )
    y = gecerli["tuketim_mwh"].to_numpy()
    katsayilar, *_ = np.linalg.lstsq(X, y, rcond=None)
    beta, gamma, sabit = katsayilar
    return float(beta), float(gamma), float(sabit)


def hava_normu_hesapla(
    hdd_cdd_serisi: pd.DataFrame, yil_sayisi: int = 10
) -> tuple[float, float] | None:
    """OD-2: hava normu, aynı ay için son yil_sayisi (varsayılan 10, SABİT
    pencere) yılın HDD/CDD ortalaması. hdd_cdd_serisi kolonları: hdd, cdd
    (satır=yıl, aynı takvim ayı). Yeterli yıl yoksa None."""
    gecerli = hdd_cdd_serisi.dropna(subset=["hdd", "cdd"])
    if len(gecerli) < yil_sayisi:
        return None
    return float(gecerli["hdd"].mean()), float(gecerli["cdd"].mean())


def tuketim_normu_hesapla(
    arindirilmis_serisi: pd.Series, yil_sayisi: int = 5
) -> float | None:
    """OD-2: tüketim normu, aynı ay için son yil_sayisi (varsayılan 5,
    ROLLING pencere) yılın ARINDIRILMIŞ (kpi_11_arindirilmis_tuketim'den
    geçmiş) tüketim ortalaması. Yeterli yıl yoksa None."""
    gecerli = arindirilmis_serisi.dropna()
    if len(gecerli) < yil_sayisi:
        return None
    return float(gecerli.mean())


def kpi_11_arindirilmis_tuketim(
    tuketim_mwh: float,
    hdd: float,
    cdd: float,
    hdd_norm: float,
    cdd_norm: float,
    beta: float,
    gamma: float,
) -> float:
    """KPI-11: arındırılmış = gerçek − β·(HDD−HDD_norm) − γ·(CDD−CDD_norm)."""
    return tuketim_mwh - beta * (hdd - hdd_norm) - gamma * (cdd - cdd_norm)


def kpi_12_norm_sapmasi(
    arindirilmis: float, tuketim_norm: float | None
) -> float | None:
    """KPI-12: (arındırılmış − tüketim_norm)/tüketim_norm × 100. tüketim_norm
    yoksa/0 ise 'hesaplanamaz' (None)."""
    if not tuketim_norm:
        return None
    return round((arindirilmis - tuketim_norm) / tuketim_norm * 100, 1)


def kpi_cagr(ilk: float | None, son: float | None, n: int) -> float | None:
    """KPI-25/26 jenerik CAGR: (son/ilk)^(1/n) − 1 × 100 ; n = gözlem − 1
    (dokumanlar/04_kpi_sozlesmeleri.md, SRS_Teknik-Gereksinim_v1.5 Tablo 26).
    KPI-25 = tüketim CAGR (ilk/son: toplam tüketim_mwh, yıl bazında).
    KPI-26 = yenilenebilir kurulu güç CAGR (ilk/son: Σ kurulu_guc_mw WHERE
    dim_kaynak.yenilenebilir_mi=true, yıl bazında) — hangi seriyi geçeceği
    çağırana (worker/analytics.py + app/dashboard.py) aittir, formül aynı.
    ilk<=0 veya n<=0 ise 'hesaplanamaz' (None) — sıfıra/negatife bölme yok."""
    if ilk is None or son is None or ilk <= 0 or n <= 0:
        return None
    return round(((son / ilk) ** (1 / n) - 1) * 100, 1)


def esik_rengi(
    deger: float | None, yesil_alt: float, sari_alt: float, yon: str
) -> str | None:
    """`kpi_esik` tablosundaki bir eşik satırına göre trafik ışığı rengi
    döndürür — 'yesil'/'sari'/'kirmizi', deger None ise None ('hesaplanamaz'
    olan bir KPI'ye renk verilmez, sahte bir 'kırmızı' üretilmez).

    Sözleşme (2026-09-05, kpi_esik'in ilk gerçek tüketicisi — bu kod
    yazılırken serbestçe tanımlandı, tabloyu daha önce hiçbir şey
    tüketmiyordu): yalnız İKİ gerçek kırılım noktası var, `kirmizi_alt`
    KASITLI OLARAK kullanılmıyor/NULL bırakılıyor (üçüncü bir sayı icat
    etmek yerine "sarı bandın dışı = kırmızı" kuralı yeterli):
    - `yon='yukselik'` (yüksek değer iyi, örn. CAGR): deger>=yesil_alt
      → yeşil; deger>=sari_alt → sarı; aksi → kırmızı.
    - `yon='alcelik'` (düşük değer iyi, örn. HHI, |norm sapması|):
      deger<=yesil_alt → yeşil; deger<=sari_alt → sarı; aksi → kırmızı.
    Simetrik sapma metrikleri (örn. KPI-12) için çağıran `abs(deger)`
    geçirmeli — bu fonksiyon işareti kendisi yorumlamaz."""
    if deger is None:
        return None
    if yon == "yukselik":
        if deger >= yesil_alt:
            return "yesil"
        if deger >= sari_alt:
            return "sari"
        return "kirmizi"
    if yon == "alcelik":
        if deger <= yesil_alt:
            return "yesil"
        if deger <= sari_alt:
            return "sari"
        return "kirmizi"
    raise ValueError(
        f"Bilinmeyen yön: {yon!r} — yalnız 'yukselik'/'alcelik' kabul edilir."
    )


# ---------------------------------------------------------------------------
# P0-2 — Sanayi iletim/dağıtım ayrımı (fact_tuketim.baglanti)
# ---------------------------------------------------------------------------


def p0_2_sanayi(tuketim: pd.DataFrame) -> dict[str, float | int]:
    sanayi = tuketim[tuketim["grup"] == "Sanayi"]
    iletim = float(sanayi.loc[sanayi["baglanti"] == "iletim", "tuketim_mwh"].sum())
    dagitim = float(sanayi.loc[sanayi["baglanti"] == "dagitim", "tuketim_mwh"].sum())
    return {
        "sanayi_toplam": iletim + dagitim,
        "sanayi_iletim": iletim,
        "sanayi_dagitim": dagitim,
        "beklenen_satir": len(tuketim),
    }
