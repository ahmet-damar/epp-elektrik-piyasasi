"""EPP — Ingest pipeline entegrasyon testi (P0-4 aktivasyon + P0-5 batch versiyonlama).

Yalnızca DATABASE_URL tanımlıysa çalışır: CI'nin 'integration' job'ı bir
postgres:16 servisi açıp supabase/migrations/*.sql dosyalarının tümünü
(dim seed dahil) sırayla uygular. Yerel geliştirme ortamında Postgres
olmadığından bu test burada atlanır — bkz. worker/ingest.py modül notu.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from worker import ingest, kpi

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tanımlı değil (yalnız CI 'integration' job'ında çalışır)",
)

GOLDEN_INPUT = Path(__file__).parent / "golden" / "input"


@pytest.fixture
def conn():  # type: ignore[no-untyped-def]
    with psycopg.connect(DATABASE_URL) as connection:
        yield connection
        connection.rollback()  # test izolasyonu: hiçbir değişiklik kalıcı olmasın


def _yeni_batch(conn, parser_version: str) -> int:  # type: ignore[no-untyped-def]
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi=f"test_{parser_version}.xlsx",
        icerik=parser_version.encode(),
        donem_tipi="aylik",
        source_period="2026-01",
    )
    return ingest.batch_olustur(conn, source_asset_id, parser_version, "v1")


def test_dim_grup_bilinmiyorsa_hata(conn) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="Bilinmeyen"):
        ingest.dim_grup_id_bul(conn, "Var Olmayan Grup XYZ")


def test_dim_lookuplar_seed_edilmis(conn) -> None:  # type: ignore[no-untyped-def]
    assert ingest.dim_grup_id_bul(conn, "Mesken") > 0
    assert ingest.dim_kaynak_id_bul(conn, "Hidrolik") > 0
    assert ingest.dim_lisans_id_bul(conn, "Lisanslı") > 0
    assert ingest.dim_lisans_id_bul(conn, "Lisanssız") > 0


def test_tuketim_yukle_ve_p0_4_aktivasyon(conn) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, 202601)
    tuketim = kpi.yukle_tuketim(GOLDEN_INPUT / "tuketim.csv").kabul

    batch1 = _yeni_batch(conn, "test-v1")
    yuklenen, atlanan = ingest.fact_tuketim_yukle(conn, tuketim, batch1)
    assert yuklenen == 6
    assert atlanan == 0
    ingest.aktivasyon_yap(conn, "fact_tuketim", batch1)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM fact_tuketim WHERE ingestion_batch_id = %s AND is_active",
            (batch1,),
        )
        assert cur.fetchone()[0] == 6

    # P0-5: aynı dosya + düzeltilmiş parser → yeni batch, aynı doğal anahtarlar.
    batch2 = _yeni_batch(conn, "test-v2")
    ingest.fact_tuketim_yukle(conn, tuketim, batch2)
    ingest.aktivasyon_yap(conn, "fact_tuketim", batch2)

    with conn.cursor() as cur:
        # P0-4: eski batch pasif, yeni batch aktif; aynı doğal anahtar için TEK aktif satır.
        cur.execute(
            "SELECT count(*) FROM fact_tuketim WHERE ingestion_batch_id = %s AND is_active",
            (batch1,),
        )
        assert cur.fetchone()[0] == 0

        cur.execute(
            "SELECT count(*) FROM fact_tuketim WHERE ingestion_batch_id = %s AND is_active",
            (batch2,),
        )
        assert cur.fetchone()[0] == 6

        cur.execute(
            """
            SELECT il_kodu, tarih_id, grup_id, baglanti, count(*)
            FROM fact_tuketim
            WHERE is_active
            GROUP BY il_kodu, tarih_id, grup_id, baglanti
            HAVING count(*) > 1
            """
        )
        assert cur.fetchall() == []


def test_uretim_ve_abone_yukle(conn) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, 202601)
    uretim = kpi.yukle_uretim(GOLDEN_INPUT / "uretim.csv").kabul
    abone = kpi.yukle_abone(GOLDEN_INPUT / "abone.csv").kabul

    batch = _yeni_batch(conn, "test-uretim-abone")
    yuklenen_u, atlanan_u = ingest.fact_uretim_yukle(conn, uretim, batch)
    assert yuklenen_u == 5
    assert atlanan_u == 0

    yuklenen_a, atlanan_a = ingest.fact_abone_yukle(conn, abone, batch)
    assert yuklenen_a == 5
    assert atlanan_a == 0

    ingest.aktivasyon_yap(conn, "fact_uretim", batch)
    ingest.aktivasyon_yap(conn, "fact_abone", batch)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM fact_uretim WHERE ingestion_batch_id = %s AND is_active",
            (batch,),
        )
        assert cur.fetchone()[0] == 5
        cur.execute(
            "SELECT count(*) FROM fact_abone WHERE ingestion_batch_id = %s AND is_active",
            (batch,),
        )
        assert cur.fetchone()[0] == 5


def test_batch_olustur_p0_5_tekil(conn) -> None:  # type: ignore[no-untyped-def]
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi="tekil_test.xlsx",
        icerik=b"ayni-dosya",
        donem_tipi="aylik",
        source_period="2026-01",
    )
    b1 = ingest.batch_olustur(conn, source_asset_id, "v1", "s1")
    b2 = ingest.batch_olustur(conn, source_asset_id, "v1", "s1")
    assert (
        b1 == b2
    )  # aynı (source_asset_id, parser_version, schema_version) → aynı batch

    b3 = ingest.batch_olustur(conn, source_asset_id, "v2", "s1")
    assert b3 != b1  # düzeltilmiş parser_version → yeni batch
