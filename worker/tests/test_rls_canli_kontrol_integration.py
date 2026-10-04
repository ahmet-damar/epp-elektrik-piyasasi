"""EPP — `worker/scripts/rls_canli_kontrol.py` entegrasyon testi
(`Claude outputs/PROMPT_MIGRATION_KAPAT_2026-10-04.md`, GÖREV 2).

Kasıtlı bozuk örnekle (RLS'siz / politikasız bir tablo) ateşlediğini
kanıtlar — `worker/validate_rls_static.py`'nin AYNI disiplini (bkz.
`10_TEKNIK_MASTER_DOKUMAN.md` §16: "ateşlediği gösterilmeden
tamamlanmaz"), bu kez CANLI DB'ye karşı.
"""

from __future__ import annotations

import os

import psycopg
import pytest

from worker.scripts import rls_canli_kontrol

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tanımlı değil (yalnız CI 'integration' job'ında çalışır)",
)

_TEST_TABLO = "test_rls_canli_kontrol_bozuk"


@pytest.fixture
def conn():  # type: ignore[no-untyped-def]
    assert DATABASE_URL is not None
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {_TEST_TABLO}")  # nosec B608 - sabit test tablosu
        connection.commit()
        yield connection
        connection.rollback()
        with connection.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {_TEST_TABLO}")  # nosec B608
        connection.commit()


def test_temiz_canlida_hicbir_ihlal_bulunmaz(conn) -> None:  # type: ignore[no-untyped-def]
    assert rls_canli_kontrol.main() == 0


def test_rls_siz_tablo_yakalanir_ve_duzeltilince_gecer(conn) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(f"CREATE TABLE {_TEST_TABLO} (id INT)")  # nosec B608
    conn.commit()

    rls_kapali, politikasiz = rls_canli_kontrol.kontrol_et(conn)
    assert _TEST_TABLO in rls_kapali
    assert _TEST_TABLO in politikasiz
    assert rls_canli_kontrol.main() == 1

    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE {_TEST_TABLO} ENABLE ROW LEVEL SECURITY")  # nosec B608
    conn.commit()

    # RLS açık ama HÂLÂ politikasız — kısmi düzeltme de yakalanmalı.
    rls_kapali, politikasiz = rls_canli_kontrol.kontrol_et(conn)
    assert _TEST_TABLO not in rls_kapali
    assert _TEST_TABLO in politikasiz
    assert rls_canli_kontrol.main() == 1

    with conn.cursor() as cur:
        cur.execute(
            f"CREATE POLICY {_TEST_TABLO}_all ON {_TEST_TABLO} "  # nosec B608
            "FOR ALL TO admin USING (true) WITH CHECK (true)"
        )
    conn.commit()

    rls_kapali, politikasiz = rls_canli_kontrol.kontrol_et(conn)
    assert _TEST_TABLO not in rls_kapali
    assert _TEST_TABLO not in politikasiz
    assert rls_canli_kontrol.main() == 0
