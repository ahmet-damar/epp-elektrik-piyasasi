"""
EPP — Türkiye Elektrik Piyasası Paneli (Streamlit)
Çalıştırma:  streamlit run app/dashboard.py

Faz 2: gerçek DB bağlantısı varsa (DATABASE_URL) worker/analytics.py
üzerinden fact_*/dim_* sorgulanır (bkz. dokumanlar/03_veri_modeli.md);
yoksa data/tr_ocak2026.py'deki statik Ocak 2026 verisiyle çalışır (yerel
geliştirme kolaylığı, DB kurulumu gerektirmez). KPI hesapları TAMAMEN
worker/kpi.py'den gelir — bu dosyada elle tekrar hesaplama YOK (bkz.
dokumanlar/06_adr_dashboard_teknoloji.md, Streamlit seçim gerekçesi).

worker/db.resolve_database_or_fallback() ya bir psycopg Connection (DATABASE_URL
varsa) ya bir Supabase istemcisi (yalnız anon key varsa) ya da None döner.
worker/analytics.py'nin sorguları düz psycopg cursor'ı varsayar — Supabase
istemcisi Faz 2'de gerçek sorgu yolunu DESTEKLEMEZ (farklı bir API yüzeyi;
ayrıca anon-key erişimi RLS'e tabidir, tek-kullanıcılı Faz 2 kapsamının
dışında) — bu durumda da statik veriye düşülür.

worker/ paketi repo kökünde, bu dosya app/ altında — Streamlit/Python yalnız
çalıştırılan dosyanın klasörünü (app/) sys.path'e ekler, repo kökünü değil.
Bu yüzden en üstte repo kökü sys.path'e eklenir (worker/ VE data/ aynı kökün
altında olduğundan tek satır ikisini de karşılar). worker importu artık
KRİTİK bir bağımlılık (analytics.py olmadan dashboard çalışmaz) — bilinçli
olarak try/except ile yutulmuyor: sys.path doğruysa zaten başarılı olur,
başarısız olursa net bir ModuleNotFoundError sessiz bir None'dan iyidir.

Bağlantı yönetimi: @st.cache_resource ile bağlantı TEK SEFER açılır —
Streamlit her etkileşimde script'i baştan çalıştırır; cache_resource
olmasaydı her tıklamada yeni bir DB bağlantısı açılırdı. Sorgu sonuçları
@st.cache_data ile cache'lenir; bağlantı parametresi `_conn` adıyla
geçirilir çünkü Streamlit alttan çizgiyle (_) başlayan parametreleri
HASH'LEMEZ — psycopg Connection nesnesi hash'lenemeyeceğinden bu
isimlendirme zorunludur (adı `conn` olsaydı cache ya patlar ya sessizce
devre dışı kalırdı).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# Repo kökünü yola ekle (worker/ VE data/ ikisi de kökün altında) — bkz. modül notu.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.tr_ocak2026 import TABLO2_KAYNAK, TABLO11
from worker import analytics, ingest, kpi
from worker.db import resolve_database_or_fallback

st.set_page_config(
    page_title="EPP — Türkiye Elektrik Piyasası", layout="wide", page_icon="⚡"
)


@st.cache_resource(show_spinner=False)
def _baglanti_kur() -> tuple[Any | None, str]:
    return resolve_database_or_fallback()


db_handle, db_source = _baglanti_kur()
# Yalnız düz psycopg (DATABASE_URL) yolu gerçek sorguyu destekler - bkz. modül notu.
gercek_veri_var = db_handle is not None and db_source == "PostgreSQL via DATABASE_URL"

if gercek_veri_var:
    st.info(f"Veri kaynağı: {db_source}")
elif db_handle is not None:
    st.warning(
        f"Veri kaynağı '{db_source}' Faz 2'de henüz desteklenmiyor (yalnız "
        "DATABASE_URL/PostgreSQL) — yerel dosya verisiyle devam ediliyor."
    )
else:
    st.warning(
        "Supabase/PostgreSQL erişimi bulunamadı. Yerel dosya verisiyle çalışmaya devam ediliyor."
    )


# ---------------- Önbellekli sorgu sarmalayıcıları (DB modu) ----------------
# _conn: bkz. modül notu - Streamlit alttan çizgili parametreleri hash'lemez.


@st.cache_data(show_spinner="Dönemler yükleniyor...")
def _donemler_getir_cached(_conn: Any) -> pd.DataFrame:
    return analytics.donemler_getir(_conn)


@st.cache_data(show_spinner="İller yükleniyor...")
def _iller_getir_cached(_conn: Any) -> pd.DataFrame:
    return analytics.iller_getir(_conn)


@st.cache_data(show_spinner="Üretim verisi yükleniyor...")
def _uretim_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.uretim_getir(_conn, tarih_id)


@st.cache_data(show_spinner="Tüketim verisi yükleniyor...")
def _tuketim_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.tuketim_getir(_conn, tarih_id)


@st.cache_data(show_spinner="Abone verisi yükleniyor...")
def _abone_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.abone_getir(_conn, tarih_id)


@st.cache_data(show_spinner="Serbest tüketici verisi yükleniyor...")
def _serbest_tuketici_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.serbest_tuketici_getir(_conn, tarih_id)


@st.cache_data(show_spinner="Hava verisi yükleniyor...")
def _hava_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.hava_getir(_conn, tarih_id)


@st.cache_data
def _statik_veri_hazirla() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame
]:
    """DB yokken data/tr_ocak2026.py'yi analytics.py ile AYNI kolon şekline getirir
    — böylece aşağıdaki KPI/render kodu tek bir yoldan geçer, DB/statik ayrımı
    yalnız burada kalır."""
    rows = []
    for il, ayd, kamu, mesken, san_dag, san_ilt, tarim in TABLO11:
        rows += [
            (il, "Aydınlatma", "dagitim", ayd),
            (il, "Kamu ve Özel Hizmetler", "dagitim", kamu),
            (il, "Mesken", "dagitim", mesken),
            (il, "Sanayi", "dagitim", san_dag),
            (il, "Sanayi", "iletim", san_ilt),  # P0-2: ayrı satır
            (il, "Tarımsal", "dagitim", tarim),
        ]
    tuketim = pd.DataFrame(rows, columns=["il", "grup", "baglanti", "tuketim_mwh"])
    tuketim["il_kodu"] = None  # statik veri il_kodu taşımıyor, yalnız il adı

    uretim = pd.DataFrame(
        TABLO2_KAYNAK, columns=["kaynak", "uretim_mwh", "yenilenebilir"]
    )
    # kurulu_guc_mw/lisans statik veride yok (Tablo 2 ülke geneli, kaynak
    # bazında üretim) — KPI-01/05/07 kartları bu yüzden 'veri yok' gösterir.
    uretim["kurulu_guc_mw"] = pd.NA
    uretim["lisans"] = pd.NA
    uretim["il"] = pd.NA
    uretim["il_kodu"] = pd.NA

    bos_abone = pd.DataFrame(columns=["il", "il_kodu", "grup", "abone_sayisi"])
    bos_serbest = pd.DataFrame(
        columns=["il", "il_kodu", "tur", "grup", "tuketim_mwh", "tuketici_sayisi"]
    )
    bos_hava = pd.DataFrame(
        columns=["il", "il_kodu", "t_ort", "hdd", "cdd", "radyasyon", "ruzgar"]
    )
    return tuketim, uretim, bos_abone, bos_serbest, bos_hava


# ---------------- Dönem seçimi + veri çekme ----------------

if gercek_veri_var:
    donemler = _donemler_getir_cached(db_handle)
    if donemler.empty:
        st.error(
            "Veritabanında aktif bir dönem bulunamadı (henüz hiçbir batch "
            "aktive edilmemiş olabilir — bkz. worker/pipeline.py batch_onayla())."
        )
        st.stop()

    with st.sidebar:
        st.header("Dönem")
        secili_yil_ay = st.selectbox("Ay/Yıl", donemler["yil_ay"].tolist())
    secili_tarih_id = int(
        donemler.loc[donemler["yil_ay"] == secili_yil_ay, "tarih_id"].iloc[0]
    )

    uretim = _uretim_getir_cached(db_handle, secili_tarih_id)
    tuketim = _tuketim_getir_cached(db_handle, secili_tarih_id)
    abone = _abone_getir_cached(db_handle, secili_tarih_id)
    serbest = _serbest_tuketici_getir_cached(db_handle, secili_tarih_id)
    hava = _hava_getir_cached(db_handle, secili_tarih_id)

    # KPI-13 (YoY): bir önceki yılın aynı ayı aktifse kullan, yoksa 'veri yok'.
    onceki_tarih_id = secili_tarih_id - 100
    if onceki_tarih_id in donemler["tarih_id"].tolist():
        onceki_tuketim = _tuketim_getir_cached(db_handle, onceki_tarih_id)
    else:
        onceki_tuketim = pd.DataFrame(columns=tuketim.columns)

    il_listesi = _iller_getir_cached(db_handle)
    iller = ["Türkiye Geneli"] + il_listesi["il_adi"].tolist()
    donem_etiketi = secili_yil_ay
    donem_saat = ingest.donem_saat_sayisi(secili_tarih_id)
else:
    tuketim, uretim, abone, serbest, hava = _statik_veri_hazirla()
    onceki_tuketim = pd.DataFrame(columns=tuketim.columns)
    iller = ["Türkiye Geneli"] + sorted(tuketim["il"].dropna().unique().tolist())
    donem_etiketi = "2026-01 (yerel dosya)"
    donem_saat = ingest.donem_saat_sayisi(202601)
    with st.sidebar:
        st.header("Dönem")
        st.selectbox("Ay/Yıl", [donem_etiketi], disabled=True)

# ---------------- BAŞLIK ----------------
st.title("⚡ Türkiye Elektrik Piyasası Paneli")
st.caption(f"EPDK Elektrik Piyasası Sektör Raporu — {donem_etiketi} · 81 İl")

# ---------------- FİLTRE (kenar çubuğu) ----------------
with st.sidebar:
    st.header("Filtreler")
    secili_il = st.selectbox("İl", iller)
    gruplar = ["Tümü"] + sorted(tuketim["grup"].dropna().unique().tolist())
    secili_grup = st.selectbox("Tüketici Grubu", gruplar)
    st.divider()
    st.caption("Kaynak: EPDK Elektrik Piyasası Sektör Raporu")

# Filtre yalnız tüketim/abone tabanlı kartlara+grafiklere uygulanır; üretim
# (KPI-01..07) ulusal kalır — orijinal tasarımın "seçili tüketim / ulusal
# üretim" ayrımıyla tutarlı.
f = tuketim.copy()
if secili_il != "Türkiye Geneli":
    f = f[f["il"] == secili_il]
if secili_grup != "Tümü":
    f = f[f["grup"] == secili_grup]

# yalnız il'e göre filtrelenmiş (grup filtresi UYGULANMAMIŞ) - KPI-09 "payı"
# kartları için: paydanın (seçili ildeki TÜM gruplar) grup filtresiyle
# daralması "payı"yı anlamsızlaştırır (tek grup kalınca %100'e yakınsar).
il_filtreli = tuketim.copy()
if secili_il != "Türkiye Geneli":
    il_filtreli = il_filtreli[il_filtreli["il"] == secili_il]

abone_f = abone.copy()
if secili_il != "Türkiye Geneli" and not abone_f.empty:
    abone_f = abone_f[abone_f["il"] == secili_il]

# ---------------- KPI KARTLARI — ÜRETİM ----------------
st.subheader("Üretim")

kurulu_var = bool(uretim["kurulu_guc_mw"].notna().any())
lisans_var = bool(uretim["lisans"].notna().any())

u1, u2, u3, u4 = st.columns(4)
u1.metric(
    "Kurulu Güç (KPI-01)",
    f"{kpi.kpi_01_kurulu_guc(uretim):,.0f} MW" if kurulu_var else "veri yok",
)

toplam_uretim = kpi.kpi_02_toplam_uretim(uretim)
u2.metric(
    "Toplam Üretim (KPI-02)",
    f"{toplam_uretim / 1e6:,.2f} TWh" if toplam_uretim else "veri yok",
)

yen_pay = kpi.kpi_03_yenilenebilir_pay(uretim)
u3.metric(
    "Yenilenebilir Payı (KPI-03)",
    f"%{yen_pay:.1f}" if yen_pay is not None else "veri yok",
)

kf = kpi.kpi_05_kapasite_faktoru(uretim, donem_saat) if kurulu_var else None
u4.metric("Kapasite Faktörü (KPI-05)", f"%{kf:.1f}" if kf is not None else "veri yok")

u5, u6, u7 = st.columns(3)
hhi = kpi.kpi_06_hhi(uretim)
u5.metric(
    "Kaynak Yoğunlaşması (KPI-06 HHI)", f"{hhi:.3f}" if hhi is not None else "veri yok"
)

lisanssiz_pay = kpi.kpi_07_lisanssiz_pay(uretim) if lisans_var else None
u6.metric(
    "Lisanssız Üretim Payı (KPI-07)",
    f"%{lisanssiz_pay:.1f}" if lisanssiz_pay is not None else "veri yok",
)

simdi_toplam_tuketim = kpi.kpi_08_toplam_tuketim(tuketim)
gecen_yil_toplam = (
    kpi.kpi_08_toplam_tuketim(onceki_tuketim) if not onceki_tuketim.empty else None
)
yoy = kpi.kpi_13_yoy(simdi_toplam_tuketim, gecen_yil_toplam)
u7.metric("Tüketim YoY (KPI-13)", f"%{yoy:+.1f}" if yoy is not None else "veri yok")

st.divider()

# ---------------- KPI KARTLARI — TÜKETİM ----------------
st.subheader("Tüketim")
t1, t2, t3, t4 = st.columns(4)

top_tuk = kpi.kpi_08_toplam_tuketim(f)
t1.metric(
    "Seçili Tüketim (KPI-08)",
    f"{top_tuk / 1e6:,.2f} TWh" if top_tuk > 1e6 else f"{top_tuk / 1000:,.0f} GWh",
)

# il_filtreli: seçili ile göre daralır, Tüketici Grubu filtresinden ETKİLENMEZ
# (payının anlamlı kalması için paydada TÜM gruplar kalmalı - bkz. yukarıdaki not).
mesken_pay = kpi.kpi_09_grup_payi(il_filtreli, "Mesken")
t2.metric(
    "Mesken Payı (KPI-09)",
    f"%{mesken_pay:.1f}" if mesken_pay is not None else "veri yok",
)

sanayi_pay = kpi.kpi_09_grup_payi(il_filtreli, "Sanayi")
t3.metric(
    "Sanayi Payı (KPI-09)",
    f"%{sanayi_pay:.1f}" if sanayi_pay is not None else "veri yok",
)
if secili_grup != "Tümü":
    st.caption(
        "Mesken/Sanayi Payı kartları İl filtresine göre güncellenir, "
        "Tüketici Grubu filtresinden bağımsızdır (payının anlamlı kalması "
        "için payda her zaman seçili ildeki TÜM grupları içerir)."
    )

abone_basi_mesken = (
    kpi.kpi_10_abone_basi(tuketim, abone, "Mesken") if not abone.empty else None
)
t4.metric(
    "Mesken Abone Başı (KPI-10)",
    f"{abone_basi_mesken:,.2f} MWh" if abone_basi_mesken is not None else "veri yok",
)

st.divider()

# ---------------- KPI KARTLARI — HAVA (Faz 3 altyapısı) ----------------
st.subheader("Hava (Faz 3 — henüz veri yok)")
h1, h2 = st.columns(2)
if not hava.empty:
    h1.metric("Isıtma Derece Gün (KPI-23 HDD)", f"{kpi.kpi_23_hdd(hava):,.0f}")
    h2.metric("Soğutma Derece Gün (KPI-24 CDD)", f"{kpi.kpi_24_cdd(hava):,.0f}")
else:
    h1.metric("Isıtma Derece Gün (KPI-23 HDD)", "veri yok")
    h2.metric("Soğutma Derece Gün (KPI-24 CDD)", "veri yok")

st.divider()

# ---------------- GRAFİKLER ----------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("En Yüksek Tüketimli 15 İl (GWh)")
    if f["il"].notna().any():
        il_top = (
            (f.groupby("il")["tuketim_mwh"].sum() / 1000)
            .sort_values(ascending=False)
            .head(15)
        )
        st.bar_chart(il_top, horizontal=True, color="#B07D2B")
    else:
        st.caption("İl bazlı kırılım bu veri kaynağında yok.")

with c2:
    st.subheader("Üretim Kaynak Karışımı — KPI-04 (%)")
    kaynak_payi = kpi.kpi_04_kaynak_payi(uretim)
    if kaynak_payi:
        kk = pd.Series(kaynak_payi).sort_values(ascending=False)
        st.bar_chart(kk, horizontal=True, color="#548235")
    else:
        st.caption("Üretim verisi yok.")

c3, c4 = st.columns(2)

with c3:
    st.subheader("Tüketici Grubu Payı (KPI-09, %)")
    # il_filtreli: bkz. yukarıdaki not - grup filtresi burada da UYGULANMAZ,
    # aksi halde tek bir grup kalıp grafik anlamsızca tek çubuğa iner.
    gruplar_sirali = sorted(il_filtreli["grup"].dropna().unique().tolist())
    grup_paylari = {g: kpi.kpi_09_grup_payi(il_filtreli, g) for g in gruplar_sirali}
    grup_paylari = {g: p for g, p in grup_paylari.items() if p is not None}
    if grup_paylari:
        st.bar_chart(
            pd.Series(grup_paylari).sort_values(ascending=False), color="#2E5496"
        )
    else:
        st.caption("Tüketim verisi yok.")

with c4:
    st.subheader("P0-2 · Sanayi İletim/Dağıtım Ayrımı (TWh)")
    p0_2 = kpi.p0_2_sanayi(tuketim)
    san = pd.Series(
        {"iletim": p0_2["sanayi_iletim"] / 1e6, "dagitim": p0_2["sanayi_dagitim"] / 1e6}
    )
    st.bar_chart(san, color="#7030A0")
    st.info(
        f"İletim: {san.get('iletim', 0):.2f} TWh · Dağıtım: {san.get('dagitim', 0):.2f} TWh "
        f"→ Toplam {san.sum():.2f} TWh (Tablo 11 ile birebir)"
    )
    if secili_il != "Türkiye Geneli":
        st.caption(
            "Bu grafik İl filtresinden bağımsızdır, her zaman Türkiye geneli "
            "gösterir — kaynak dosyanın 'TÜRKİYE' satırıyla yapılan sabit bir "
            "veri kalite/mutabakat kontrolüdür (bkz. dokumanlar/02_srs_ozet.md, "
            "'İl toplamı ↔ TÜRKİYE satırı ±%0,5 mutabık')."
        )

# ---------------- SERBEST TÜKETİCİ (Faz 0/1'de kurulan tablo) ----------------
if not serbest.empty:
    st.divider()
    st.subheader("Serbest Tüketici (Tablo 13)")
    st.caption(
        f"Toplam tüketim: {serbest['tuketim_mwh'].sum() / 1000:,.0f} GWh · "
        f"Toplam tüketici sayısı: {serbest['tuketici_sayisi'].sum():,.0f}"
    )
    with st.expander("📋 Serbest tüketici ham veriyi göster"):
        st.dataframe(serbest, width="stretch")

# ---------------- VERİ TABLOSU ----------------
with st.expander("📋 Ham veriyi göster"):
    st.dataframe(f.sort_values("tuketim_mwh", ascending=False), width="stretch")

st.caption("EPP — EPDK Elektrik Piyasası Veri & Dashboard Platformu · Faz 2")
