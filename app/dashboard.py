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

Bağlantı yönetimi: bağlantı OTURUM BAŞINA (`st.session_state`) açılır ve
o oturum boyunca yeniden kullanılır — Streamlit her etkileşimde script'i
baştan çalıştırır; session_state olmasaydı her tıklamada yeni bir DB
bağlantısı açılırdı. Sorgu sonuçları @st.cache_data ile cache'lenir;
bağlantı parametresi `_conn` adıyla geçirilir çünkü Streamlit alttan
çizgiyle (_) başlayan parametreleri HASH'LEMEZ — psycopg Connection
nesnesi hash'lenemeyeceğinden bu isimlendirme zorunludur (adı `conn`
olsaydı cache ya patlar ya sessizce devre dışı kalırdı).

**2026-09-05, tüm @st.cache_data'lara `ttl=1800` (30 dk) eklendi:**
önceden TTL yoktu — yeni veri (örn. yeni bir batch aktive edilince)
görünmesi için Streamlit Cloud'da elle "Reboot app" gerekiyordu
(süreç tazelenmeden cache asla düşmüyordu). 30 dk, "aşırı sık yeniden
sorgulama" ile "saatlerce bayat kalma" arasında bir denge — bu veri
en fazla günde birkaç kez (yeni ay aktivasyonu) değişiyor, agresif bir
TTL gerekmiyor. `_statik_veri_hazirla()` (yerel dosya, DB değil)
BİLİNÇLİ OLARAK TTL'siz bırakıldı — çalışma süresince hiç değişmiyor.

**2026-09-05, KRİTİK değişiklik — `@st.cache_resource`'tan `st.session_state`'e
geçildi:** `@st.cache_resource` PARAMETRESİZDİ, yani TÜM Streamlit
kullanıcıları/sekmeleri TEK bir paylaşımlı psycopg bağlantısını
KULLANIYORDU. Bu, kullanıcı bazlı `SET ROLE` (Faz B, dokumanlar/
06_adr_dashboard_teknoloji.md) eklendiğinde KRİTİK bir sorun olurdu:
Kullanıcı A `SET ROLE viewer` yaptığı anda Kullanıcı B'nin isteği AYNI
bağlantı/rol durumunu görebilirdi (Supavisor'ın transaction-mode
pooler'ının SET ROLE'ü NEDEN kısıtladığının BİREBİR AYNI sınıf sorunu,
şimdi uygulama katmanında tekrarlanmış olurdu). `st.session_state` HER
Streamlit OTURUMUNA kendi bağlantısını verir — bağlantılar artık
paylaşılmıyor.

**Performans/bağlantı-sayısı notu (bilinçli bir ödünleşim):** her sekme/
oturum artık KENDİ Postgres bağlantısını açıyor — önceden tek bir
paylaşımlı bağlantı vardı. Supabase'in (plana göre değişen) eşzamanlı
bağlantı limiti var; çok sayıda eşzamanlı oturum bu limiti
zorlayabilir — Supavisor pooler (bkz. `DATABASE_URL`'in pooler host'u)
bunu bir ölçüde yumuşatır (bağlantı havuzlama), ama session-mode/direkt
bağlantılar (`DATABASE_URL_DASHBOARD`, aşağıya bkz.) havuzlanmadığından
her oturum GERÇEKTEN ayrı bir sunucu bağlantısı tüketir — çok kullanıcılı
gerçek trafikte bu izlenmeli.

**2026-09-05, Faz B SON ADIM — gerçek giriş ekranı + `SET ROLE` bağlandı:**
`DATABASE_URL_DASHBOARD` (.env, `app_dashboard_service` rolü — bkz.
dokumanlar/06_adr_dashboard_teknoloji.md) yapılandırılmışsa panel artık
ZORUNLU bir giriş ekranı gösterir (`worker.auth.giris_yap()` → Supabase
Auth). Başarılı girişte `worker.auth.rol_baglantisi_ac()` GERÇEK JWT
claim'lerini (`app_metadata.role`) taşıyan, `SET ROLE` yapılmış YENİ bir
bağlantı açar ve `session_state`'e koyar — eski, girişsiz `DATABASE_URL`
yolu (paylaşılabilir/salt-okunur) YALNIZ `DATABASE_URL_DASHBOARD` hiç
yapılandırılmamışsa (yerel/offline geliştirme) devrede kalır.
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
from worker.auth import giris_yap, rol_baglantisi_ac
from worker.db import get_dashboard_database_url, resolve_database_or_fallback

st.set_page_config(
    page_title="EPP — Türkiye Elektrik Piyasası", layout="wide", page_icon="⚡"
)


def _cikis_yap() -> None:
    """Oturumu tamamen temizler (açık bağlantıyı kapatır + session_state'i
    sıfırlar) ve sayfayı yeniden başlatır — sidebar'daki "Çıkış Yap"
    butonundan çağrılır."""
    baglanti = st.session_state.get("db_handle")
    if baglanti is not None and hasattr(baglanti, "close"):
        try:
            baglanti.close()
        except Exception:  # noqa: BLE001, S110 - çıkışta kapatma hatası kullanıcıyı engellememeli
            pass
    for anahtar in ("db_handle", "db_source", "kullanici_email", "kullanici_rolu"):
        st.session_state.pop(anahtar, None)
    st.rerun()


def _giris_ekrani_goster() -> None:
    """E-posta/şifre formu — worker.auth.giris_yap()'a devreder. Başarısız
    girişte "e-posta veya şifre hatalı" gibi GENEL bir mesaj gösterilir,
    hesabın var olup olmadığı SIZDIRILMAZ (bkz. worker/auth.py modül notu).
    Başarılı girişte worker.auth.rol_baglantisi_ac() ile rol-farkındalıklı
    bağlantı açılır ve session_state'e konur. `st.stop()` ile çağrıldığı
    yerden SONRASI (asıl dashboard içeriği) render EDİLMEZ — giriş
    ekranı gösterildiği/yeniden denendiği sürece kullanıcı veriye hiç
    erişemez."""
    st.title("⚡ EPP — Türkiye Elektrik Piyasası Paneli")
    st.subheader("Giriş")
    with st.form("giris_formu"):
        email = st.text_input("E-posta")
        sifre = st.text_input("Şifre", type="password")
        gonderildi = st.form_submit_button("Giriş Yap")
    if gonderildi:
        sonuc = giris_yap(email, sifre)
        if sonuc is None:
            st.error("E-posta veya şifre hatalı.")
        else:
            try:
                baglanti = rol_baglantisi_ac(sonuc.jwt_claims_json, sonuc.rol)
            except Exception as e:  # noqa: BLE001 - kullanıcıya net bir hata göstermek için
                st.error(f"Giriş başarılı ama bağlantı açılamadı: {e}")
            else:
                st.session_state.db_handle = baglanti
                st.session_state.db_source = "PostgreSQL via DATABASE_URL_DASHBOARD"
                st.session_state.kullanici_email = sonuc.kullanici_email
                st.session_state.kullanici_rolu = sonuc.rol
                st.rerun()
    st.stop()


def _baglanti_al() -> tuple[Any | None, str]:
    """Bağlantıyı OTURUM BAŞINA açar (bkz. modül notu — 2026-09-05, `@st.
    cache_resource`'un paylaşımlı-bağlantı riskinden kaçınmak için
    `st.session_state`'e geçildi).

    **2026-09-05, Faz B son adım — giriş ZORUNLU hale geldi:**
    `DATABASE_URL_DASHBOARD` (.env'de) YAPILANDIRILMIŞSA panel HER ZAMAN
    kimlik doğrulaması ister — eski "girişsiz DATABASE_URL ile doğrudan
    gerçek veri" yolu artık KULLANILMAZ (yoksa giriş ekranı dekoratif
    kalır, gerçek erişim kontrolü sağlamaz). `DATABASE_URL_DASHBOARD`
    HİÇ yapılandırılmamışsa (yerel/offline geliştirme — Faz B kurulmamış
    bir ortam) eski davranış (`resolve_database_or_fallback()`: varsa
    `DATABASE_URL`, yoksa anon-key Supabase istemcisi, o da yoksa statik
    dosya verisi) AYNEN korunur — bu durumda giriş ekranı da HİÇ
    gösterilmez (zaten gerçek veri yok, kimlik doğrulayacak bir şey yok)."""
    if get_dashboard_database_url():
        if "db_handle" not in st.session_state:
            _giris_ekrani_goster()  # gönderilmediyse/başarısızsa st.stop() ile burada durur
        return st.session_state.db_handle, st.session_state.db_source

    if "db_handle" not in st.session_state:
        st.session_state.db_handle, st.session_state.db_source = (
            resolve_database_or_fallback()
        )
    return st.session_state.db_handle, st.session_state.db_source


db_handle, db_source = _baglanti_al()
# İkisi de gerçek sorguyu destekler: eski (girişsiz) DATABASE_URL yolu VE
# yeni (girişli) DATABASE_URL_DASHBOARD yolu - bkz. modül notu.
gercek_veri_var = db_handle is not None and db_source in (
    "PostgreSQL via DATABASE_URL",
    "PostgreSQL via DATABASE_URL_DASHBOARD",
)

if "kullanici_email" in st.session_state:
    with st.sidebar:
        st.caption(
            f"👤 {st.session_state.kullanici_email} ({st.session_state.kullanici_rolu})"
        )
        if st.button("Çıkış Yap", use_container_width=True):
            _cikis_yap()
        st.divider()

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

if st.session_state.get("kullanici_rolu") == "data_operator":
    # data_operator RLS'te yalnız INSERT/UPDATE politikalarına sahip (bkz.
    # supabase/migrations/20260819_0002_rls_roles.sql) — SELECT politikası
    # YOK, bu yüzden aşağıdaki KPI sorguları bu rol için sessizce 0 satır
    # dönerdi (boş/bozuk görünen bir ekran). Veri girişi UI'ı henüz
    # yapılmadı (dokumanlar/06_adr_dashboard_teknoloji.md, "Faz B sonrası"
    # kararı) — kafa karıştırıcı boş ekran yerine AÇIK bir bilgi mesajı
    # gösterip burada dur.
    st.info(
        "Bu rol (data_operator) için henüz bir veri girişi ekranı yok. "
        "Veri yükleme işlemleri şimdilik `worker/jobs/` altındaki "
        "script'lerle yapılıyor."
    )
    st.stop()


# ---------------- Önbellekli sorgu sarmalayıcıları (DB modu) ----------------
# _conn: bkz. modül notu - Streamlit alttan çizgili parametreleri hash'lemez.


@st.cache_data(show_spinner="Dönemler yükleniyor...", ttl=1800)
def _donemler_getir_cached(_conn: Any) -> pd.DataFrame:
    return analytics.donemler_getir(_conn)


@st.cache_data(show_spinner="İller yükleniyor...", ttl=1800)
def _iller_getir_cached(_conn: Any) -> pd.DataFrame:
    return analytics.iller_getir(_conn)


@st.cache_data(show_spinner="Üretim verisi yükleniyor...", ttl=1800)
def _uretim_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.uretim_getir(_conn, tarih_id)


@st.cache_data(show_spinner="Tüketim verisi yükleniyor...", ttl=1800)
def _tuketim_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.tuketim_getir(_conn, tarih_id)


@st.cache_data(show_spinner="Abone verisi yükleniyor...", ttl=1800)
def _abone_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.abone_getir(_conn, tarih_id)


@st.cache_data(show_spinner="Serbest tüketici verisi yükleniyor...", ttl=1800)
def _serbest_tuketici_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.serbest_tuketici_getir(_conn, tarih_id)


@st.cache_data(show_spinner="Hava verisi yükleniyor...", ttl=1800)
def _hava_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.hava_getir(_conn, tarih_id)


@st.cache_data(show_spinner=False, ttl=1800)
def _sistem_parametre_getir_cached(_conn: Any) -> dict[str, float]:
    return analytics.sistem_parametre_getir(_conn)


@st.cache_data(show_spinner=False, ttl=1800)
def _kapsam_disi_getir_cached(_conn: Any, tarih_id: int) -> pd.DataFrame:
    return analytics.kapsam_disi_getir(_conn, tarih_id)


@st.cache_data(show_spinner=False, ttl=300)
def _son_batchler_getir_cached(_conn: Any) -> pd.DataFrame:
    return analytics.son_batchler_getir(_conn)


@st.cache_data(show_spinner=False, ttl=300)
def _son_job_durumlari_getir_cached(_conn: Any) -> pd.DataFrame:
    return analytics.son_job_durumlari_getir(_conn)


@st.cache_data(
    show_spinner="Hava normalizasyonu (KPI-11/12, Türkiye Geneli) hesaplanıyor...",
    ttl=1800,
)
def _kpi_11_12_ulusal_hesapla_cached(
    _conn: Any, tarih_id: int, hava_norm_yil: int, tuketim_norm_yil: int
) -> dict[str, float | int | None]:
    return analytics.kpi_11_12_ulusal_hesapla(
        _conn, tarih_id, hava_norm_yil=hava_norm_yil, tuketim_norm_yil=tuketim_norm_yil
    )


@st.cache_data(show_spinner="Hava normalizasyonu (KPI-11/12) hesaplanıyor...", ttl=1800)
def _kpi_11_12_hesapla_cached(
    _conn: Any, il_kodu: int, tarih_id: int, hava_norm_yil: int, tuketim_norm_yil: int
) -> dict[str, float | None]:
    return analytics.kpi_11_12_hesapla(
        _conn,
        il_kodu,
        tarih_id,
        hava_norm_yil=hava_norm_yil,
        tuketim_norm_yil=tuketim_norm_yil,
    )


@st.cache_data(show_spinner="Yıllık tüketim serisi yükleniyor...", ttl=1800)
def _yillik_tuketim_serisi_cached(_conn: Any) -> pd.DataFrame:
    return analytics.yillik_tuketim_serisi_getir(_conn)


@st.cache_data(show_spinner="Yıllık kurulu güç serisi yükleniyor...", ttl=1800)
def _yillik_yenilenebilir_kurulu_guc_serisi_cached(_conn: Any) -> pd.DataFrame:
    return analytics.yillik_yenilenebilir_kurulu_guc_serisi_getir(_conn)


@st.cache_data(show_spinner="Sanayi-hariç tüketim serisi yükleniyor...", ttl=1800)
def _yillik_tuketim_sanayi_haric_serisi_cached(_conn: Any) -> pd.DataFrame:
    return analytics.yillik_tuketim_sanayi_haric_serisi_getir(_conn)


@st.cache_data(show_spinner=False, ttl=1800)
def _kpi_esikleri_getir_cached(_conn: Any) -> dict[str, dict[str, float | str]]:
    return analytics.kpi_esikleri_getir(_conn)


_RENK_EMOJI = {"yesil": "🟢", "sari": "🟡", "kirmizi": "🔴"}


def _trafik_isigi(
    deger: float | None, kpi_id: str, esikler: dict[str, dict[str, float | str]]
) -> str:
    """Görev 3 (2026-09-05): `kpi_esik`'te tanımlı bir KPI için trafik ışığı
    emoji'si döndürür, tanımlı değilse ya da değer 'hesaplanamaz'/'veri yok'
    ise boş string (kart eskisi gibi renksiz kalır — kod YOKSA sahte bir
    renk üretilmez, worker/kpi.py:esik_rengi() ile aynı ilke)."""
    esik = esikler.get(kpi_id)
    if esik is None or deger is None:
        return ""
    renk = kpi.esik_rengi(
        deger, float(esik["yesil_alt"]), float(esik["sari_alt"]), str(esik["yon"])
    )
    return f"{_RENK_EMOJI.get(renk, '')} " if renk else ""


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
    kapsam_disi = _kapsam_disi_getir_cached(db_handle, secili_tarih_id)
    esikler = _kpi_esikleri_getir_cached(db_handle)

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

    # OD-1: baz sıcaklıklar sistem_parametre'den (koda gömülmez).
    _sp = _sistem_parametre_getir_cached(db_handle)
    hdd_baz_c = _sp.get("hdd_baz_c", 18.0)
    cdd_baz_c = _sp.get("cdd_baz_c", 22.0)
    hava_norm_yil = int(_sp.get("hava_norm_yil", 10))
    tuketim_norm_yil = int(_sp.get("tuketim_norm_yil", 5))
else:
    tuketim, uretim, abone, serbest, hava = _statik_veri_hazirla()
    onceki_tuketim = pd.DataFrame(columns=tuketim.columns)
    iller = ["Türkiye Geneli"] + sorted(tuketim["il"].dropna().unique().tolist())
    donem_etiketi = "2026-01 (yerel dosya)"
    donem_saat = ingest.donem_saat_sayisi(202601)
    # statik yedekte sistem_parametre'ye erişim yok - migration 20260819_0004
    # seed değerleriyle aynı (Faz 2 dashboard notunda da böyleydi).
    hdd_baz_c, cdd_baz_c, hava_norm_yil, tuketim_norm_yil = 18.0, 22.0, 10, 5
    kapsam_disi = pd.DataFrame(columns=["fact_tablosu", "nitelik", "sebep"])
    esikler = {}
    with st.sidebar:
        st.header("Dönem")
        st.selectbox("Ay/Yıl", [donem_etiketi], disabled=True)

# ---------------- BAŞLIK ----------------
st.title("⚡ Türkiye Elektrik Piyasası Paneli")
st.caption(f"EPDK Elektrik Piyasası Sektör Raporu — {donem_etiketi} · 81 İl")

# Aşama 7 (dokumanlar/06_canli_veri_operasyon_gunlugu.md): seçili dönem
# için veri_kapsam_disi'de işaretli bir kayıt varsa (T13/T1/T4-Temmuz2022
# gibi "kaynakta yok" durumları), ilgili KPI kartlarının boş/"veri yok"
# görünmesi kullanıcıya AÇIKLAMASIZ kalmasın diye burada tek bir bilgi
# kutusunda özetlenir — sahte bir eksiklik izlenimi vermemek için.
if not kapsam_disi.empty:
    satirlar = [
        f"**{r.fact_tablosu}**"
        + (f" ({r.nitelik})" if r.nitelik != "(tumu)" else "")
        + f" — {r.sebep}"
        for r in kapsam_disi.itertuples()
    ]
    st.info(
        "ℹ️ Bu dönem için kaynakta mevcut olmayan veriler:\n\n"
        + "\n\n".join(f"- {s}" for s in satirlar)
    )

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

# KPI-11/12 (hava normalizasyonu) il bazlı çalışır (Türkiye ölçeğinde tek bir
# β/γ anlamlı değil — iklim bölgeye göre çok değişir) - yalnız DB modunda VE
# belirli bir İl seçiliyken hesaplanabilir.
secili_il_kodu: int | None = None
if gercek_veri_var and secili_il != "Türkiye Geneli":
    eslesen = il_listesi.loc[il_listesi["il_adi"] == secili_il, "il_kodu"]
    if not eslesen.empty:
        secili_il_kodu = int(eslesen.iloc[0])

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
    "Kaynak Yoğunlaşması (KPI-06 HHI)",
    f"{_trafik_isigi(hhi, 'KPI-06', esikler)}{hhi:.3f}"
    if hhi is not None
    else "veri yok",
)

lisanssiz_pay = kpi.kpi_07_lisanssiz_pay(uretim) if lisans_var else None
u6.metric(
    "Lisanssız Üretim Payı (KPI-07)",
    f"%{lisanssiz_pay:.1f}" if lisanssiz_pay is not None else "veri yok",
)

# 2026-09-03: kpi_13_yoy() artık ÖZET rakam değil, DataFrame'lerin kendisini
# alıyor — iki dönemin grup kümesi uyuşmuyorsa (örn. Sanayi biri içeriyor
# diğeri içermiyorsa) None döner (bkz. worker/kpi.py modül notu, KPI-25/26
# ile AYNI "kapsam uyuşmuyorsa hesaplama" disiplini).
yoy = kpi.kpi_13_yoy(tuketim, onceki_tuketim if not onceki_tuketim.empty else None)
u7.metric(
    "Tüketim YoY (KPI-13)",
    f"{_trafik_isigi(yoy, 'KPI-13', esikler)}%{yoy:+.1f}"
    if yoy is not None
    else "hesaplanamaz",
)

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

# ---------------- KPI KARTLARI — HAVA NORMALİZASYONU (Faz 3) ----------------
st.subheader("Hava")
h1, h2, h3, h4 = st.columns(4)
if not hava.empty:
    h1.metric(
        "Isıtma Derece Gün (KPI-23 HDD)",
        f"{kpi.kpi_23_hdd(hava, hdd_baz_c=hdd_baz_c):,.0f}",
    )
    h2.metric(
        "Soğutma Derece Gün (KPI-24 CDD)",
        f"{kpi.kpi_24_cdd(hava, cdd_baz_c=cdd_baz_c):,.0f}",
    )
else:
    h1.metric("Isıtma Derece Gün (KPI-23 HDD)", "veri yok")
    h2.metric("Soğutma Derece Gün (KPI-24 CDD)", "veri yok")

if secili_il_kodu is not None:
    kpi_11_12 = _kpi_11_12_hesapla_cached(
        db_handle, secili_il_kodu, secili_tarih_id, hava_norm_yil, tuketim_norm_yil
    )
    h3.metric(
        "Arındırılmış Tüketim (KPI-11)",
        f"{kpi_11_12['arindirilmis']:,.0f} MWh"
        if kpi_11_12["arindirilmis"] is not None
        else "hesaplanamaz",
    )
    _kpi_12_deger = kpi_11_12["kpi_12"]
    # yön=alcelik SAPMANIN BÜYÜKLÜĞÜNE bakar, işaretine değil (bkz. worker/
    # kpi.py:esik_rengi() sözleşmesi) — bu yüzden abs() geçiriliyor.
    _kpi_12_abs = abs(_kpi_12_deger) if _kpi_12_deger is not None else None
    h4.metric(
        "Norm Sapması (KPI-12)",
        f"{_trafik_isigi(_kpi_12_abs, 'KPI-12', esikler)}%{_kpi_12_deger:+.1f}"
        if _kpi_12_deger is not None
        else "hesaplanamaz",
    )
elif gercek_veri_var:
    # Görev 4 (2026-09-05, Seçenek A — dokumanlar/06_canli_veri_operasyon_
    # gunlugu.md): "Türkiye Geneli" artık 81 ilin KENDİ regresyonlarının
    # toplamıyla hesaplanıyor, ayrı bir "ulusal HDD/CDD" uydurulmuyor.
    kpi_11_12_ulusal = _kpi_11_12_ulusal_hesapla_cached(
        db_handle, secili_tarih_id, hava_norm_yil, tuketim_norm_yil
    )
    h3.metric(
        "Arındırılmış Tüketim (KPI-11, Türkiye Geneli)",
        f"{kpi_11_12_ulusal['arindirilmis']:,.0f} MWh"
        if kpi_11_12_ulusal["arindirilmis"] is not None
        else "hesaplanamaz",
    )
    _kpi_12_ulusal_deger = kpi_11_12_ulusal["kpi_12"]
    _kpi_12_ulusal_abs = (
        abs(_kpi_12_ulusal_deger) if _kpi_12_ulusal_deger is not None else None
    )
    h4.metric(
        "Norm Sapması (KPI-12, Türkiye Geneli)",
        f"{_trafik_isigi(_kpi_12_ulusal_abs, 'KPI-12', esikler)}%{_kpi_12_ulusal_deger:+.1f}"
        if _kpi_12_ulusal_deger is not None
        else "hesaplanamaz",
    )
    if kpi_11_12_ulusal["kapsam_il_sayisi"]:
        st.caption(
            f"81 ilin {kpi_11_12_ulusal['kapsam_il_sayisi']}'i yeterli geçmişe "
            "sahip olduğu için ulusal toplama dahil edildi (Görev 4, Seçenek A "
            "— her il kendi β/γ regresyonuyla hesaplanıp toplanır, tek bir "
            "'ulusal HDD/CDD' uydurulmaz)."
        )
else:
    h3.metric("Arındırılmış Tüketim (KPI-11)", "hesaplanamaz")
    h4.metric("Norm Sapması (KPI-12)", "hesaplanamaz")

st.divider()

# ---------------- KPI KARTLARI — YILLIK TRENDLER (CAGR) ----------------
st.subheader("Yıllık Trendler")
y1, y2, y3 = st.columns(3)
if gercek_veri_var:
    tuketim_serisi = _yillik_tuketim_serisi_cached(db_handle)
    kpi_25 = analytics.cagr_seriden_hesapla(tuketim_serisi, "tuketim_mwh")
    kurulu_serisi = _yillik_yenilenebilir_kurulu_guc_serisi_cached(db_handle)
    kpi_26 = analytics.cagr_seriden_hesapla(kurulu_serisi, "kurulu_guc_mw")
    tuketim_sanayi_haric_serisi = _yillik_tuketim_sanayi_haric_serisi_cached(db_handle)
    kpi_27 = analytics.cagr_seriden_hesapla(tuketim_sanayi_haric_serisi, "tuketim_mwh")
else:
    kpi_25 = None
    kpi_26 = None
    kpi_27 = None
y1.metric(
    "Tüketim CAGR (KPI-25)",
    f"{_trafik_isigi(kpi_25, 'KPI-25', esikler)}%{kpi_25:+.1f}"
    if kpi_25 is not None
    else "hesaplanamaz",
)
y2.metric(
    "Yenilenebilir Kurulu Güç CAGR (KPI-26)",
    f"{_trafik_isigi(kpi_26, 'KPI-26', esikler)}%{kpi_26:+.1f}"
    if kpi_26 is not None
    else "hesaplanamaz",
)
y3.metric(
    "Sanayi-Hariç Tüketim CAGR (KPI-27)",
    f"{_trafik_isigi(kpi_27, 'KPI-27', esikler)}%{kpi_27:+.1f}"
    if kpi_27 is not None
    else "hesaplanamaz",
)
if gercek_veri_var and (kpi_25 is None or kpi_26 is None or kpi_27 is None):
    st.caption(
        "CAGR için en az iki farklı yıla ait aktif veri gerekir — henüz "
        "yeterli geçmiş (backfill) yüklenmemiş olabilir."
    )
st.caption(
    "KPI-27, Sanayi grubunu TÜM yıllardan çıkararak hesaplanır — KPI-25'in "
    "(resmi toplam tüketim) YERİNE GEÇMEZ, yalnız ek bağlam sağlar "
    "(dokumanlar/04_kpi_sozlesmeleri.md)."
)

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

# ---------------- SİSTEM DURUMU ----------------
# Yalnız gerçek DB modunda anlamlı (ingestion_batch/job_status statik
# yedekte hiç yok). Diğer önbelleklerden (ttl=1800) FARKLI olarak burada
# ttl=300 (5 dk) kullanılıyor — bu, "az önce yüklenen bir batch'in durumu
# ne oldu" gibi operasyonel bir izleme amacı taşıyor, KPI kartlarının
# aksine daha taze kalması bekleniyor.
if gercek_veri_var:
    st.divider()
    with st.expander("🔧 Sistem Durumu (son batch'ler + iş kuyruğu)"):
        st.caption("Son 20 ingestion_batch")
        batchler = _son_batchler_getir_cached(db_handle)
        if batchler.empty:
            st.caption("Hiç batch bulunamadı.")
        else:
            st.dataframe(batchler, width="stretch", hide_index=True)

        st.caption("Son 20 job_status (Faz 1 asenkron kuyruk)")
        joblar = _son_job_durumlari_getir_cached(db_handle)
        if joblar.empty:
            st.caption(
                "Hiç iş kaydı bulunamadı (Faz 1 kuyruğu bu ortamda hiç kullanılmamış olabilir)."
            )
        else:
            st.dataframe(joblar, width="stretch", hide_index=True)

st.caption("EPP — EPDK Elektrik Piyasası Veri & Dashboard Platformu · Faz 2")
