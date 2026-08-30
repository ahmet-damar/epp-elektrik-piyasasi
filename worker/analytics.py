"""EPP — Faz 2 dashboard için salt-okunur analitik sorgular.

worker/kpi.py'nin ZATEN beklediği DataFrame şekillerini üretir (kpi.py'ye
hiç dokunulmadı) — fact_* tablolarını ilgili dim_*'larla join'leyip
is_active=true filtresiyle çeker (bkz. dokumanlar/03_veri_modeli.md).

Framework-agnostik: Streamlit'e BAĞIMLI DEĞİL, düz psycopg + pandas.
Cache'leme (bağlantı ömrü + sorgu sonuçları) app/dashboard.py'nin
sorumluluğu — bkz. o dosyanın modül notu.

dim_lisans.tur DB'de ASCII saklanır (CHECK IN ('Lisansli','Lisanssiz'),
bkz. worker/ingest.py _LISANS_KODU) ama worker/kpi.py.kpi_07_lisanssiz_pay()
Türkçe karakterli görünüm formuyla karşılaştırır ('Lisanssız') — kpi.py'ye
dokunmamak için DB->görünüm çevrimi burada (_LISANS_GORUNUM) yapılır.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from psycopg import Connection

_LISANS_GORUNUM = {"Lisansli": "Lisanslı", "Lisanssiz": "Lisanssız"}


def _numerik(df: pd.DataFrame, kolonlar: list[str]) -> None:
    """psycopg NUMERIC kolonları Decimal/None döner; kpi.py float bekliyor —
    burada float64'e çevrilir (None -> NaN, kpi.py'nin zaten ele aldığı gibi)."""
    for kolon in kolonlar:
        if kolon in df.columns:
            df[kolon] = pd.to_numeric(df[kolon], errors="coerce")


def uretim_getir(
    conn: Connection, tarih_id: int, il_kodu: int | None = None
) -> pd.DataFrame:
    """kpi_01/02/03/04/05/06/07'nin beklediği şekil: il, il_kodu, kaynak,
    yenilenebilir, lisans, kurulu_guc_mw, uretim_mwh."""
    kolonlar = [
        "il",
        "il_kodu",
        "kaynak",
        "yenilenebilir",
        "lisans",
        "kurulu_guc_mw",
        "uretim_mwh",
    ]
    sorgu = """
        SELECT di.il_adi, fu.il_kodu, dk.kaynak_adi, dk.yenilenebilir_mi, dl.tur,
               fu.kurulu_guc_mw, fu.uretim_mwh
        FROM fact_uretim fu
        JOIN dim_kaynak dk ON dk.kaynak_id = fu.kaynak_id
        JOIN dim_lisans dl ON dl.lisans_id = fu.lisans_id
        JOIN dim_il di ON di.il_kodu = fu.il_kodu
        WHERE fu.tarih_id = %s AND fu.is_active
    """
    parametreler: list[object] = [tarih_id]
    if il_kodu is not None:
        sorgu += " AND fu.il_kodu = %s"
        parametreler.append(il_kodu)
    with conn.cursor() as cur:
        cur.execute(sorgu, parametreler)
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=kolonlar)
    if not df.empty:
        df["lisans"] = df["lisans"].map(_LISANS_GORUNUM).fillna(df["lisans"])
        df["yenilenebilir"] = df["yenilenebilir"].astype(bool)
    _numerik(df, ["kurulu_guc_mw", "uretim_mwh"])
    return df


def tuketim_getir(
    conn: Connection, tarih_id: int, il_kodu: int | None = None
) -> pd.DataFrame:
    """kpi_08/09/p0_2_sanayi'nin beklediği şekil: il, il_kodu, grup, baglanti, tuketim_mwh."""
    kolonlar = ["il", "il_kodu", "grup", "baglanti", "tuketim_mwh"]
    sorgu = """
        SELECT di.il_adi, ft.il_kodu, dg.grup_adi, ft.baglanti, ft.tuketim_mwh
        FROM fact_tuketim ft
        JOIN dim_tuketici_grubu dg ON dg.grup_id = ft.grup_id
        JOIN dim_il di ON di.il_kodu = ft.il_kodu
        WHERE ft.tarih_id = %s AND ft.is_active
    """
    parametreler: list[object] = [tarih_id]
    if il_kodu is not None:
        sorgu += " AND ft.il_kodu = %s"
        parametreler.append(il_kodu)
    with conn.cursor() as cur:
        cur.execute(sorgu, parametreler)
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=kolonlar)
    _numerik(df, ["tuketim_mwh"])
    return df


def abone_getir(
    conn: Connection, tarih_id: int, il_kodu: int | None = None
) -> pd.DataFrame:
    """kpi_10_abone_basi'nin beklediği şekil: il, il_kodu, grup, abone_sayisi."""
    kolonlar = ["il", "il_kodu", "grup", "abone_sayisi"]
    sorgu = """
        SELECT di.il_adi, fa.il_kodu, dg.grup_adi, fa.abone_sayisi
        FROM fact_abone fa
        JOIN dim_tuketici_grubu dg ON dg.grup_id = fa.grup_id
        JOIN dim_il di ON di.il_kodu = fa.il_kodu
        WHERE fa.tarih_id = %s AND fa.is_active
    """
    parametreler: list[object] = [tarih_id]
    if il_kodu is not None:
        sorgu += " AND fa.il_kodu = %s"
        parametreler.append(il_kodu)
    with conn.cursor() as cur:
        cur.execute(sorgu, parametreler)
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=kolonlar)
    _numerik(df, ["abone_sayisi"])
    return df


def serbest_tuketici_getir(
    conn: Connection, tarih_id: int, il_kodu: int | None = None
) -> pd.DataFrame:
    """Doğrudan bir kpi.py fonksiyonu yok (Faz 0/1'de kurulan fact tablosu) —
    dashboard'da ham tablo/toplam gösterimi için: il, il_kodu, tur, grup,
    tuketim_mwh, tuketici_sayisi."""
    kolonlar = ["il", "il_kodu", "tur", "grup", "tuketim_mwh", "tuketici_sayisi"]
    sorgu = """
        SELECT di.il_adi, fs.il_kodu, fs.tur, dg.grup_adi, fs.tuketim_mwh, fs.tuketici_sayisi
        FROM fact_serbest_tuketici fs
        JOIN dim_tuketici_grubu dg ON dg.grup_id = fs.grup_id
        JOIN dim_il di ON di.il_kodu = fs.il_kodu
        WHERE fs.tarih_id = %s AND fs.is_active
    """
    parametreler: list[object] = [tarih_id]
    if il_kodu is not None:
        sorgu += " AND fs.il_kodu = %s"
        parametreler.append(il_kodu)
    with conn.cursor() as cur:
        cur.execute(sorgu, parametreler)
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=kolonlar)
    _numerik(df, ["tuketim_mwh", "tuketici_sayisi"])
    return df


def hava_getir(
    conn: Connection, tarih_id: int, il_kodu: int | None = None
) -> pd.DataFrame:
    """kpi_23_hdd/kpi_24_cdd'nin beklediği şekil: il, il_kodu, t_ort, hdd, cdd,
    radyasyon, ruzgar. fact_hava_aylik Faz 2'de henüz hiç doldurulmadı (Faz 3,
    Open-Meteo) — boş DataFrame dönebilir; çağıran 'veri yok' göstermeli."""
    kolonlar = ["il", "il_kodu", "t_ort", "hdd", "cdd", "radyasyon", "ruzgar"]
    sorgu = """
        SELECT di.il_adi, fh.il_kodu, fh.t_ort, fh.hdd, fh.cdd, fh.radyasyon, fh.ruzgar
        FROM fact_hava_aylik fh
        JOIN dim_il di ON di.il_kodu = fh.il_kodu
        WHERE fh.tarih_id = %s AND fh.is_active
    """
    parametreler: list[object] = [tarih_id]
    if il_kodu is not None:
        sorgu += " AND fh.il_kodu = %s"
        parametreler.append(il_kodu)
    with conn.cursor() as cur:
        cur.execute(sorgu, parametreler)
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=kolonlar)
    _numerik(df, ["t_ort", "hdd", "cdd", "radyasyon", "ruzgar"])
    return df


def donemler_getir(conn: Connection) -> pd.DataFrame:
    """Sidebar dönem seçici için: yalnız en az bir aktif fact_tuketim satırı
    olan dönemler (tarih_id, yil_ay), en yeniden en eskiye."""
    sorgu = """
        SELECT DISTINCT dt.tarih_id, dt.yil_ay
        FROM dim_tarih dt
        WHERE EXISTS (
            SELECT 1 FROM fact_tuketim ft
            WHERE ft.tarih_id = dt.tarih_id AND ft.is_active
        )
        ORDER BY dt.tarih_id DESC
    """
    with conn.cursor() as cur:
        cur.execute(sorgu)
        satirlar = cur.fetchall()
    return pd.DataFrame(satirlar, columns=["tarih_id", "yil_ay"])


def iller_getir(conn: Connection) -> pd.DataFrame:
    """İl filtresi için dim_il'in tamamı (81 il)."""
    with conn.cursor() as cur:
        cur.execute("SELECT il_kodu, il_adi FROM dim_il ORDER BY il_adi")
        satirlar = cur.fetchall()
    return pd.DataFrame(satirlar, columns=["il_kodu", "il_adi"])
