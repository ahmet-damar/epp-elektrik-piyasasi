"""EPP — Faz 2 dashboard için salt-okunur analitik sorgular (+ Faz 3 hava normalizasyonu).

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

from worker import kpi

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


def uretim_kaynak_geneli_getir(conn: Connection, tarih_id: int) -> pd.DataFrame:
    """`fact_uretim_kaynak_geneli`'den TEK bir dönem için kaynak bazında
    üretim (il kırılımı YOK, Lisanslı+Lisanssız İKİSİ DE — çağıran gerekirse
    `lisans` kolonuyla filtreler). Kolonlar: kaynak, yenilenebilir, lisans,
    uretim_mwh.

    **KPI-02/03/06/07 için eklendi (2026-09-09, Aşama 3/ADIM 5 madde 2):**
    `uretim_getir()` (il×kaynak `fact_uretim`) bu grain'de `uretim_mwh`'yi
    HİÇ vermiyordu (bkz. o fonksiyonun/§5.7'nin modül notu — EPDK hiçbir
    formatta il×kaynak joint üretim kırılımı yayımlamıyor) — bu yüzden
    KPI-02/03/06/07 hep 'veri yok' gösteriyordu. `fact_uretim_kaynak_
    geneli` (ülke geneli, il kırılımsız) artık GERÇEK aylık üretim veriyor
    (2026-01'den itibaren, Excel T2+T5) — bu fonksiyon o KPI'ların girdisini
    buraya taşır. `uretim_getir()`'in YERİNE GEÇMEZ — KPI-01 (kurulu güç,
    STOK) ve KPI-05'in PAYDASI (kurulu güç) hâlâ `fact_uretim.kurulu_guc_mw`
    kullanır (bkz. `dogru_kapasite_faktoru()` modül notu, lisans_id
    tutarlılığı KRİTİK)."""
    kolonlar = ["kaynak", "yenilenebilir", "lisans", "uretim_mwh"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dk.kaynak_adi, dk.yenilenebilir_mi, dl.tur, fukg.uretim_mwh
            FROM fact_uretim_kaynak_geneli fukg
            JOIN dim_kaynak dk ON dk.kaynak_id = fukg.kaynak_id
            JOIN dim_lisans dl ON dl.lisans_id = fukg.lisans_id
            WHERE fukg.tarih_id = %s AND fukg.is_active
            """,
            (tarih_id,),
        )
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=kolonlar)
    if not df.empty:
        df["lisans"] = df["lisans"].map(_LISANS_GORUNUM).fillna(df["lisans"])
        df["yenilenebilir"] = df["yenilenebilir"].astype(bool)
    _numerik(df, ["uretim_mwh"])
    return df


def kapasite_faktoru_girdisi_getir(conn: Connection, tarih_id: int) -> pd.DataFrame:
    """KPI-05 (Kapasite Faktörü) için pay VE paydayı AYNI lisans filtresiyle
    (yalnız Lisanslı) getirir — tek satırlık `[kurulu_guc_mw, uretim_mwh]`.

    **KRİTİK (2026-09-09, ADIM 5 madde 3, sessiz hata riski):** Pay
    `fact_uretim_kaynak_geneli`'den (T2 = yalnız LİSANSLI üretim) — payda
    ise `fact_uretim.kurulu_guc_mw`'dan geliyor ve O TABLODA hem T1
    (Lisanslı) hem T4 (Lisanssız) kurulu güç BİRLİKTE var. `lisans_id` her
    iki tarafta da AYNI şekilde (yalnız Lisanslı) filtrelenmezse payda
    olduğundan büyük çıkar ve kapasite faktörü SESSİZCE (hatasız) sistematik
    düşük hesaplanır. Bu yüzden filtre iki ayrı çağıranın tutarlılığına
    bırakılmadan TEK bir yerde (burada) merkezi olarak uygulanır — bkz.
    worker/tests/test_analytics_integration.py::
    test_kapasite_faktoru_girdisi_lisans_filtresi_olmadan_yanilticidir
    (filtresiz/yanlış yolun GERÇEKTEN farklı ve düşük çıktığını kanıtlar)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(fu.kurulu_guc_mw), 0)
            FROM fact_uretim fu
            JOIN dim_lisans dl ON dl.lisans_id = fu.lisans_id
            WHERE fu.tarih_id = %s AND fu.is_active AND dl.tur = 'Lisansli'
            """,
            (tarih_id,),
        )
        satir_kurulu = cur.fetchone()
        assert satir_kurulu is not None  # COALESCE(SUM,0): agregat, hep 1 satır döner
        (kurulu,) = satir_kurulu
        cur.execute(
            """
            SELECT COALESCE(SUM(fukg.uretim_mwh), 0)
            FROM fact_uretim_kaynak_geneli fukg
            JOIN dim_lisans dl ON dl.lisans_id = fukg.lisans_id
            WHERE fukg.tarih_id = %s AND fukg.is_active AND dl.tur = 'Lisansli'
            """,
            (tarih_id,),
        )
        satir_uretim = cur.fetchone()
        assert satir_uretim is not None
        (uretim_mwh,) = satir_uretim
    df = pd.DataFrame([{"kurulu_guc_mw": kurulu, "uretim_mwh": uretim_mwh}])
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


def ulke_geneli_tuketim_getir(conn: Connection, tarih_id: int) -> pd.DataFrame:
    """`fact_tuketim_ulke_geneli`'den TEK bir dönem için grup bazında tüketim
    (il kırılımı YOK, Sanayi DAHİL). Kolonlar: grup, tuketim_mwh.

    **KPI-13 (YoY) için eklendi (2026-09-08, Aşama 3/ADIM 2):** `tuketim_
    getir()` (il bazlı `fact_tuketim`) Word yıllarında (2016-2025) Sanayi
    HİÇ içermediğinden, 2025↔2026 gibi Word/Excel sınırını geçen YoY
    karşılaştırmaları `kpi_13_yoy()`'un grup-kümesi korumasına takılıp
    HER ZAMAN 'hesaplanamaz' dönüyordu. `fact_tuketim_ulke_geneli` artık
    2016-2025 (Word, T11 Genel Toplam) VE 2026+ (Excel, T11 Genel Toplam
    de-kümülatif edilerek) için Sanayi DAHİL AYNI 5 grubu veriyor — bu
    fonksiyon dashboard'un KPI-13 girdisini buraya taşımak için var, `tuketim_
    getir()`'in YERİNE GEÇMEZ (il bazlı grafikler/KPI-08,09,10 hâlâ onu
    kullanır)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dg.grup_adi, ftu.tuketim_mwh
            FROM fact_tuketim_ulke_geneli ftu
            JOIN dim_tuketici_grubu dg ON dg.grup_id = ftu.grup_id
            WHERE ftu.tarih_id = %s AND ftu.is_active
            """,
            (tarih_id,),
        )
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=["grup", "tuketim_mwh"])
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
    radyasyon, ruzgar. fact_hava_aylik Faz 3'te UPSERT modeline geçti (bkz.
    migration 20260819_0009) — is_active YOK, her (il,tarih_id) için tek
    güncel satır zaten var. Open-Meteo hiç çekilmediyse boş DataFrame
    dönebilir; çağıran 'veri yok' göstermeli."""
    kolonlar = ["il", "il_kodu", "t_ort", "hdd", "cdd", "radyasyon", "ruzgar"]
    sorgu = """
        SELECT di.il_adi, fh.il_kodu, fh.t_ort, fh.hdd, fh.cdd, fh.radyasyon, fh.ruzgar
        FROM fact_hava_aylik fh
        JOIN dim_il di ON di.il_kodu = fh.il_kodu
        WHERE fh.tarih_id = %s
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


def sistem_parametre_getir(conn: Connection) -> dict[str, float]:
    """OD-1: HDD/CDD baz sıcaklıkları vb. sistem_parametre'den okunur, koda
    gömülmez. Anahtarlar: hdd_baz_c, cdd_baz_c, hava_norm_yil, tuketim_norm_yil
    (bkz. migration 20260819_0004)."""
    with conn.cursor() as cur:
        cur.execute("SELECT parametre_adi, parametre_degeri FROM sistem_parametre")
        satirlar = cur.fetchall()
    return {ad: float(deger) for ad, deger in satirlar}


def _il_tuketim_hava_getir(conn: Connection, il_kodu: int) -> pd.DataFrame:
    """KPI-11/12'nin TEK veri kaynağı: bir ilin tüm dönemlerinde toplam
    tuketim_mwh (tüm grup/baglanti) + o dönemin hdd/cdd'si + yil/ay.
    Regresyon (β/γ), hava normu ve tüketim normu hepsi bundan (pandas'ta
    filtrelenerek) türetilir — bkz. kpi_11_12_hesapla()."""
    kolonlar = ["tarih_id", "yil", "ay", "tuketim_mwh", "hdd", "cdd"]
    sorgu = """
        SELECT dt.tarih_id, dt.yil, dt.ay, SUM(ft.tuketim_mwh) AS tuketim_mwh,
               fh.hdd, fh.cdd
        FROM fact_tuketim ft
        JOIN dim_tarih dt ON dt.tarih_id = ft.tarih_id
        JOIN fact_hava_aylik fh
          ON fh.il_kodu = ft.il_kodu AND fh.tarih_id = ft.tarih_id
        WHERE ft.il_kodu = %s AND ft.is_active
        GROUP BY dt.tarih_id, dt.yil, dt.ay, fh.hdd, fh.cdd
        ORDER BY dt.tarih_id
    """
    with conn.cursor() as cur:
        cur.execute(sorgu, [il_kodu])
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=kolonlar)
    _numerik(df, ["tuketim_mwh", "hdd", "cdd"])
    return df


def kpi_11_12_hesapla(
    conn: Connection,
    il_kodu: int,
    tarih_id: int,
    hava_norm_yil: int = 10,
    tuketim_norm_yil: int = 5,
) -> dict[str, float | None]:
    """KPI-11 (arındırılmış tüketim) + KPI-12 (norm sapması) için gereken
    geçmiş veriyi çeker ve worker/kpi.py'nin SAF fonksiyonlarını sırayla
    çağırır: β/γ regresyonu -> hava normu (OD-2: hava_norm_yil, SABİT
    pencere) -> tüketim normu (OD-2: tuketim_norm_yil, ROLLING pencere,
    aynı-ay ARINDIRILMIŞ ortalama) -> arındırılmış + KPI-12. Zincirin
    HERHANGİ bir adımında yeterli geçmiş yoksa sonraki adımlar atlanır,
    ilgili alanlar None ('hesaplanamaz') kalır — sahte değer üretilmez.
    hava_norm_yil/tuketim_norm_yil çağıran tarafından sistem_parametre'den
    (hava_norm_yil, tuketim_norm_yil) okunup geçirilmelidir (OD-1/OD-2)."""
    sonuc: dict[str, float | None] = {
        "beta": None,
        "gamma": None,
        "hava_norm_hdd": None,
        "hava_norm_cdd": None,
        "tuketim_norm": None,
        "arindirilmis": None,
        "kpi_12": None,
    }

    yil, ay = divmod(tarih_id, 100)
    gecmis = _il_tuketim_hava_getir(conn, il_kodu)
    if gecmis.empty:
        return sonuc

    katsayilar = kpi.beta_gamma_tahmin_et(gecmis)
    if katsayilar is None:
        return sonuc
    beta, gamma, _sabit = katsayilar
    sonuc["beta"], sonuc["gamma"] = beta, gamma

    ayni_ay = gecmis[gecmis["ay"] == ay]
    hava_penceresi = ayni_ay[
        (ayni_ay["yil"] < yil) & (ayni_ay["yil"] >= yil - hava_norm_yil)
    ]
    normu = kpi.hava_normu_hesapla(
        hava_penceresi[["hdd", "cdd"]], yil_sayisi=hava_norm_yil
    )
    if normu is None:
        return sonuc
    hdd_norm, cdd_norm = normu
    sonuc["hava_norm_hdd"], sonuc["hava_norm_cdd"] = hdd_norm, cdd_norm

    tuketim_penceresi = ayni_ay[
        (ayni_ay["yil"] < yil) & (ayni_ay["yil"] >= yil - tuketim_norm_yil)
    ].copy()
    tuketim_norm: float | None = None
    if not tuketim_penceresi.empty:
        tuketim_penceresi["arindirilmis"] = tuketim_penceresi.apply(
            lambda satir: kpi.kpi_11_arindirilmis_tuketim(
                satir["tuketim_mwh"],
                satir["hdd"],
                satir["cdd"],
                hdd_norm,
                cdd_norm,
                beta,
                gamma,
            ),
            axis=1,
        )
        tuketim_norm = kpi.tuketim_normu_hesapla(
            tuketim_penceresi["arindirilmis"], yil_sayisi=tuketim_norm_yil
        )
    sonuc["tuketim_norm"] = tuketim_norm

    simdiki = gecmis[gecmis["tarih_id"] == tarih_id]
    if simdiki.empty:
        return sonuc
    satir = simdiki.iloc[0]
    arindirilmis = kpi.kpi_11_arindirilmis_tuketim(
        satir["tuketim_mwh"],
        satir["hdd"],
        satir["cdd"],
        hdd_norm,
        cdd_norm,
        beta,
        gamma,
    )
    sonuc["arindirilmis"] = arindirilmis
    sonuc["kpi_12"] = kpi.kpi_12_norm_sapmasi(arindirilmis, tuketim_norm)
    return sonuc


def yillik_tuketim_serisi_getir(conn: Connection) -> pd.DataFrame:
    """KPI-25 (tüketim CAGR, RESMİ "toplam tüketim" tanımı) girdisi: yıl
    başına toplam tuketim_mwh, **YALNIZ `fact_tuketim_ulke_geneli`**'den
    (akış/flow metriği, aylar toplanır). Kolonlar: yil, tuketim_mwh.

    **Kaynak kararı (2026-09-08, Aşama 2/C5):** Önceden (2026-09-02'den bu
    yana) bu fonksiyon il bazlı `fact_tuketim`'i, "yalnız Sanayi grubunu
    İÇEREN yıllar" filtresiyle okuyordu — Sanayi Word (.docx) kaynaklı
    2016-2025 dönemlerinde `fact_tuketim`'e HİÇ girmediğinden (Karar 2,
    `baglanti` ayrımı kaynakta yok) bu filtre pratikte yalnız 2026'yı
    bırakıyor, KPI-25 sürekli 'hesaplanamaz' dönüyordu. `fact_tuketim_
    ulke_geneli` (2026-09-05/08'de eklendi) artık 2016-2025'in TAMAMI için
    Sanayi DAHİL ülke geneli veri sağladığından KPI-25 TAMAMEN bu tabloya
    taşındı — il bazlı `fact_tuketim` ile ASLA KARIŞTIRILMAZ (grain
    karışımı riski, bkz. dokumanlar/10_TEKNIK_MASTER_DOKUMAN.md §11.2).

    **Dahil edilme şartı — tam yıl VE 5/5 grup** (alt sorgu `HAVING`):
    bir yıl yalnız TÜM 12 ayı VE her ayda TÜM 5 tüketici grubu (`COUNT(*) =
    12*5 = 60`) mevcutsa seriye girer. Bu, 2016'yı OTOMATİK ve KASITLI
    olarak dışarıda bırakır — 2016-12 Tarımsal, ülke seviyesinde de negatif
    çıktığı için hiç yüklenmedi (59/60 satır, bkz. §11.3), bu KPI-25 için
    de "veri yok" (None/'hesaplanamaz' katkısı, sahte bir sayı DEĞİL)
    anlamına gelir — altı ay sonra "2016 neden CAGR'da yok" diye yeniden
    araştırılmasın diye burada AÇIKÇA not düşülüyor.

    Sanayi hariç, ayrı bir CAGR için bkz. `yillik_tuketim_sanayi_haric_
    serisi_getir()` (KPI-27, ayrı bir metrik, İL BAZLI `fact_tuketim`'den,
    KPI-25'in YERİNE GEÇMEZ, kaynak DEĞİŞMEDİ)."""
    sorgu = """
        SELECT dt.yil, SUM(ftu.tuketim_mwh) AS tuketim_mwh
        FROM fact_tuketim_ulke_geneli ftu
        JOIN dim_tarih dt ON dt.tarih_id = ftu.tarih_id
        WHERE ftu.is_active
          AND dt.yil IN (
              SELECT dt2.yil
              FROM fact_tuketim_ulke_geneli ftu2
              JOIN dim_tarih dt2 ON dt2.tarih_id = ftu2.tarih_id
              WHERE ftu2.is_active AND dt2.donem_tipi = 'aylik'
              GROUP BY dt2.yil
              HAVING count(DISTINCT dt2.ay) = 12
                 AND count(DISTINCT ftu2.grup_id) = 5
                 AND count(*) = 60
          )
        GROUP BY dt.yil
        ORDER BY dt.yil
    """
    with conn.cursor() as cur:
        cur.execute(sorgu)
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=["yil", "tuketim_mwh"])
    _numerik(df, ["tuketim_mwh"])
    return df


def yillik_tuketim_sanayi_haric_serisi_getir(conn: Connection) -> pd.DataFrame:
    """KPI-27 (Sanayi-hariç tüketim CAGR) girdisi — KPI-25'İN YERİNE GEÇMEZ,
    ayrı bir metrik, kaynağı İL BAZLI `fact_tuketim` (KPI-25 2026-09-08'de
    `fact_tuketim_ulke_geneli`'ye taşındı, bkz. `yillik_tuketim_serisi_
    getir()` — bu fonksiyon DEĞİŞMEDİ, kasıtlı olarak il bazlı kalıyor).
    Yıl başına toplam tuketim_mwh, Sanayi grubu HER YILDAN açıkça
    ÇIKARILARAK hesaplanır. Sonuç: resmi "toplam tüketim" (KPI-25) DEĞİL,
    yalnız ek bağlam için bir alt-küme.

    **Yalnız TAM yıllar** (12 farklı ay) dahil edilir — 2026 şu an yalnız
    6 aylık kısmi veri içeriyor (dokumanlar/06_canli_veri_operasyon_gunlugu.md,
    2026-08-31), kısmi bir yılın toplamını tam yıllarla karşılaştırmak
    AYNI tür distorsiyonu (kısmi-yıl/tam-yıl karışıklığı) yeniden
    üretirdi — KPI-25'in düzeltilen ikinci sorunuyla aynı kök neden.
    2026 12 aya tamamlanınca otomatik olarak seriye girecek."""
    sorgu = """
        SELECT dt.yil, SUM(ft.tuketim_mwh) AS tuketim_mwh
        FROM fact_tuketim ft
        JOIN dim_tarih dt ON dt.tarih_id = ft.tarih_id
        JOIN dim_tuketici_grubu g ON g.grup_id = ft.grup_id
        WHERE ft.is_active AND g.grup_adi != 'Sanayi'
          AND dt.yil IN (
              SELECT dt2.yil
              FROM fact_tuketim ft2
              JOIN dim_tarih dt2 ON dt2.tarih_id = ft2.tarih_id
              WHERE ft2.is_active AND dt2.donem_tipi = 'aylik'
              GROUP BY dt2.yil
              HAVING count(DISTINCT dt2.ay) = 12
          )
        GROUP BY dt.yil
        ORDER BY dt.yil
    """
    with conn.cursor() as cur:
        cur.execute(sorgu)
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=["yil", "tuketim_mwh"])
    _numerik(df, ["tuketim_mwh"])
    return df


def yillik_yenilenebilir_kurulu_guc_serisi_getir(conn: Connection) -> pd.DataFrame:
    """KPI-26 (yenilenebilir kurulu güç CAGR) girdisi: yıl başına, o yılın
    EN GÜNCEL ayındaki toplam yenilenebilir kurulu_guc_mw (dim_kaynak.
    yenilenebilir_mi=true) — kurulu güç bir STOK metriğidir, aylar
    TOPLANMAZ, yılın son ölçümü alınır. Kolonlar: yil, kurulu_guc_mw.

    **Yalnız Lisanslı verisi OLAN yıllar dahil edilir** (alt sorgu). Neden:
    Word (.docx) kaynaklı 2023-2025 dönemleri için T1 (Lisanslı kurulu güç)
    hiç yüklenmedi — kaynakta yok, il×kaynak birleşik tablo mevcut değil
    (dokumanlar/07_word_parser_kapsam.md, Bulgu 5 + Karar 3). Yalnız T4
    (Lisanssız) yüklendi. Bu filtre OLMASAYDI, 2023-2025 (yalnız Lisanssız
    — Türkiye'nin toplam yenilenebilir kapasitesinin küçük bir kesri,
    büyük rüzgar/güneş/hidrolik santralleri Lisanslı'dır) 2026 (Excel,
    Lisanslı+Lisanssız TAM) ile AYNI CAGR serisine karışır ve KPI-26 sahte,
    çarpıtılmış bir büyüme/düşüş sayısı üretir — KPI-25'te (Sanayi dahil/
    hariç) bulunan sorunla AYNI kök neden, farklı KPI. Lisanslı verisi
    olmayan bir yıl, bu fonksiyon için 'veri yok' (KPI-25/26'nın var olan
    None="hesaplanamaz" davranışıyla tutarlı) sayılır — 2027+'de T1 gerçek
    Excel verisiyle geldiğinde otomatik olarak seriye girecek, kod
    değişikliği gerekmeyecek."""
    sorgu = """
        SELECT dt.tarih_id, dt.yil, dt.ay, SUM(fu.kurulu_guc_mw) AS kurulu_guc_mw
        FROM fact_uretim fu
        JOIN dim_tarih dt ON dt.tarih_id = fu.tarih_id
        JOIN dim_kaynak dk ON dk.kaynak_id = fu.kaynak_id
        WHERE fu.is_active AND dk.yenilenebilir_mi = true
          AND dt.yil IN (
              SELECT dt2.yil
              FROM fact_uretim fu2
              JOIN dim_tarih dt2 ON dt2.tarih_id = fu2.tarih_id
              JOIN dim_lisans dl2 ON dl2.lisans_id = fu2.lisans_id
              WHERE fu2.is_active AND dl2.tur = 'Lisansli'
              GROUP BY dt2.yil
          )
        GROUP BY dt.tarih_id, dt.yil, dt.ay
        ORDER BY dt.tarih_id
    """
    with conn.cursor() as cur:
        cur.execute(sorgu)
        satirlar = cur.fetchall()
    df = pd.DataFrame(satirlar, columns=["tarih_id", "yil", "ay", "kurulu_guc_mw"])
    _numerik(df, ["kurulu_guc_mw"])
    if df.empty:
        return pd.DataFrame(columns=["yil", "kurulu_guc_mw"])
    en_guncel = df.loc[df.groupby("yil")["ay"].idxmax()]
    return en_guncel[["yil", "kurulu_guc_mw"]].reset_index(drop=True)


def cagr_seriden_hesapla(seri: pd.DataFrame, deger_kolonu: str) -> float | None:
    """seri: en az iki farklı yıl içeren (yil, deger_kolonu) DataFrame — bkz.
    yillik_tuketim_serisi_getir/yillik_yenilenebilir_kurulu_guc_serisi_getir.
    n = son_yil - ilk_yil (dokumanlar/04_kpi_sozlesmeleri.md, SRS Tablo 26
    örneği: 2021->2025 => n=4). worker/kpi.py kpi_cagr()'ı çağırır."""
    gecerli = seri.dropna(subset=[deger_kolonu]).sort_values("yil")
    if len(gecerli) < 2:
        return None
    ilk = float(gecerli[deger_kolonu].iloc[0])
    son = float(gecerli[deger_kolonu].iloc[-1])
    n = int(gecerli["yil"].iloc[-1] - gecerli["yil"].iloc[0])
    return kpi.kpi_cagr(ilk, son, n)


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


def kapsam_disi_getir(conn: Connection, tarih_id: int) -> pd.DataFrame:
    """Seçili dönem için `veri_kapsam_disi`'de işaretli kayıtları döndürür
    (Aşama 7, dokumanlar/06_canli_veri_operasyon_gunlugu.md): dashboard
    boş/'veri yok' göstermek YERİNE, o verinin kaynakta neden mevcut
    olmadığını (Karar 1/3, kalıcı kaynak hataları vb.) açıkça göstersin
    diye. Kolonlar: fact_tablosu, nitelik, sebep."""
    sorgu = """
        SELECT fact_tablosu, nitelik, sebep
        FROM veri_kapsam_disi
        WHERE tarih_id = %s
        ORDER BY fact_tablosu, nitelik
    """
    with conn.cursor() as cur:
        cur.execute(sorgu, [tarih_id])
        satirlar = cur.fetchall()
    return pd.DataFrame(satirlar, columns=["fact_tablosu", "nitelik", "sebep"])


def son_batchler_getir(conn: Connection, limit: int = 20) -> pd.DataFrame:
    """Dashboard 'Sistem Durumu' bölümü için: en son N `ingestion_batch`
    kaydı, `source_asset`'ten dosya adı/kaynak türü ile birleştirilmiş.
    Şema DEĞİŞMEDİ, salt okuma. Kolonlar: batch_id, source_type, file_name,
    source_period, status, accepted_row_count, rejected_row_count,
    error_summary, created_at."""
    sorgu = """
        SELECT ib.batch_id, sa.source_type, sa.file_name, sa.source_period,
               ib.status, ib.accepted_row_count, ib.rejected_row_count,
               ib.error_summary, ib.created_at
        FROM ingestion_batch ib
        JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
        ORDER BY ib.batch_id DESC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sorgu, [limit])
        satirlar = cur.fetchall()
    return pd.DataFrame(
        satirlar,
        columns=[
            "batch_id",
            "source_type",
            "file_name",
            "source_period",
            "status",
            "accepted_row_count",
            "rejected_row_count",
            "error_summary",
            "created_at",
        ],
    )


def son_job_durumlari_getir(conn: Connection, limit: int = 20) -> pd.DataFrame:
    """Dashboard 'Sistem Durumu' bölümü için: en son N `job_status` kaydı
    (Faz 1 asenkron kuyruk). Şema DEĞİŞMEDİ, salt okuma. Kolonlar: job_id,
    correlation_id, status, attempt_count, next_retry_at, updated_at."""
    sorgu = """
        SELECT job_id, correlation_id, status, attempt_count, next_retry_at, updated_at
        FROM job_status
        ORDER BY job_id DESC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sorgu, [limit])
        satirlar = cur.fetchall()
    return pd.DataFrame(
        satirlar,
        columns=[
            "job_id",
            "correlation_id",
            "status",
            "attempt_count",
            "next_retry_at",
            "updated_at",
        ],
    )


def iller_getir(conn: Connection) -> pd.DataFrame:
    """İl filtresi için dim_il'in tamamı (81 il)."""
    with conn.cursor() as cur:
        cur.execute("SELECT il_kodu, il_adi FROM dim_il ORDER BY il_adi")
        satirlar = cur.fetchall()
    return pd.DataFrame(satirlar, columns=["il_kodu", "il_adi"])


def kpi_11_12_ulusal_hesapla(
    conn: Connection, tarih_id: int, hava_norm_yil: int = 10, tuketim_norm_yil: int = 5
) -> dict[str, float | int | None]:
    """Görev 4 (2026-09-05, Seçenek A — dokumanlar/06_canli_veri_operasyon_
    gunlugu.md): "Türkiye Geneli" seçiliyken KPI-11/12'yi 81 ilin KENDİ
    regresyonlarını (`kpi_11_12_hesapla`, HİÇ DEĞİŞTİRİLMEDİ) topla(ştır)
    arak hesaplar — Seçenek B (tek bir "ulusal HDD/CDD" uydurup ayrı bir
    regresyon) BİLİNÇLİ OLARAK reddedildi: İstanbul'u Hakkari'yle eşit
    ağırlıklandırmak fiziksel olarak anlamsız olurdu, gerçek bölgesel
    iklim tepkisini bulanıklaştırırdı.

    KPI-11 (arındırılmış tüketim) toplanabilir bir büyüklük — doğrudan
    81 ilin toplamı. KPI-12 (norm sapması, %) toplanamaz — payı
    (arındırılmış) VE paydayı (tüketim_norm) AYRI AYRI topla(ştır)ıp
    `kpi.kpi_12_norm_sapmasi()`'yi TOPLAMLAR üzerinde BİR KEZ çağırıyoruz
    (81 ilin kendi yüzdelerini ortalamak YERİNE — o, büyük illeri küçük
    illerle eşit ağırlıklandırır, yanlış olurdu).

    Yeterli geçmişi olmayan iller (`kpi_11_12_hesapla` None döndürür)
    toplamdan SESSİZCE değil, `kapsam_il_sayisi` ile GÖRÜNÜR şekilde
    dışlanır — çağıran (`app/dashboard.py`) bunu kullanıcıya
    gösterebilir (örn. "81 ilin 74'ü dahil edildi")."""
    il_listesi = iller_getir(conn)
    arindirilmis_toplam = 0.0
    tuketim_norm_toplam = 0.0
    kapsam_il_sayisi = 0
    for il_kodu in il_listesi["il_kodu"]:
        sonuc = kpi_11_12_hesapla(
            conn, int(il_kodu), tarih_id, hava_norm_yil, tuketim_norm_yil
        )
        if sonuc["arindirilmis"] is None or sonuc["tuketim_norm"] is None:
            continue
        arindirilmis_toplam += sonuc["arindirilmis"]
        tuketim_norm_toplam += sonuc["tuketim_norm"]
        kapsam_il_sayisi += 1

    if kapsam_il_sayisi == 0:
        return {"arindirilmis": None, "kpi_12": None, "kapsam_il_sayisi": 0}

    kpi_12_ulusal = kpi.kpi_12_norm_sapmasi(arindirilmis_toplam, tuketim_norm_toplam)
    return {
        "arindirilmis": arindirilmis_toplam,
        "kpi_12": kpi_12_ulusal,
        "kapsam_il_sayisi": kapsam_il_sayisi,
    }


def kpi_esikleri_getir(
    conn: Connection, surum: str = "v1"
) -> dict[str, dict[str, float | str]]:
    """Dashboard trafik ışığı (Görev 3, 2026-09-05) için `kpi_esik`
    satırlarını `kpi_id`'ye göre bir sözlüğe çevirir. `kirmizi_alt` KASITLI
    OLARAK sözlüğe dahil edilmiyor (worker/kpi.py:esik_rengi() yalnız
    yesil_alt/sari_alt/yon kullanıyor — bkz. o fonksiyonun sözleşme notu).
    Bir KPI için satır yoksa (eşik tanımlanmamış) o KPI sözlükte hiç
    görünmez — çağıran `.get(kpi_id)` ile kontrol etmeli."""
    sorgu = """
        SELECT kpi_id, yesil_alt, sari_alt, yon
        FROM kpi_esik
        WHERE surum = %s
    """
    with conn.cursor() as cur:
        cur.execute(sorgu, [surum])
        satirlar = cur.fetchall()
    return {
        kpi_id: {"yesil_alt": float(yesil_alt), "sari_alt": float(sari_alt), "yon": yon}
        for kpi_id, yesil_alt, sari_alt, yon in satirlar
    }
