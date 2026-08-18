"""
EPP — Türkiye Elektrik Piyasası Paneli (Streamlit)
Çalıştırma:  streamlit run app/dashboard.py
Veri: data/tr_ocak2026.py (gerçek EPDK Ocak 2026, 81 il)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# data/ klasörünü yola ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from tr_ocak2026 import TABLO11, TABLO3_URETIM, TABLO2_KAYNAK, YENILENEBILIR  # noqa: E402

st.set_page_config(page_title="EPP — Türkiye Elektrik Piyasası", layout="wide", page_icon="⚡")


@st.cache_data
def veri_hazirla():
    # Tüketim: uzun format (il, grup, baglanti, mwh)
    rows = []
    for il, ayd, kamu, mesken, san_dag, san_ilt, tarim in TABLO11:
        rows += [
            (il, "Aydınlatma", "dagitim", ayd),
            (il, "Kamu ve Özel Hizmetler", "dagitim", kamu),
            (il, "Mesken", "dagitim", mesken),
            (il, "Sanayi", "dagitim", san_dag),
            (il, "Sanayi", "iletim", san_ilt),   # P0-2: ayrı satır
            (il, "Tarımsal", "dagitim", tarim),
        ]
    tuk = pd.DataFrame(rows, columns=["il", "grup", "baglanti", "mwh"])
    uret_il = pd.DataFrame(TABLO3_URETIM.items(), columns=["il", "uretim_mwh"])
    kaynak = pd.DataFrame(TABLO2_KAYNAK, columns=["kaynak", "uretim_mwh", "yenilenebilir"])
    return tuk, uret_il, kaynak


tuk, uret_il, kaynak = veri_hazirla()

# ---------------- BAŞLIK ----------------
st.title("⚡ Türkiye Elektrik Piyasası Paneli")
st.caption("Gerçek EPDK Elektrik Piyasası Sektör Raporu — Ocak 2026 · 81 İl")

# ---------------- FİLTRE (kenar çubuğu) ----------------
with st.sidebar:
    st.header("Filtreler")
    iller = ["Türkiye Geneli"] + sorted(tuk["il"].unique().tolist())
    secili_il = st.selectbox("İl", iller)
    gruplar = ["Tümü"] + sorted(tuk["grup"].unique().tolist())
    secili_grup = st.selectbox("Tüketici Grubu", gruplar)
    st.divider()
    st.caption("Kaynak: EPDK Ocak 2026 Sektör Raporu")

# Filtre uygula
f = tuk.copy()
if secili_il != "Türkiye Geneli":
    f = f[f["il"] == secili_il]
if secili_grup != "Tümü":
    f = f[f["grup"] == secili_grup]

# ---------------- KPI KARTLARI ----------------
top_tuk = f["mwh"].sum()
top_uret = kaynak["uretim_mwh"].sum()
yen_pay = kaynak.loc[kaynak["yenilenebilir"], "uretim_mwh"].sum() / top_uret * 100
san_iletim = tuk[(tuk["grup"] == "Sanayi") & (tuk["baglanti"] == "iletim")]["mwh"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Seçili Tüketim", f"{top_tuk/1e6:,.2f} TWh" if top_tuk > 1e6 else f"{top_tuk/1000:,.0f} GWh")
k2.metric("Türkiye Üretim", f"{top_uret/1e6:,.1f} TWh")
k3.metric("Yenilenebilir Payı", f"%{yen_pay:.1f}")
k4.metric("Öz-Yeterlilik", f"%{top_uret/tuk['mwh'].sum()*100:.0f}")

st.divider()

# ---------------- GRAFİKLER ----------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("En Yüksek Tüketimli 15 İl (GWh)")
    il_top = (tuk.groupby("il")["mwh"].sum() / 1000).sort_values(ascending=False).head(15)
    st.bar_chart(il_top, horizontal=True, color="#B07D2B")

with c2:
    st.subheader("Üretim Kaynak Karışımı (TWh)")
    kk = kaynak.set_index("kaynak")["uretim_mwh"].sort_values(ascending=False) / 1e6
    st.bar_chart(kk, horizontal=True, color="#548235")

c3, c4 = st.columns(2)

with c3:
    st.subheader("Tüketici Grubu Payı")
    grup_top = tuk.groupby("grup")["mwh"].sum().sort_values(ascending=False)
    st.bar_chart(grup_top / 1e6, color="#2E5496")

with c4:
    st.subheader("P0-2 · Sanayi İletim/Dağıtım Ayrımı (TWh)")
    san = tuk[tuk["grup"] == "Sanayi"].groupby("baglanti")["mwh"].sum() / 1e6
    st.bar_chart(san, color="#7030A0")
    st.info(f"İletim: {san.get('iletim', 0):.2f} TWh · Dağıtım: {san.get('dagitim', 0):.2f} TWh "
            f"→ Toplam {san.sum():.2f} TWh (Tablo 11 ile birebir)")

# ---------------- VERİ TABLOSU ----------------
with st.expander("📋 Ham veriyi göster"):
    st.dataframe(f.sort_values("mwh", ascending=False), use_container_width=True)

st.caption("EPP — EPDK Elektrik Piyasası Veri & Dashboard Platformu · Faz 1")
