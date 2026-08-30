"""EPP — KPI hesaplama motoru (Faz 0).

Kaynak: dokumanlar/04_kpi_sozlesmeleri.md (Ek B), dokumanlar/05_kaynak_dosya_sozlesmesi.md (Ek F).
Girdi: is_active kabul edilmiş (dogrulanmis) DataFrame'ler. Veri kalite
kurallari (red/karantina) bu modulun dogrula_* fonksiyonlarinda uygulanir.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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

# sistem_parametre varsayılanları (OD-1) — Faz 0'da sabit, ileride DB'den okunur
HDD_BAZ_C = 18
CDD_BAZ_C = 22


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
    kurulu = float(uretim["kurulu_guc_mw"].sum()) if not uretim.empty else 0.0
    if kurulu == 0 or saat <= 0:
        return None
    uretim_toplam = float(uretim["uretim_mwh"].sum()) if not uretim.empty else 0.0
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


def kpi_13_yoy(simdi: float, gecen_yil: float | None) -> float | None:
    if not gecen_yil:
        return None  # 'hesaplanamaz' (geçen yıl verisi yok)
    return round((simdi - gecen_yil) / gecen_yil * 100, 1)


# ---------------------------------------------------------------------------
# Hava Türetimleri (Faz 0 altyapı — β/γ Faz 3'te)
# ---------------------------------------------------------------------------


def kpi_23_hdd(hava: pd.DataFrame) -> float:
    return float((HDD_BAZ_C - hava["t_ort"]).clip(lower=0).sum())


def kpi_24_cdd(hava: pd.DataFrame) -> float:
    return float((hava["t_ort"] - CDD_BAZ_C).clip(lower=0).sum())


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
