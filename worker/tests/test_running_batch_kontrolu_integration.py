"""EPP — `worker/scripts/running_batch_kontrolu.py` entegrasyon testi
(2026-09-17, doğrulama turu — Madde 1e). `created_at` doğrudan SQL ile
geçmişe ayarlanır (DEFAULT now()'ı bilerek geçersiz kılar) — DB'ye
gerçek zaman geçmesini beklemeden deterministik test."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from worker import ingest
from worker.scripts import running_batch_kontrolu as rbk

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tanımlı değil (yalnız CI 'integration' job'ında çalışır)",
)


@pytest.fixture
def conn():  # type: ignore[no-untyped-def]
    with psycopg.connect(DATABASE_URL) as connection:
        yield connection
        connection.rollback()  # test izolasyonu: hiçbir değişiklik kalıcı olmasın


def _batch_olustur_created_at_ile(
    conn, parser_version: str, created_at: datetime
) -> int:  # type: ignore[no-untyped-def]
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi=f"test_{parser_version}.xlsx",
        icerik=parser_version.encode(),
        donem_tipi="aylik",
        source_period="2096-01",
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, parser_version, "v1")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ingestion_batch SET status = 'running', created_at = %s WHERE batch_id = %s",
            (created_at, batch_id),
        )
    return batch_id


def test_esikten_eski_running_batch_yakalanir(conn) -> None:  # type: ignore[no-untyped-def]
    simdi = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    eski_batch = _batch_olustur_created_at_ile(
        conn, "test-rbk-eski", simdi - timedelta(hours=48)
    )

    takililar = rbk.takili_running_batchleri_bul(conn, esik_saat=24, simdi=simdi)
    batch_idler = {t.batch_id for t in takililar}
    assert eski_batch in batch_idler
    bulunan = next(t for t in takililar if t.batch_id == eski_batch)
    assert bulunan.kac_saattir_calisiyor == pytest.approx(48.0, abs=0.01)


def test_esikten_taze_running_batch_yakalanmaz(conn) -> None:  # type: ignore[no-untyped-def]
    simdi = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    taze_batch = _batch_olustur_created_at_ile(
        conn, "test-rbk-taze", simdi - timedelta(hours=2)
    )

    takililar = rbk.takili_running_batchleri_bul(conn, esik_saat=24, simdi=simdi)
    batch_idler = {t.batch_id for t in takililar}
    assert taze_batch not in batch_idler


def test_succeeded_batch_esikten_eski_olsa_bile_yakalanmaz(conn) -> None:  # type: ignore[no-untyped-def]
    """Yalnız `status='running'` ilgilendirir — tamamlanmış/başarısız
    batch'ler ne kadar eski olursa olsun 'takılı' SAYILMAZ."""
    simdi = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    eski_batch = _batch_olustur_created_at_ile(
        conn, "test-rbk-tamamlanmis", simdi - timedelta(hours=100)
    )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ingestion_batch SET status = 'succeeded' WHERE batch_id = %s",
            (eski_batch,),
        )

    takililar = rbk.takili_running_batchleri_bul(conn, esik_saat=24, simdi=simdi)
    batch_idler = {t.batch_id for t in takililar}
    assert eski_batch not in batch_idler


def test_mutabakat_reddedildi_batch_esikten_eski_olsa_bile_yakalanmaz(conn) -> None:  # type: ignore[no-untyped-def]
    """2026-09-18 (İş C4): YENİ terminal durum `'mutabakat_reddedildi'`
    eklendikten SONRA bu script'in davranışı hâlâ doğru mu? Yalnız
    `status='running'` filtrelendiği için EVET — bu durumdaki bir batch
    (örn. artık dönüştürülmüş eski batch 732 taklidi) ne kadar eski
    olursa olsun 'takılı' SAYILMAMALI (zaten kalıcı bir sonuca ulaşmış)."""
    simdi = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    eski_batch = _batch_olustur_created_at_ile(
        conn, "test-rbk-mutabakat-reddedildi", simdi - timedelta(hours=100)
    )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ingestion_batch SET status = 'mutabakat_reddedildi' WHERE batch_id = %s",
            (eski_batch,),
        )

    takililar = rbk.takili_running_batchleri_bul(conn, esik_saat=24, simdi=simdi)
    batch_idler = {t.batch_id for t in takililar}
    assert eski_batch not in batch_idler


def test_gercek_batch_732_deseninin_kucuk_olcekli_taklidi(conn) -> None:  # type: ignore[no-untyped-def]
    """Canlıda bulunan gerçek örnek (batch_id=732, `fact_uretim_kaynak_
    geneli`/2024-02, created_at=2026-09-16 06:58:57 UTC, mutabakat
    tarafından kalıcı olarak reddedildiği için süresiz 'running' kalmış
    — bkz. kapsam_raporu.md 'Doğrulama Turu' Madde 1) — AYNI yaş
    mertebesinde (~1 gün) sentetik bir batch, varsayılan 24 saatlik eşiği
    aşıyor mu diye test eder."""
    simdi = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)  # gerçek "bugün"
    gercek_732_yasi_saat = (
        simdi - datetime(2026, 9, 16, 6, 58, 57, tzinfo=UTC)
    ).total_seconds() / 3600
    assert (
        gercek_732_yasi_saat > rbk.VARSAYILAN_ESIK_SAAT
    )  # canlıda ZATEN eşiği aşmış durumda

    taklit_batch = _batch_olustur_created_at_ile(
        conn, "test-rbk-732-taklidi", simdi - timedelta(hours=gercek_732_yasi_saat)
    )
    takililar = rbk.takili_running_batchleri_bul(conn, simdi=simdi)
    assert taklit_batch in {t.batch_id for t in takililar}
