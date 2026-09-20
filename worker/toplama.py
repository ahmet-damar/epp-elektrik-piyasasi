"""EPP — Toplama katmanı (agregasyon): çözünürlük (ay/çeyrek/yıl) + aralık
parametreli, kapsam bayrağı döndüren erişim fonksiyonları.
(`Claude outputs/PROMPT_TOPLAMA_KATMANI_2026-09-19.md`, 2026-09-19/20)

Bu turda YALNIZ VERİ KATMANI — dashboard'un (UI, AYRI bir tur) çağıracağı
ince bir erişim katmanı. Kapsanan tablolar: fact_tuketim, fact_tuketim_
ulke_geneli, fact_uretim_kaynak_geneli, fact_uretim_il_geneli (bkz.
migration `20260920_0001_toplama_katmani_views.sql`'in `vw_toplama_*`
view'leri — is_active filtresi + dim_* join'i + gerekliyse il_kodu
üzerinden ÜLKE GENELİNE toplama ORADA yapılır).

**Tasarım kararları (verilmiş, PROMPT'ta):**

1. Çözünürlük (`Grain`: ay/çeyrek/yıl) ve aralık (`baslangic_tarih_id`/
   `bitis_tarih_id`) BAĞIMSIZ iki parametre — "10 yıllık aylık" gibi en
   çok kullanılacak kombinasyon bunun için üretilebilir.
2. R12 (kayan 12 aylık toplam) `r12_getir()` — TEK seri (tüm kırılımların
   toplamı), mevsimselliği siler, her ay yeni nokta üretir.
3. Çeyrek = TAKVİM çeyreği (Q1=Oca-Mar, Q2=Nis-Haz, Q3=Tem-Eyl,
   Q4=Eki-Ara) — `dim_tarih.ceyrek` ile ZATEN aynı tanım (bkz.
   `worker/ingest.py:tarih_bilesenleri()`).
4. **ORAN KURALI:** önce topla, sonra oranla — asla oranların
   ortalaması alınmaz. `uretim_yenilenebilir_payi_getir()` toplamları
   AYRI AYRI SUM'lar, oranı EN SONDA hesaplar (bkz. o fonksiyonun notu +
   `worker/tests/test_toplama_oran_kurali.py`).
5. **KAPSAM BAYRAĞI:** her satır `beklenen_donem_sayisi`,
   `mevcut_donem_sayisi`, `tam_mi` taşır. Eksik dönemde toplam SESSİZCE
   düşük dönmez — `tam_mi=False` açıkça işaretlenir. `mevcut_donem_
   sayisi`'nin neye dayandığı TABLOYA göre değişir (bkz.
   `_kapsam_ve_deger_df()`'in `kirilim_bazinda_kapsam` notu, madde 7 ile
   ilişkisi): `fact_tuketim`/`fact_tuketim_ulke_geneli`'de KIRILIM
   (grup) düzeyinde (EPDK her ay TÜM grupları basar, birinin yokluğu
   KALICI eksikliktir — örn. 2016-12 Tarımsal); `fact_uretim_kaynak_
   geneli`/`fact_uretim_il_geneli`'de TABLO düzeyinde (bir kaynağın o ay
   hiç listelenmemesi "üretim yok" demektir, "veri eksik" değil).
6. **KÜMÜLATİF KOLON TUZAĞI:** `vw_toplama_tuketim_ulke_geneli_aylik`
   yalnız `tuketim_mwh` (de-kümülatif) expose eder,
   `kumulatif_tuketim_mwh` view'de HİÇ SEÇİLMEZ — bu modülün yanlışlıkla
   kümülatif kolonu toplaması YAPISAL OLARAK imkânsız.
7. **"Kaynak satırı yok" ≠ "veri yok":** bkz. madde 5 — ay yüklü + bu
   kırılımın satırı yok → SUM doğal olarak 0 katkı verir (satır hiç yok,
   toplamı etkilemez) VE `mevcut_donem_sayisi` bundan ETKİLENMEZ (tablo
   düzeyinde hesaplanır). Ay hiç yüklü değilse `mevcut_donem_sayisi`
   düşer, `tam_mi=False` olur.
8. **2025→2026 dikişi:** `donem_araligi_dikis_iceriyor_mu()` — Sanayi
   (Karar 2) + Lisanssız 2026'da seriye giriyor, Word yıllarında
   (≤2025) yok. Salt aritmetik, DB'ye gitmez — UI (AYRI tur) bunu
   etiketlemek için kullanacak.
9. **SQL'de, Python'da DEĞİL:** tüm SUM/COUNT/pencere fonksiyonu
   Postgres'te çalışır — bu modül yalnız grain'e göre SABİT şablonlardan
   (hiçbir zaman ham kullanıcı girdisi interpolasyonu YOK — `Grain` bir
   `Literal`, tablo/view adları `_TABLO_KAYIT`'ten, whitelist) parametreli
   SQL metni kurar, sonucu `pd.DataFrame`'e çevirir. `MATERIALIZED VIEW
   KULLANILMADI` (gerekçe: migration dosyasının notuna bkz.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import pandas as pd

if TYPE_CHECKING:
    from psycopg import Connection

Grain = Literal["ay", "ceyrek", "yil"]
TabloAdi = Literal[
    "tuketim", "tuketim_ulke_geneli", "uretim_kaynak_geneli", "uretim_il_geneli"
]

_GRAIN_DEGERLERI: tuple[Grain, ...] = ("ay", "ceyrek", "yil")

BEKLENEN_IL_SAYISI = 81

# whitelist: (ham fact tablosu — "yüklü ay" hesaplamasında, vw_toplama_* —
# değer hesaplamasında, değer kolonu adı). SQL metnine yalnız BURADAN
# gelen sabit adlar interpolasyon edilir, hiçbir zaman çağıranın girdisi.
_TABLO_KAYIT: dict[TabloAdi, tuple[str, str, str]] = {
    "tuketim": ("fact_tuketim", "vw_toplama_tuketim_aylik", "tuketim_mwh"),
    "tuketim_ulke_geneli": (
        "fact_tuketim_ulke_geneli",
        "vw_toplama_tuketim_ulke_geneli_aylik",
        "tuketim_mwh",
    ),
    "uretim_kaynak_geneli": (
        "fact_uretim_kaynak_geneli",
        "vw_toplama_uretim_kaynak_aylik",
        "uretim_mwh",
    ),
    "uretim_il_geneli": (
        "fact_uretim_il_geneli",
        "vw_toplama_uretim_il_aylik",
        "uretim_mwh",
    ),
}

_DONEM_ANAHTARI_VIEW: dict[Grain, str] = {
    "ay": "tarih_id",
    "ceyrek": "(yil * 10 + ceyrek)",
    "yil": "yil",
}
_DONEM_ANAHTARI_TAKVIM: dict[Grain, str] = {
    "ay": "t.tarih_id",
    "ceyrek": "(t.yil * 10 + t.ceyrek)",
    "yil": "t.yil",
}


def _grain_dogrula(grain: str) -> None:
    if grain not in _GRAIN_DEGERLERI:
        raise ValueError(
            f"Bilinmeyen çözünürlük: {grain!r} (beklenen: {_GRAIN_DEGERLERI})"
        )


def _tarih_araligina_ayir(
    baslangic_tarih_id: int, bitis_tarih_id: int
) -> tuple[int, int, int, int]:
    """YYYYMM tarih_id'lerini (yıl, ay) çiftlerine ayırır — `generate_series`
    için `make_date` girdisi. Yalnız AYLIK (YYYY00 yıllık DEĞİL) tarih_id
    kabul eder — toplama katmanının kendisi zaten yıllık/çeyreklik
    bucket'ları AYLIK ham veriden türetiyor, YYYY00 girdisi tanımsız."""
    if baslangic_tarih_id > bitis_tarih_id:
        raise ValueError(
            f"baslangic_tarih_id ({baslangic_tarih_id}) > bitis_tarih_id ({bitis_tarih_id})"
        )
    y1, m1 = divmod(baslangic_tarih_id, 100)
    y2, m2 = divmod(bitis_tarih_id, 100)
    if m1 == 0 or m2 == 0:
        raise ValueError(
            "toplama katmanı yalnız AYLIK tarih_id kabul eder (YYYY00 yıllık desteklenmiyor)"
        )
    return y1, m1, y2, m2


def _ay_ekle(tarih_id: int, delta: int) -> int:
    """`tarih_id` (YYYYMM) üzerinde `delta` ay ileri/geri kaydırır — yıl
    devrini doğru işler (örn. 202412 + 1 -> 202501). `worker/scripts/
    kapsam_raporu.py:ay_ekle()` ile AYNI mantık — bilerek yeniden
    tanımlandı (core modül, scripts/'e bağımlı OLMAMALI)."""
    yil, ay = divmod(tarih_id, 100)
    toplam_ay_indeksi = yil * 12 + (ay - 1) + delta
    yeni_yil, yeni_ay_indeksi = divmod(toplam_ay_indeksi, 12)
    return yeni_yil * 100 + (yeni_ay_indeksi + 1)


def donem_araligi_dikis_iceriyor_mu(
    baslangic_tarih_id: int, bitis_tarih_id: int
) -> bool:
    """2025→2026 dikişi (madde 8): Sanayi (Karar 2) + Lisanssız 2026'dan
    itibaren seriye giriyor, Word yıllarında (≤2025) hiç yok — bir aralık
    HER İKİ tarafı da kapsıyorsa toplamlarda YAPISAL bir basamak var
    demektir (grafik etiketlemezse "2026'da tüketim fırladı" diye
    okunur). Salt aritmetik — DB'ye gitmez, UI (ayrı tur) etiketlemek
    için kullanacak."""
    return baslangic_tarih_id <= 202512 and bitis_tarih_id >= 202601


# worker/analytics.py:_LISANS_GORUNUM ile AYNI çevrim — dim_lisans.tur
# DB'de ASCII saklanır (CHECK IN ('Lisansli','Lisanssiz')), view'ler bunu
# HAM döner (`lisans_turu`). Burada da uygulanmazsa çağıran (gelecekteki
# UI) 'Lisanslı' filtresiyle SESSİZCE 0 satır bulur — analytics.py'nin
# ZATEN çözdüğü tuzağın birebir tekrarı olurdu.
_LISANS_GORUNUM = {"Lisansli": "Lisanslı", "Lisanssiz": "Lisanssız"}


def _jit_kapat(cur: Any) -> None:
    """**2026-09-20 (`Claude outputs/PROMPT_UI_ZAMAN_SERISI_2026-09-20.md`
    Bölüm 1) — ÖLÇÜLDÜ, ÇÜRÜTÜLDÜ:** önceki turun kapanış raporu ~715ms'lik
    JIT derleme maliyetini "tek seferlik" sayıp göz ardı etmişti. 5 AYRI
    bağlantıda ölçüldüğünde (disposable): JIT açıkken TUTARLI ~805-1280ms,
    `SET jit=off` ile TUTARLI ~102ms — 8× fark HER koşuda tekrarlanıyor,
    amortisman YOK (Postgres JIT'i backend/sorgu arasında CACHE'lemiyor,
    dokümantasyonun kendi söylediği gibi). Canlıda da (salt okuma, gerçek
    veri) aynı yön doğrulandı: JIT açık ~265-310ms, kapalı ~195-210ms
    (network+pgbouncer baskın olduğundan oran daha küçük ama YÖN AYNI).
    Bu ölçek/şekildeki analitik sorgularda (küçük tablo, orta karmaşıklıkta
    agregasyon) JIT'in kendi belgelediği "az kazanç, olası kayıp" senaryosu
    — `SET LOCAL jit = off` (yalnız bu transaction'da, sunucu genelinde
    DEĞİL) tercih edildi: `jit_above_cost` eşiğini yükseltmek disposable'ın
    plan maliyetine göre "sihirli sayı" olurdu, canlıdaki gerçek veri
    hacminde farklı davranabilirdi — `SET LOCAL` her ortamda AYNI, ölçülmüş
    davranışı garanti eder."""
    cur.execute("SET LOCAL jit = off")


def _numerik_ve_bool(df: pd.DataFrame) -> None:
    for kolon in ("deger", "il_sayisi_min", "deger_r12"):
        if kolon in df.columns:
            df[kolon] = pd.to_numeric(df[kolon], errors="coerce")
    for kolon in ("tam_mi", "yenilenebilir_mi"):
        if kolon in df.columns:
            df[kolon] = df[kolon].astype(bool)
    if "lisans_turu" in df.columns:
        df["lisans_turu"] = (
            df["lisans_turu"].map(_LISANS_GORUNUM).fillna(df["lisans_turu"])
        )


def _kapsam_ve_deger_df(
    conn: Connection,
    *,
    tablo_adi: str,
    view_adi: str,
    breakdown_kolonlari: tuple[str, ...],
    deger_kolonu: str,
    il_kirilimi_var_mi: bool,
    kirilim_bazinda_kapsam: bool,
    grain: Grain,
    baslangic_tarih_id: int,
    bitis_tarih_id: int,
) -> pd.DataFrame:
    """Motor: grain'e göre bucket'lara ayırır, HER bucket için `deger_kolonu`
    toplamını VE kapsam bayrağını (beklenen/mevcut_donem_sayisi, tam_mi)
    SQL'de hesaplayıp döner.

    **`kirilim_bazinda_kapsam` — madde 5 ile madde 7'nin UZLAŞTIRILMASI:**
    iki farklı "eksik" türü var, KARIŞTIRILAMAZ:
    - `False` (TABLO düzeyi — `fact_uretim_kaynak_geneli`,
      `fact_uretim_il_geneli`): "mevcut_donem_sayisi", tablonun o ay
      HERHANGİ bir aktif satırı var mı sinyaline dayanır, KIRILIMDAN
      (örn. tek bir kaynak) BAĞIMSIZ — çünkü EPDK bir kaynağı (örn.
      Motorin/Nafta) o ay HİÇ listelemeyebilir, bu "üretim yok" demektir,
      "veri eksik" değil (madde 7). SUM zaten yokluğu 0 gibi ele alır.
    - `True` (KIRILIM düzeyi — `fact_tuketim`, `fact_tuketim_ulke_geneli`):
      "mevcut_donem_sayisi" HER kırılım değeri (örn. her tüketici grubu)
      için AYRI hesaplanır — çünkü EPDK'nın tüketim tablosu HER ay TÜM
      grupları (Aydınlatma/Kamu/Mesken/Sanayi-hariç/Tarımsal) basar; bir
      grubun belirli bir ayda YOKLUĞU (örn. 2016-12 Tarımsal) KALICI bir
      veri kaybıdır, "o ay o grup tüketmedi" değil — madde 5'in canlı
      örneği. Tablo düzeyi sinyal bunu KAÇIRIRDI (diğer gruplar o ay
      zaten yüklü olduğundan "tablo yüklü" derdi).

    `il_kirilimi_var_mi=True` ise `il_sayisi_min` (bucket'taki en düşük
    aylık il kardinalitesi) de döner, `tam_mi` buna da bağlı olur
    (`BEKLENEN_IL_SAYISI`'nden az olursa dönem 'tam' SAYILMAZ — bir
    ulusal toplamın 79/81 il'den türetilmiş olması SESSİZCE düşük bir
    toplam anlamına gelir, madde 5'in 2023-01/02 deprem örneği)."""
    _grain_dogrula(grain)
    y1, m1, y2, m2 = _tarih_araligina_ayir(baslangic_tarih_id, bitis_tarih_id)
    donem_view = _DONEM_ANAHTARI_VIEW[grain]
    donem_takvim = _DONEM_ANAHTARI_TAKVIM[grain]
    breakdown_sql = ", ".join(breakdown_kolonlari)
    breakdown_sql_d = ", ".join(f"d.{c}" for c in breakdown_kolonlari)
    breakdown_sql_bk = ", ".join(f"bk.{c}" for c in breakdown_kolonlari)
    esitlik_v_bk = " AND ".join(f"v.{c} = bk.{c}" for c in breakdown_kolonlari)
    esitlik_d_k = " AND ".join(f"d.{c} = k.{c}" for c in breakdown_kolonlari)
    il_secim_deger = ", MIN(il_sayisi) AS il_sayisi_min" if il_kirilimi_var_mi else ""
    il_secim_final = ", d.il_sayisi_min" if il_kirilimi_var_mi else ""
    il_tam_ifadesi = (
        f" AND (d.il_sayisi_min = {BEKLENEN_IL_SAYISI})" if il_kirilimi_var_mi else ""
    )
    takvim_cte = """
        takvim AS (
            SELECT
                (EXTRACT(year FROM gs)::int) * 100 + EXTRACT(month FROM gs)::int AS tarih_id,
                EXTRACT(year FROM gs)::int AS yil,
                ((EXTRACT(month FROM gs)::int - 1) / 3 + 1)::int AS ceyrek
            FROM generate_series(make_date(%(y1)s, %(m1)s, 1), make_date(%(y2)s, %(m2)s, 1), interval '1 month') AS gs
        )"""
    deger_cte = f"""
        deger AS (
            SELECT {donem_view} AS donem_anahtari, {breakdown_sql},
                   SUM({deger_kolonu}) AS deger{il_secim_deger}
            FROM {view_adi}
            WHERE tarih_id BETWEEN %(baslangic)s AND %(bitis)s
            GROUP BY {donem_view}, {breakdown_sql}
        )"""  # nosec B608 - view_adi/breakdown_sql/deger_kolonu YALNIZ çağıran sarmalayıcıların sabit whitelist'inden

    # tablo/view adları YALNIZ _TABLO_KAYIT/sarmalayıcı fonksiyonların
    # sabit whitelist'inden gelir — kullanıcı girdisi asla buraya
    # ulaşmaz, bandit B608 bu yüzden bilinçli olarak susturuldu.
    if kirilim_bazinda_kapsam:
        sorgu = f"""
            WITH {takvim_cte},
            breakdown_keys AS (
                SELECT DISTINCT {breakdown_sql} FROM {view_adi}
                WHERE tarih_id BETWEEN %(baslangic)s AND %(bitis)s
            ),
            hucre AS (
                SELECT {donem_takvim} AS donem_anahtari, {breakdown_sql_bk},
                       EXISTS (
                           SELECT 1 FROM {view_adi} v
                           WHERE v.tarih_id = t.tarih_id AND {esitlik_v_bk}
                       ) AS var_mi
                FROM takvim t
                CROSS JOIN breakdown_keys bk
            ),
            kapsam AS (
                SELECT donem_anahtari, {breakdown_sql},
                       COUNT(*) AS beklenen_donem_sayisi,
                       COUNT(*) FILTER (WHERE var_mi) AS mevcut_donem_sayisi
                FROM hucre
                GROUP BY donem_anahtari, {breakdown_sql}
            ),
            {deger_cte}
            SELECT d.donem_anahtari, {breakdown_sql_d},
                   d.deger{il_secim_final},
                   k.beklenen_donem_sayisi, k.mevcut_donem_sayisi,
                   (k.beklenen_donem_sayisi = k.mevcut_donem_sayisi{il_tam_ifadesi}) AS tam_mi
            FROM deger d
            JOIN kapsam k ON k.donem_anahtari = d.donem_anahtari AND {esitlik_d_k}
            ORDER BY d.donem_anahtari, {breakdown_sql}
        """  # nosec B608
    else:
        sorgu = f"""
            WITH {takvim_cte},
            yuklu AS (
                SELECT DISTINCT tarih_id FROM {tablo_adi} WHERE is_active
            ),
            kapsam AS (
                SELECT {donem_takvim} AS donem_anahtari,
                       COUNT(*) AS beklenen_donem_sayisi,
                       COUNT(y.tarih_id) AS mevcut_donem_sayisi
                FROM takvim t
                LEFT JOIN yuklu y USING (tarih_id)
                GROUP BY {donem_takvim}
            ),
            {deger_cte}
            SELECT d.donem_anahtari, {breakdown_sql_d},
                   d.deger{il_secim_final},
                   k.beklenen_donem_sayisi, k.mevcut_donem_sayisi,
                   (k.beklenen_donem_sayisi = k.mevcut_donem_sayisi{il_tam_ifadesi}) AS tam_mi
            FROM deger d
            JOIN kapsam k ON k.donem_anahtari = d.donem_anahtari
            ORDER BY d.donem_anahtari, {breakdown_sql}
        """  # nosec B608
    with conn.cursor() as cur:
        _jit_kapat(cur)
        cur.execute(
            sorgu,
            {
                "y1": y1,
                "m1": m1,
                "y2": y2,
                "m2": m2,
                "baslangic": baslangic_tarih_id,
                "bitis": bitis_tarih_id,
            },
        )
        satirlar = cur.fetchall()
        kolonlar = [c.name for c in cur.description]  # type: ignore[union-attr]
    df = pd.DataFrame(satirlar, columns=kolonlar)
    _numerik_ve_bool(df)
    return df


def tuketim_toplama_getir(
    conn: Connection, grain: Grain, baslangic_tarih_id: int, bitis_tarih_id: int
) -> pd.DataFrame:
    """`fact_tuketim` — grup_id kırılımlı (il toplanmış ÜLKE GENELİ)
    toplamlar. Kolonlar: donem_anahtari, grup_id, grup_adi, deger,
    il_sayisi_min, beklenen/mevcut_donem_sayisi, tam_mi.
    `kirilim_bazinda_kapsam=True` — EPDK HER ay TÜM grupları basar, bir
    grubun yokluğu (örn. 2016-12 Tarımsal) KALICI eksikliktir (madde 5)."""
    return _kapsam_ve_deger_df(
        conn,
        tablo_adi="fact_tuketim",
        view_adi="vw_toplama_tuketim_aylik",
        breakdown_kolonlari=("grup_id", "grup_adi"),
        deger_kolonu="tuketim_mwh",
        il_kirilimi_var_mi=True,
        kirilim_bazinda_kapsam=True,
        grain=grain,
        baslangic_tarih_id=baslangic_tarih_id,
        bitis_tarih_id=bitis_tarih_id,
    )


def tuketim_ulke_geneli_toplama_getir(
    conn: Connection, grain: Grain, baslangic_tarih_id: int, bitis_tarih_id: int
) -> pd.DataFrame:
    """`fact_tuketim_ulke_geneli` — grup_id kırılımlı toplamlar (zaten
    ülke geneli, il kırılımı YOK). `kumulatif_tuketim_mwh` view'de hiç
    seçilmediği için burada asla toplanamaz (madde 6)."""
    return _kapsam_ve_deger_df(
        conn,
        tablo_adi="fact_tuketim_ulke_geneli",
        view_adi="vw_toplama_tuketim_ulke_geneli_aylik",
        breakdown_kolonlari=("grup_id", "grup_adi"),
        deger_kolonu="tuketim_mwh",
        il_kirilimi_var_mi=False,
        kirilim_bazinda_kapsam=True,
        grain=grain,
        baslangic_tarih_id=baslangic_tarih_id,
        bitis_tarih_id=bitis_tarih_id,
    )


def uretim_kaynak_toplama_getir(
    conn: Connection, grain: Grain, baslangic_tarih_id: int, bitis_tarih_id: int
) -> pd.DataFrame:
    """`fact_uretim_kaynak_geneli` — kaynak_id × lisans_id kırılımlı
    toplamlar (il kırılımı YOK, zaten ülke geneli). Bir kaynağın belirli
    bir ayda hiç listelenmemesi (örn. Motorin/Nafta) `mevcut_donem_
    sayisi`yi ETKİLEMEZ (madde 7) — yalnız TABLONUN o ay hiç yüklenmemesi
    etkiler."""
    return _kapsam_ve_deger_df(
        conn,
        tablo_adi="fact_uretim_kaynak_geneli",
        view_adi="vw_toplama_uretim_kaynak_aylik",
        breakdown_kolonlari=(
            "kaynak_id",
            "kaynak_adi",
            "yenilenebilir_mi",
            "lisans_id",
            "lisans_turu",
        ),
        deger_kolonu="uretim_mwh",
        il_kirilimi_var_mi=False,
        kirilim_bazinda_kapsam=False,
        grain=grain,
        baslangic_tarih_id=baslangic_tarih_id,
        bitis_tarih_id=bitis_tarih_id,
    )


def uretim_il_toplama_getir(
    conn: Connection, grain: Grain, baslangic_tarih_id: int, bitis_tarih_id: int
) -> pd.DataFrame:
    """`fact_uretim_il_geneli` — lisans_id kırılımlı (il toplanmış ÜLKE
    GENELİ) toplamlar. 202402 gibi "bir taraf eksik" (Bulgu J) dönemler
    tablo-düzeyinde `mevcut_donem_sayisi`yi düşürür, `tam_mi=False`."""
    return _kapsam_ve_deger_df(
        conn,
        tablo_adi="fact_uretim_il_geneli",
        view_adi="vw_toplama_uretim_il_aylik",
        breakdown_kolonlari=("lisans_id", "lisans_turu"),
        deger_kolonu="uretim_mwh",
        il_kirilimi_var_mi=True,
        kirilim_bazinda_kapsam=False,
        grain=grain,
        baslangic_tarih_id=baslangic_tarih_id,
        bitis_tarih_id=bitis_tarih_id,
    )


def uretim_yenilenebilir_payi_getir(
    conn: Connection, grain: Grain, baslangic_tarih_id: int, bitis_tarih_id: int
) -> pd.DataFrame:
    """**ORAN KURALI örneği (madde 4):** yenilenebilir üretim payı = (bucket
    içindeki TÜM ayların yenilenebilir toplamı) / (bucket içindeki TÜM
    ayların TOPLAM üretimi) — ayların kendi yüzdesinin ORTALAMASI DEĞİL.
    Önce iki toplam AYRI AYRI SUM'lanır, oran EN SONDA (tek bölme)
    hesaplanır — bkz. `worker/tests/test_toplama_oran_kurali.py`.
    Kolonlar: donem_anahtari, yenilenebilir_mwh, toplam_mwh, pay,
    beklenen/mevcut_donem_sayisi, tam_mi (`fact_uretim_kaynak_geneli`
    tablo-düzeyi "yüklü ay" sinyaline dayanır, kaynak kırılımından
    bağımsız — madde 5/7 ile TUTARLI)."""
    _grain_dogrula(grain)
    y1, m1, y2, m2 = _tarih_araligina_ayir(baslangic_tarih_id, bitis_tarih_id)
    donem_view = _DONEM_ANAHTARI_VIEW[grain]
    donem_takvim = _DONEM_ANAHTARI_TAKVIM[grain]

    sorgu = f"""
        WITH takvim AS (
            SELECT
                (EXTRACT(year FROM gs)::int) * 100 + EXTRACT(month FROM gs)::int AS tarih_id,
                EXTRACT(year FROM gs)::int AS yil,
                ((EXTRACT(month FROM gs)::int - 1) / 3 + 1)::int AS ceyrek
            FROM generate_series(make_date(%(y1)s, %(m1)s, 1), make_date(%(y2)s, %(m2)s, 1), interval '1 month') AS gs
        ),
        yuklu AS (
            SELECT DISTINCT tarih_id FROM fact_uretim_kaynak_geneli WHERE is_active
        ),
        kapsam AS (
            SELECT {donem_takvim} AS donem_anahtari,
                   COUNT(*) AS beklenen_donem_sayisi,
                   COUNT(y.tarih_id) AS mevcut_donem_sayisi
            FROM takvim t
            LEFT JOIN yuklu y USING (tarih_id)
            GROUP BY {donem_takvim}
        ),
        deger AS (
            SELECT {donem_view} AS donem_anahtari,
                   SUM(uretim_mwh) FILTER (WHERE yenilenebilir_mi) AS yenilenebilir_mwh,
                   SUM(uretim_mwh) AS toplam_mwh
            FROM vw_toplama_uretim_kaynak_aylik
            WHERE tarih_id BETWEEN %(baslangic)s AND %(bitis)s
            GROUP BY {donem_view}
        )
        SELECT d.donem_anahtari,
               COALESCE(d.yenilenebilir_mwh, 0) AS yenilenebilir_mwh,
               d.toplam_mwh,
               CASE WHEN d.toplam_mwh > 0
                    THEN COALESCE(d.yenilenebilir_mwh, 0) / d.toplam_mwh
                    ELSE NULL END AS pay,
               k.beklenen_donem_sayisi, k.mevcut_donem_sayisi,
               (k.beklenen_donem_sayisi = k.mevcut_donem_sayisi) AS tam_mi
        FROM deger d
        JOIN kapsam k ON k.donem_anahtari = d.donem_anahtari
        ORDER BY d.donem_anahtari
    """  # nosec B608 - donem_view/donem_takvim YALNIZ _DONEM_ANAHTARI_*'ten (grain Literal'ine göre sabit), kullanıcı girdisi değil
    with conn.cursor() as cur:
        _jit_kapat(cur)
        cur.execute(
            sorgu,
            {
                "y1": y1,
                "m1": m1,
                "y2": y2,
                "m2": m2,
                "baslangic": baslangic_tarih_id,
                "bitis": bitis_tarih_id,
            },
        )
        satirlar = cur.fetchall()
        kolonlar = [c.name for c in cur.description]  # type: ignore[union-attr]
    df = pd.DataFrame(satirlar, columns=kolonlar)
    for kolon in ("yenilenebilir_mwh", "toplam_mwh", "pay"):
        df[kolon] = pd.to_numeric(df[kolon], errors="coerce")
    df["tam_mi"] = df["tam_mi"].astype(bool)
    return df


def r12_getir(
    conn: Connection, tablo: TabloAdi, baslangic_tarih_id: int, bitis_tarih_id: int
) -> pd.DataFrame:
    """Kayan 12 aylık toplam (R12) — madde 2. TEK seri (TÜM kırılımların
    toplamı — "trend görünümünün asıl aracı"). Her ay noktası, o ayı VE
    önceki 11 ayı kapsar (`RANGE BETWEEN 11 PRECEDING AND CURRENT ROW`,
    ay_index=yil*12+ay üzerinde — ROWS DEĞİL RANGE, çünkü aradaki
    takvim ayları eksikse (gap) ROWS penceresi YANLIŞLIKLA daha eski
    ayları içine çeker; RANGE değer-tabanlı olduğundan gap'i doğru
    algılar). `mevcut_donem_sayisi` TABLO-düzeyi "yüklü ay" sinyaline
    dayanır (madde 5/7 ile TUTARLI) — 12'den azsa `tam_mi=False`.
    `beklenen_donem_sayisi` HER ZAMAN 12 (R12'nin tanımı gereği)."""
    if tablo not in _TABLO_KAYIT:
        raise ValueError(
            f"Bilinmeyen tablo: {tablo!r} (beklenen: {tuple(_TABLO_KAYIT)})"
        )
    tablo_adi, view_adi, deger_kolonu = _TABLO_KAYIT[tablo]
    genis_baslangic = _ay_ekle(baslangic_tarih_id, -11)
    y1, m1, y2, m2 = _tarih_araligina_ayir(genis_baslangic, bitis_tarih_id)

    sorgu = f"""
        WITH takvim AS (
            SELECT
                (EXTRACT(year FROM gs)::int) * 100 + EXTRACT(month FROM gs)::int AS tarih_id,
                (EXTRACT(year FROM gs)::int * 12 + EXTRACT(month FROM gs)::int) AS ay_index
            FROM generate_series(make_date(%(y1)s, %(m1)s, 1), make_date(%(y2)s, %(m2)s, 1), interval '1 month') AS gs
        ),
        yuklu AS (
            SELECT DISTINCT tarih_id FROM {tablo_adi} WHERE is_active
        ),
        kapsam AS (
            SELECT t.tarih_id, t.ay_index,
                   COUNT(y.tarih_id) OVER (
                       ORDER BY t.ay_index RANGE BETWEEN 11 PRECEDING AND CURRENT ROW
                   ) AS mevcut_donem_sayisi
            FROM takvim t
            LEFT JOIN yuklu y USING (tarih_id)
        ),
        deger_aylik AS (
            SELECT tarih_id, (tarih_id / 100 * 12 + MOD(tarih_id, 100)) AS ay_index,
                   SUM({deger_kolonu}) AS deger
            FROM {view_adi}
            WHERE tarih_id BETWEEN %(genis_baslangic)s AND %(bitis)s
            GROUP BY tarih_id
        ),
        deger_r12 AS (
            SELECT tarih_id, ay_index,
                   SUM(deger) OVER (
                       ORDER BY ay_index RANGE BETWEEN 11 PRECEDING AND CURRENT ROW
                   ) AS deger_r12
            FROM deger_aylik
        )
        SELECT k.tarih_id, d.deger_r12,
               12 AS beklenen_donem_sayisi, k.mevcut_donem_sayisi,
               (k.mevcut_donem_sayisi = 12) AS tam_mi
        FROM kapsam k
        JOIN deger_r12 d ON d.tarih_id = k.tarih_id
        WHERE k.tarih_id BETWEEN %(baslangic)s AND %(bitis)s
        ORDER BY k.tarih_id
    """  # nosec B608 - tablo_adi/view_adi YALNIZ _TABLO_KAYIT whitelist'inden
    with conn.cursor() as cur:
        _jit_kapat(cur)
        cur.execute(
            sorgu,
            {
                "y1": y1,
                "m1": m1,
                "y2": y2,
                "m2": m2,
                "genis_baslangic": genis_baslangic,
                "baslangic": baslangic_tarih_id,
                "bitis": bitis_tarih_id,
            },
        )
        satirlar = cur.fetchall()
        kolonlar = [c.name for c in cur.description]  # type: ignore[union-attr]
    df = pd.DataFrame(satirlar, columns=kolonlar)
    df["deger_r12"] = pd.to_numeric(df["deger_r12"], errors="coerce")
    df["tam_mi"] = df["tam_mi"].astype(bool)
    return df


def veri_seti_tarih_araligi_getir(
    conn: Connection, tablo: TabloAdi
) -> tuple[int, int] | None:
    """**2026-09-20 (UI turu) — UI'nin aralık seçicisini (Son 12 ay/Son 3
    yıl/Tümü/Özel) DOĞRU sınırlarla doldurabilmesi için:** `tablo`nun
    `is_active` satırlarının kapsadığı `(min_tarih_id, max_tarih_id)` —
    hiç aktif satır yoksa `None`.

    **Tabloya göre KÖKTEN farklıdır, TEK bir sabit kullanılamaz:**
    `worker/analytics.py:donemler_getir()` yalnız `fact_tuketim`'e bakar
    ve canlıda `fact_tuketim` yalnız 2026-01'den başlar (Excel dönemi) —
    ama `fact_tuketim_ulke_geneli`/`fact_uretim_kaynak_geneli`/`fact_
    uretim_il_geneli` 2016'dan başlar (Word yılları da dahil). UI bu
    fonksiyonu SEÇİLİ veri setine göre çağırmalı — aksi hâlde 3/4 veri
    setinin 'Tümü'/'Özel' aralığı SESSİZCE 2026'ya daralır, kullanıcı
    10 yıllık geçmişe hiç erişemez."""
    if tablo not in _TABLO_KAYIT:
        raise ValueError(
            f"Bilinmeyen tablo: {tablo!r} (beklenen: {tuple(_TABLO_KAYIT)})"
        )
    tablo_adi, _, _ = _TABLO_KAYIT[tablo]
    sorgu = f"SELECT MIN(tarih_id), MAX(tarih_id) FROM {tablo_adi} WHERE is_active"  # nosec B608 - tablo_adi YALNIZ _TABLO_KAYIT whitelist'inden
    with conn.cursor() as cur:
        cur.execute(sorgu)
        row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    return int(row[0]), int(row[1])
