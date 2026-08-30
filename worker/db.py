from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

# Proje kökündeki .env dosyasını sürece yükler (varsa) - zaten ayarlı ortam
# değişkenlerinin üzerine yazmaz (override=False, varsayılan). CI ve gerçek
# deploy'larda .env dosyası yoktur, bu durumda load_dotenv() sessizce no-op'tur
# ve DATABASE_URL/SUPABASE_* zaten iş akışının kendi env değişkenlerinden gelir.
load_dotenv()


def _read_env(name: str) -> str:
    return os.getenv(name, "").strip()


def get_database_url() -> str | None:
    value = _read_env("DATABASE_URL")
    return value or None


def get_supabase_url() -> str | None:
    value = _read_env("SUPABASE_URL")
    return value or None


def get_supabase_anon_key() -> str | None:
    value = _read_env("SUPABASE_ANON_KEY")
    return value or None


def get_service_role_key() -> str | None:
    value = _read_env("SUPABASE_SERVICE_ROLE_KEY")
    return value or None


def create_supabase_client() -> Any | None:
    supabase_url = get_supabase_url()
    anon_key = get_supabase_anon_key()
    if not supabase_url or not anon_key:
        return None

    try:
        from supabase import create_client
    except ImportError:
        return None

    return create_client(supabase_url, anon_key)


def get_db_connection() -> Any | None:
    database_url = get_database_url()
    if not database_url:
        return None

    try:
        import psycopg
    except ImportError:
        return None

    try:
        return psycopg.connect(database_url)
    except psycopg.Error:
        return None


def resolve_database_or_fallback() -> tuple[Any | None, str]:
    connection = get_db_connection()
    if connection is not None:
        return connection, "PostgreSQL via DATABASE_URL"

    client = create_supabase_client()
    if client is not None:
        return client, "Supabase via anon key"

    return (
        None,
        "No database connection configured; continuing with local fallback data.",
    )
