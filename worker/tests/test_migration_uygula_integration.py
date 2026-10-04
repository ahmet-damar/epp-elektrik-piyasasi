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


_RLS_UYUMLU_TABLO_SQL = (
    "CREATE TABLE IF NOT EXISTS test_migration_uygula_tablosu (id INT);\n"
    "ALTER TABLE test_migration_uygula_tablosu ENABLE ROW LEVEL SECURITY;\n"
    "DROP POLICY IF EXISTS test_migration_uygula_tablosu_all ON test_migration_uygula_tablosu;\n"
    "CREATE POLICY test_migration_uygula_tablosu_all ON test_migration_uygula_tablosu "
    "FOR ALL TO admin USING (true) WITH CHECK (true);\n"
)


def _basit_dosyalar(tmp_path: Path) -> Path:
    # Dosyalar RLS+politika İÇERİR (migration_uygula'nın kendi --uygula
    # sonrası otomatik rls_canli_kontrol.py çağrısı ile UYUMLU olsun —
    # gerçek migration'lar da hep bu şekilde, sentetik test tabloları da
    # aynı kurala tabi).
    dizin = tmp_path / "migrations"
    dizin.mkdir()
    (dizin / "9998_0001_tablo.sql").write_text(
        f"BEGIN;\n{_RLS_UYUMLU_TABLO_SQL}COMMIT;\n", encoding="utf-8"
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
    # `conn` fixture'ının bu SELECT'i açık bir transaction'da tutması,
    # migration_uygula'nın (ŞİMDİ her koşuda ALTER TABLE/CREATE POLICY
    # çalıştıran) sonraki çağrısını kilitte BEKLETİR (ACCESS SHARE lock
    # DDL ile çakışır) — statement_timeout'a kadar GERÇEKTEN asılı
    # kalır, gerçek bir testle BULUNDU. Salt-okuma transaction'ı
    # ROLLBACK ile hemen serbest bırakılır.
    conn.rollback()
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
        # RLS+politika: bootstrap sonrası otomatik rls_canli_kontrol.py
        # çağrısı ile UYUMLU olsun (bu tablo migration İÇERİĞİ üzerinden
        # DEĞİL, testin kendi setup'ı tarafından oluşturuluyor).
        cur.execute("ALTER TABLE test_bootstrap_tablosu ENABLE ROW LEVEL SECURITY")
        cur.execute(
            "CREATE POLICY test_bootstrap_tablosu_all ON test_bootstrap_tablosu "
            "FOR ALL TO admin USING (true) WITH CHECK (true)"
        )
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
    conn.rollback()  # bkz. test_ikinci_kosu_idempotent... notu — DDL kilidine girmesin

    # Bootstrap sonrası normal akış: yalnız işaretlenmeyen (0002) bekliyor olmalı.
    kod = _main(["--dizin", str(dizin), "--yedek-atla", "test"], monkeypatch)
    assert kod == 0


def test_tam_korumali_tablo_korumasiz_an_olmadan_kurulur_ve_idempotenttir(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """GÖREV 1 kanıtı: `_tam_korumali_tablo_olustur()` ilk çağrıda
    tablo+RLS+2 politika+grant'ı TEK transaction'da kurar (korumasız bir
    ARA an YOK), ikinci çağrıda (idempotent) patlamaz, VE gerçek
    `20261004_0001_schema_migrations.sql` dosyası normal akışla
    SONRADAN uygulandığında (politikalar ZATEN var olsa da) hata
    vermez — dosyadaki `DROP POLICY IF EXISTS` + `CREATE POLICY`
    deseni sayesinde."""
    dizin = _basit_dosyalar(tmp_path)
    # İlk koşu (dry-run yeter) — _tam_korumali_tablo_olustur HER modda çalışır.
    assert _main(["--dizin", str(dizin), "--yedek-atla", "test"], monkeypatch) == 0
    with conn.cursor() as cur:
        cur.execute(
            "SELECT relrowsecurity FROM pg_class WHERE relname = 'schema_migrations'"
        )
        assert cur.fetchone() == (True,)
        cur.execute(
            "SELECT policyname FROM pg_policies WHERE tablename = 'schema_migrations' "
            "ORDER BY 1"
        )
        assert [r[0] for r in cur.fetchall()] == [
            "admin_schema_migrations_insert",
            "admin_schema_migrations_select",
        ]
    conn.rollback()  # bkz. test_ikinci_kosu_idempotent... notu — DDL kilidine girmesin

    # İkinci koşu — idempotent, patlamamalı (DROP POLICY IF EXISTS + CREATE POLICY).
    assert _main(["--dizin", str(dizin), "--yedek-atla", "test"], monkeypatch) == 0

    # Gerçek migration dosyası SONRADAN normal akışla uygulanınca ÇAKIŞMASIN.
    gercek_migrasyon = (
        migration_uygula.MIGRATIONS_DIZIN_VARSAYILAN
        / "20261004_0001_schema_migrations.sql"
    )
    (dizin / "zzzz_son_20261004_0001_schema_migrations.sql").write_text(
        gercek_migrasyon.read_text(encoding="utf-8"), encoding="utf-8"
    )
    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--uygula"], monkeypatch
    )
    assert kod == 0


def test_tam_bos_tabloda_uctan_uca_calisir(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """GÖREV 3 kanıtı 1: `--tam --uygula` boş tabloda bootstrap'ı yapar,
    AYNI koşuda bekleyenleri uygular."""
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE test_bootstrap_tablosu (id INT)")
        cur.execute("ALTER TABLE test_bootstrap_tablosu ENABLE ROW LEVEL SECURITY")
        cur.execute(
            "CREATE POLICY test_bootstrap_tablosu_all ON test_bootstrap_tablosu "
            "FOR ALL TO admin USING (true) WITH CHECK (true)"
        )
    conn.commit()

    dizin = tmp_path / "migrations"
    dizin.mkdir()
    (dizin / "9998_0001_var.sql").write_text(
        "BEGIN;\nCREATE TABLE IF NOT EXISTS test_bootstrap_tablosu (id INT);\nCOMMIT;\n",
        encoding="utf-8",
    )
    (dizin / "9998_0002_yeni.sql").write_text(
        f"BEGIN;\n{_RLS_UYUMLU_TABLO_SQL}COMMIT;\n", encoding="utf-8"
    )

    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--tam", "--uygula"],
        monkeypatch,
    )
    assert kod == 0
    with conn.cursor() as cur:
        cur.execute("SELECT dosya_adi FROM schema_migrations ORDER BY 1")
        assert [r[0] for r in cur.fetchall()] == [
            "9998_0001_var.sql",
            "9998_0002_yeni.sql",
        ]
        cur.execute("SELECT to_regclass('test_migration_uygula_tablosu')")
        assert cur.fetchone()[0] is not None


def test_tam_dolu_tabloda_bootstrap_atlar(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """GÖREV 3 kanıtı 2: tablo DOLUYSA `--tam` bootstrap'ı atlar, hata
    vermeden doğrudan bekleyenleri uygular — tekrar tekrar çalıştırılabilir."""
    dizin = _basit_dosyalar(tmp_path)
    assert (
        _main(
            ["--dizin", str(dizin), "--yedek-atla", "test", "--tam", "--uygula"],
            monkeypatch,
        )
        == 0
    )
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schema_migrations")
        once = cur.fetchone()[0]
        assert once == 2
    conn.rollback()  # bkz. test_ikinci_kosu_idempotent... notu — DDL kilidine girmesin

    # İkinci --tam --uygula: tablo artık DOLU — bootstrap atlanır, hiçbir
    # şey patlamadan temiz döner (idempotent, tekrar çalıştırılabilir).
    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--tam", "--uygula"],
        monkeypatch,
    )
    assert kod == 0
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schema_migrations")
        assert cur.fetchone()[0] == once


def test_tam_bootstrap_patladiginda_uygulamaya_gecmez(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """GÖREV 3 kanıtı 3: bootstrap adımı KASITLI olarak patlatılırsa
    (`_bootstrap_core` sahte bir istisna fırlatır), uygulama adımına
    HİÇ GEÇİLMEZ — hiçbir dosya işlenmez."""
    dizin = _basit_dosyalar(tmp_path)

    def _patlayan(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("kasıtlı bozuk bootstrap")

    monkeypatch.setattr(migration_uygula, "_bootstrap_core", _patlayan)
    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--tam", "--uygula"],
        monkeypatch,
    )
    assert kod == 1
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM schema_migrations")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT to_regclass('test_migration_uygula_tablosu')")
        assert cur.fetchone()[0] is None


def test_uygula_sonrasi_rls_siz_tablo_birakan_migration_basarisiz_sayilir(
    conn, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """GÖREV 2 kanıtı: `--uygula` DDL'i başarıyla uygulasa da, arkasında
    RLS'siz/politikasız bir tablo bırakırsa genel sonuç 1 olmalı —
    `migration_uygula.py` başarılı bir `--uygula` koşusunun SONUNDA
    `rls_canli_kontrol.py`'yi OTOMATİK çağırır."""
    dizin = tmp_path / "migrations"
    dizin.mkdir()
    (dizin / "9998_0001_rlssiz.sql").write_text(
        "BEGIN;\nCREATE TABLE IF NOT EXISTS test_migration_uygula_tablosu (id INT);\nCOMMIT;\n",
        encoding="utf-8",
    )
    kod = _main(
        ["--dizin", str(dizin), "--yedek-atla", "test", "--uygula"], monkeypatch
    )
    assert kod == 1  # DDL'in kendisi başarılı oldu ama RLS kontrolü durdurdu
    with conn.cursor() as cur:
        # Migration'ın kendisi GERÇEKTEN uygulandı (kaydedildi) — RLS
        # kontrolü SONRADAN, AYRI bir adımda durduruyor, migration'ı
        # geri almıyor (gerçek Flyway/golang-migrate deseniyle TUTARLI:
        # "uygulandı ama arkasında sorun bıraktı" ≠ "hiç uygulanmadı").
        cur.execute("SELECT dosya_adi FROM schema_migrations")
        assert [r[0] for r in cur.fetchall()] == ["9998_0001_rlssiz.sql"]
        cur.execute("SELECT to_regclass('test_migration_uygula_tablosu')")
        assert cur.fetchone()[0] is not None
    rls_kapali, politikasiz = migration_uygula.rls_canli_kontrol.kontrol_et(conn)
    assert "test_migration_uygula_tablosu" in rls_kapali
    assert "test_migration_uygula_tablosu" in politikasiz
