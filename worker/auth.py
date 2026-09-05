"""EPP — Faz B (çok-kullanıcılı giriş): Supabase Auth ile kimlik doğrulama +
rol-farkındalıklı DB bağlantısı açma.

Framework-agnostik (ADR-7'nin ilkesi — bkz. dokumanlar/06_adr_dashboard_
teknoloji.md): Streamlit'e bağımlı hiçbir şey bu dosyada YOK, yalnız
`app/dashboard.py` bu modülü çağırır. Böylece ileride Next.js/FastAPI'ye
geçilirse bu modül DEĞİŞMEDEN kullanılabilir.

İki adımlı akış:
1. `giris_yap()` — Supabase Auth'a (anon key ile, `sign_in_with_password`)
   karşı e-posta/şifre doğrular. Başarılıysa oturumun GERÇEK JWT'sini
   çözüp `app_metadata.role`'ü okur; rol bilinen üçlüden (viewer/
   data_operator/admin) biri DEĞİLSE erişim reddedilir (henüz rol
   atanmamış bir hesap = erişimsiz, sessizce 'viewer' varsayılmaz).
2. `rol_baglantisi_ac()` — `DATABASE_URL_DASHBOARD` (app_dashboard_
   service, dokumanlar/06'da kurulan dar-yetkili rol) ile YENİ bir
   bağlantı açar, o bağlantıda GERÇEK JWT claim'lerini `request.jwt.
   claims` GUC'una yazar ve `SET ROLE <rol>` yapar — `current_app_role()`
   (SECURITY DEFINER, dokumanlar/06) ve RLS politikaları bu ikisine göre
   çalışır. `rol` parametresi HER ZAMAN sabit bir whitelist'e karşı
   doğrulanır (SQL injection'a karşı savunma — ayrıca `psycopg.sql.
   Identifier`/`Literal` kullanılır, ham string birleştirme YOK).

Yeni kullanıcı eklemek (bu modülün kapsamı DIŞINDA — Supabase Admin API,
`auth.admin.create_user()`, tek seferlik bir işlemdir, bkz. dokumanlar/
06_adr_dashboard_teknoloji.md "Faz B — yeni kullanıcı ekleme" bölümü).
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass

import psycopg
from psycopg import sql

from worker.db import create_supabase_client, get_dashboard_database_url

# Fiziksel PostgreSQL rolleriyle BİREBİR eşleşen whitelist (dokumanlar/
# 06_adr_dashboard_teknoloji.md, migration 20260819_0002/0016) — bu
# kümenin DIŞINDA hiçbir değer SET ROLE'e asla ulaşmaz.
GECERLI_ROLLER = frozenset({"viewer", "data_operator", "admin"})

# Aşama 2 (2026-09-05, dokumanlar/06_adr_dashboard_teknoloji.md) — login
# rate-limiting. Supabase Auth'un KENDİ rate-limit'i (resmi dokümantasyonu
# doğrudan kontrol edildi, varsayılmadı) sign-in-with-password için ayrı/
# dokümante edilmiş bir deneme sınırı SAĞLAMIYOR (yalnız OTP/anonim-giriş/
# e-posta gönderimi için var) — panel açık internette (Streamlit Community
# Cloud) barındırıldığından bu proje kendi başarısız-deneme sayacını
# uyguluyor. Süreç-içi (in-memory) — DB migration'ı GEREKTİRMEZ; Streamlit
# Community Cloud bir uygulamayı TEK süreçte çalıştırdığından bu, tüm
# oturumlar arasında paylaşılan tutarlı bir sayaç sağlar (süreç yeniden
# başlarsa/redeploy olursa sıfırlanır — kabul edilebilir, esas tehdit
# modeli tek bir çalışan sürecin ömrü boyunca art arda deneme).
_RATE_LIMIT_MAX_DENEME = 5
_RATE_LIMIT_PENCERE_SN = 15 * 60  # 15 dakika
_basarisiz_denemeler: dict[str, list[float]] = {}


class GirisKilitli(Exception):
    """`_RATE_LIMIT_MAX_DENEME` başarısız denemeden sonra `_RATE_LIMIT_
    PENCERE_SN` boyunca aynı e-posta için giriş engellenir. Bu, hesabın
    var olup olmadığını SIZDIRMAZ — sayaç e-postanın KENDİSİNE (var olsun
    olmasın) bağlıdır, gerçek/sahte hesap için AYNI şekilde tetiklenir."""

    def __init__(self, kalan_sn: float) -> None:
        self.kalan_sn = kalan_sn
        super().__init__(f"Çok fazla başarısız deneme, {kalan_sn:.0f} sn kilitli.")


def _rate_limit_kontrol_et(email_anahtari: str) -> None:
    """Pencere dışına düşen eski denemeleri temizler; sınır aşıldıysa
    `GirisKilitli` fırlatır (Supabase'e HİÇ istek atmadan — hem gereksiz
    dış çağrıyı önler hem Supabase'in kendi rate-limit'ini gereksiz
    tüketmez)."""
    simdi = time.monotonic()
    denemeler = _basarisiz_denemeler.get(email_anahtari, [])
    denemeler = [t for t in denemeler if simdi - t < _RATE_LIMIT_PENCERE_SN]
    _basarisiz_denemeler[email_anahtari] = denemeler
    if len(denemeler) >= _RATE_LIMIT_MAX_DENEME:
        kalan_sn = _RATE_LIMIT_PENCERE_SN - (simdi - denemeler[0])
        raise GirisKilitli(kalan_sn)


def _basarisiz_deneme_kaydet(email_anahtari: str) -> None:
    _basarisiz_denemeler.setdefault(email_anahtari, []).append(time.monotonic())


def _basarili_giriste_sifirla(email_anahtari: str) -> None:
    _basarisiz_denemeler.pop(email_anahtari, None)


@dataclass(frozen=True)
class AuthSonucu:
    """`giris_yap()`'ın başarılı bir girişte döndürdüğü sonuç."""

    jwt_claims_json: str
    rol: str
    kullanici_email: str


def _jwt_payload_coz(access_token: str) -> dict:
    """Bir JWT'nin (imza doğrulaması YAPMADAN — bu belirteç zaten Supabase
    Auth'un kendisinden, `sign_in_with_password()` başarıyla döndüğü için
    güvenilir; yalnız payload'ı OKUMAK için) orta segmentini (payload)
    çözer."""
    govde = access_token.split(".")[1]
    dolgu = "=" * (-len(govde) % 4)
    return json.loads(base64.urlsafe_b64decode(govde + dolgu))


def giris_yap(email: str, sifre: str) -> AuthSonucu | None:
    """Supabase Auth'a karşı e-posta/şifre doğrular. Başarısızsa (yanlış
    şifre, var olmayan hesap, VEYA hesap var ama `app_metadata.role`
    bilinen üçlüden biri DEĞİLSE) `None` döner — çağıran (app/dashboard.py)
    "e-posta veya şifre hatalı" gibi GENEL bir mesaj göstermeli, hangi
    durumun gerçekleştiğini (hesap yok / şifre yanlış / rol atanmamış)
    kullanıcıya SIZDIRMAMALI.

    5 başarısız denemeden sonra AYNI e-posta için 15 dk `GirisKilitli`
    fırlatılır (Aşama 2 rate-limiting — bkz. modül başındaki not).
    E-posta anahtarı normalize edilir (`strip().lower()`) — büyük/küçük
    harf veya baştaki/sondaki boşlukla sayaç bypass edilemez."""
    email_anahtari = email.strip().lower()
    _rate_limit_kontrol_et(email_anahtari)

    client = create_supabase_client()
    if client is None:
        return None

    from supabase_auth.errors import AuthApiError

    try:
        yanit = client.auth.sign_in_with_password({"email": email, "password": sifre})
    except AuthApiError:
        _basarisiz_deneme_kaydet(email_anahtari)
        return None

    if yanit.session is None or yanit.user is None:
        _basarisiz_deneme_kaydet(email_anahtari)
        return None

    # Kimlik bilgileri (Supabase'e göre) DOĞRU — rol whitelist dışı olsa
    # bile bu bir kaba-kuvvet/tahmin denemesi DEĞİL, sayaç sıfırlanır.
    _basarili_giriste_sifirla(email_anahtari)

    claims = _jwt_payload_coz(yanit.session.access_token)
    rol = (claims.get("app_metadata") or {}).get("role")
    if rol not in GECERLI_ROLLER:
        return None

    return AuthSonucu(
        jwt_claims_json=json.dumps(claims),
        rol=rol,
        kullanici_email=yanit.user.email or email,
    )


def rol_baglantisi_ac(jwt_claims_json: str, rol: str) -> psycopg.Connection:
    """`DATABASE_URL_DASHBOARD` (app_dashboard_service) ile YENİ bir
    bağlantı açar, `request.jwt.claims`'i gerçek oturumun JWT'siyle set
    eder ve `SET ROLE <rol>` yapar. Çağıran bu bağlantıyı `st.session_
    state`'e koymalı (oturum başına AYRI bağlantı — dokumanlar/06'daki
    paylaşımlı-bağlantı bulgusu, bkz. app/dashboard.py modül notu).

    `rol` KESİNLİKLE `GECERLI_ROLLER` whitelist'inde olmalı — değilse
    `SET ROLE`'e hiç ulaşmadan `ValueError` fırlatılır. Whitelist kontrolü
    YETERLİ olsa da, ayrıca `psycopg.sql.Identifier`/`Literal` kullanılır
    (savunma derinliği — ham f-string/`%`-birleştirme ile SQL metni
    ASLA kurulmaz)."""
    if rol not in GECERLI_ROLLER:
        raise ValueError(
            f"Whitelist dışı rol: {rol!r} — yalnız {sorted(GECERLI_ROLLER)} kabul edilir."
        )

    database_url = get_dashboard_database_url()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL_DASHBOARD tanımlı değil — .env kontrol et "
            "(dokumanlar/06_adr_dashboard_teknoloji.md)."
        )

    conn = psycopg.connect(database_url, prepare_threshold=None)
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SET request.jwt.claims = {}").format(
                    sql.Literal(jwt_claims_json)
                )
            )
            cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(rol)))
        conn.commit()
    except Exception:
        conn.close()
        raise
    return conn
