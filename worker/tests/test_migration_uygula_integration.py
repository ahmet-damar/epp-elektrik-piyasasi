"""EPP — `worker/scripts/migration_uygula.py` entegrasyon testi
(`Claude outputs/PROMPT_MIGRATION_CANLI_2026-10-04.md`).

Gerçek `supabase/migrations/` yerine her testin kendi `tmp_path`'inde
sentetik, küçük `.sql` dosya setleri kullanılır (`--dizin` ile) — ama
`schema_migrations` tablosunun KENDİSİ paylaşılan bir fiziksel tablodur
(disposable DB'nin kendi migration kurulumunda zaten oluşturuldu), bu
yüzden her test öncesi/sonrası TRUNCATE edilir.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
import pytest

from worker.scripts import migration_uygula

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tanımlı değil (yalnız CI 'integration' job'ında çalışır)",
)

_TEST_TABLOLARI = (
    "test_migration_uygula_tablosu",
    "test_migration_uygula_bozuk",
    "test_bootstrap_tablosu",
)


@pytest.fixture
def conn():  # type: ignore[no-untyped-def]
    assert DATABASE_URL is not None
    with psycopg.connect(DATABASE_URL) as connection:
        _temizle(connection)
        yield connection
        connection.rollback()
        _temizle(connection)


def _temizle(connection: psycopg.Connection) -> None:
    with connection.cursor() as cur:
        cur.execute("TRUNCATE schema_migrations")
        cur.execute("DELETE FROM audit_log WHERE table_name = 'schema_migrations'")
        for tablo in _TEST_TABLOLARI:
            cur.execute(f"DROP TABLE IF EXISTS {tablo}")  # nosec B608 - sabit test tablo listesi
    connection.commit()


def _main(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(sys, "argv", ["migration_uygula.py", *argv])
    return migration_uygula.main()


def _basit_dosyalar(tmp_path: Path) -> Path:
    dizin = tmp_path / "migrations"
    dizin.mkdir()
    (dizin / "9998_0001_tablo.sql").write_text(
        "BEGIN;\nCREATE TABLE IF NOT EXISTS test_migration_uygula_tablosu (id INT);\nCOMMIT;\n",
        encoding="utf-8",
    )
    (dizin / "9998_0002_kolon.sql").write_text(
        "BEGIN;\nALTER TABLE test_migration_uygula_tablosu ADD COLUMN ad TEXT;\nCOMMIT;\n",
        encoding="utf-8",
    )
    return dizin


def test_dry_run_hicbir_sey_yazmaz(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    dizin = _basit_dosyalar(tmp_path)
    kod = _main(["--dizin", str(dizin), "--yedek-atla", "test"], monkeypatch)
    assert kod == 0
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schema_migrations")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT to_regclass('test_migration_uygula_tablosu')")
        assert cur.fetchone()[0] is None


def test_uygula_eksik_migrationlari_uygular_ve_kaydeder(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    dizin = _basit_dosyalar(tmp_path)
    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--uygula"], monkeypatch
    )
    assert kod == 0
    with conn.cursor() as cur:
        cur.execute("SELECT dosya_adi FROM schema_migrations ORDER BY dosya_adi")
        assert [r[0] for r in cur.fetchall()] == [
            "9998_0001_tablo.sql",
            "9998_0002_kolon.sql",
        ]
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'test_migration_uygula_tablosu'"
        )
        kolonlar = {r[0] for r in cur.fetchall()}
        assert kolonlar == {"id", "ad"}


def test_ikinci_kosu_idempotent_hicbir_sey_yapmaz(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    dizin = _basit_dosyalar(tmp_path)
    assert (
        _main(["--dizin", str(dizin), "--yedek-atla", "test", "--uygula"], monkeypatch)
        == 0
    )
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schema_migrations")
        once = cur.fetchone()[0]
    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--uygula"], monkeypatch
    )
    assert kod == 0
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schema_migrations")
        assert cur.fetchone()[0] == once


def test_hash_uyusmazliginda_gercekten_durur(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    dizin = _basit_dosyalar(tmp_path)
    assert (
        _main(["--dizin", str(dizin), "--yedek-atla", "test", "--uygula"], monkeypatch)
        == 0
    )
    # Uygulanmış bir dosyaya KASITLI bir boşluk ekle (içerik değişti, hash değişti).
    hedef = dizin / "9998_0001_tablo.sql"
    hedef.write_text(
        hedef.read_text(encoding="utf-8") + "\n-- kasıtlı bozuk değişiklik\n",
        encoding="utf-8",
    )
    kod = _main(["--dizin", str(dizin), "--yedek-atla", "test"], monkeypatch)
    assert kod == 1


def test_ortasinda_patlayan_migrationda_sonraki_uygulanmiyor(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    dizin = tmp_path / "migrations"
    dizin.mkdir()
    (dizin / "9998_0001_iyi.sql").write_text(
        "BEGIN;\nCREATE TABLE IF NOT EXISTS test_migration_uygula_tablosu (id INT);\nCOMMIT;\n",
        encoding="utf-8",
    )
    (dizin / "9998_0002_bozuk.sql").write_text(
        "BEGIN;\nSELEKT KASITLI BOZUK SOZDIZIMI;\nCOMMIT;\n", encoding="utf-8"
    )
    (dizin / "9998_0003_sonraki.sql").write_text(
        "BEGIN;\nCREATE TABLE IF NOT EXISTS test_migration_uygula_bozuk (id INT);\nCOMMIT;\n",
        encoding="utf-8",
    )
    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--uygula"], monkeypatch
    )
    assert kod == 1
    with conn.cursor() as cur:
        cur.execute("SELECT dosya_adi FROM schema_migrations")
        assert [r[0] for r in cur.fetchall()] == ["9998_0001_iyi.sql"]
        cur.execute("SELECT to_regclass('test_migration_uygula_bozuk')")
        assert cur.fetchone()[0] is None


def test_bootstrap_dolu_tabloda_reddedilir(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    dizin = _basit_dosyalar(tmp_path)
    assert (
        _main(["--dizin", str(dizin), "--yedek-atla", "test", "--uygula"], monkeypatch)
        == 0
    )
    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--bootstrap"], monkeypatch
    )
    assert kod == 1


def test_bootstrap_mevcut_nesneleri_isaretler_eksikte_durur(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE test_bootstrap_tablosu (id INT)")
    conn.commit()

    dizin = tmp_path / "migrations"
    dizin.mkdir()
    (dizin / "9998_0001_var.sql").write_text(
        "BEGIN;\nCREATE TABLE IF NOT EXISTS test_bootstrap_tablosu (id INT);\nCOMMIT;\n",
        encoding="utf-8",
    )
    (dizin / "9998_0002_yok.sql").write_text(
        "BEGIN;\nCREATE TABLE IF NOT EXISTS test_migration_uygula_bozuk (id INT);\nCOMMIT;\n",
        encoding="utf-8",
    )

    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--bootstrap", "--uygula"],
        monkeypatch,
    )
    assert kod == 0
    with conn.cursor() as cur:
        cur.execute("SELECT dosya_adi FROM schema_migrations")
        assert [r[0] for r in cur.fetchall()] == ["9998_0001_var.sql"]

    # Bootstrap sonrası normal akış: yalnız işaretlenmeyen (0002) bekliyor olmalı.
    kod = _main(["--dizin", str(dizin), "--yedek-atla", "test"], monkeypatch)
    assert kod == 0
