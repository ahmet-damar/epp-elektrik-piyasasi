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
from dataclasses import dataclass

import psycopg
from psycopg import sql

from worker.db import create_supabase_client, get_dashboard_database_url

# Fiziksel PostgreSQL rolleriyle BİREBİR eşleşen whitelist (dokumanlar/
# 06_adr_dashboard_teknoloji.md, migration 20260819_0002/0016) — bu
# kümenin DIŞINDA hiçbir değer SET ROLE'e asla ulaşmaz.
GECERLI_ROLLER = frozenset({"viewer", "data_operator", "admin"})


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
    kullanıcıya SIZDIRMAMALI."""
    client = create_supabase_client()
    if client is None:
        return None

    from supabase_auth.errors import AuthApiError

    try:
        yanit = client.auth.sign_in_with_password({"email": email, "password": sifre})
    except AuthApiError:
        return None

    if yanit.session is None or yanit.user is None:
        return None

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
