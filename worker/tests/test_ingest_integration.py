"""EPP — Ingest pipeline entegrasyon testi (P0-4 aktivasyon + P0-5 batch versiyonlama).

Yalnızca DATABASE_URL tanımlıysa çalışır: CI'nin 'integration' job'ı bir
postgres:16 servisi açıp supabase/migrations/*.sql dosyalarının tümünü
(dim seed dahil) sırayla uygular. Yerel geliştirme ortamında Postgres
olmadığından bu test burada atlanır — bkz. worker/ingest.py modül notu.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
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


def test_fact_uretim_uretim_mwh_kolonu_olmadan_yuklenir(conn) -> None:  # type: ignore[no-untyped-def]
    """T1/T4'ün ham çıktısında uretim_mwh sütunu hiç yok (bkz. worker/parser.py
    modül notu — aylık raporda il×kaynak grain'inde üretim verisi mevcut
    değil). kurulu_guc_mw doluysa satır kabul edilmeli, uretim_mwh NULL yazılmalı."""
    ingest.dim_tarih_getir_veya_olustur(conn, 202601)
    kurulu = kpi.yukle_uretim(GOLDEN_INPUT / "uretim.csv").kabul.drop(
        columns=["uretim_mwh"]
    )
    assert "uretim_mwh" not in kurulu.columns

    batch = _yeni_batch(conn, "test-kurulu-guc-only")
    yuklenen, atlanan = ingest.fact_uretim_yukle(conn, kurulu, batch)
    assert yuklenen == 5
    assert atlanan == 0

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM fact_uretim WHERE ingestion_batch_id = %s AND uretim_mwh IS NULL",
            (batch,),
        )
        assert cur.fetchone()[0] == 5


def test_serbest_tuketici_yukle_ve_rejected_row_count(conn) -> None:  # type: ignore[no-untyped-def]
    """T13: iki ölçüden biri eksikse satır atlanır VE bu sayı sessizce
    kaybolmaz — ingestion_batch.rejected_row_count'a yansıtılır (diğer
    dogrula_*/red mantığıyla tutarlı)."""
    ingest.dim_tarih_getir_veya_olustur(conn, 202601)
    df = pd.DataFrame(
        [
            {
                "il_kodu": 26,
                "tarih_id": 202601,
                "tur": "Serbest Tuketici",
                "grup": "Mesken",
                "tuketim_mwh": 100.0,
                "tuketici_sayisi": 5.0,
            },
            {
                "il_kodu": 26,
                "tarih_id": 202601,
                "tur": "Serbest Tuketici",
                "grup": "Sanayi",
                "tuketim_mwh": 200.0,
                "tuketici_sayisi": 10.0,
            },
            {
                "il_kodu": 26,
                "tarih_id": 202601,
                "tur": "Serbest Tuketici",
                "grup": "Tarımsal",
                "tuketim_mwh": None,  # boş hücre — dogrula_serbest_tuketici reddetmez,
                "tuketici_sayisi": None,  # ama fact tablosu NOT NULL: yukle_* atlar.
            },
        ]
    )
    kabul = kpi.dogrula_serbest_tuketici(df).kabul
    assert len(kabul) == 3  # negatif/bilinmeyen yok, hiçbiri red/karantina değil

    batch = _yeni_batch(conn, "test-serbest-tuketici")
    yuklenen, atlanan = ingest.fact_serbest_tuketici_yukle(conn, kabul, batch)
    assert yuklenen == 2
    assert atlanan == 1

    ingest.batch_durumu_guncelle(
        conn,
        batch,
        "succeeded",
        accepted_row_count=yuklenen,
        rejected_row_count=atlanan,
    )

    with conn.cursor() as cur:
        cur.execute(
            "SELECT accepted_row_count, rejected_row_count FROM ingestion_batch WHERE batch_id = %s",
            (batch,),
        )
        assert cur.fetchone() == (2, 1)

    ingest.aktivasyon_yap(conn, "fact_serbest_tuketici", batch)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM fact_serbest_tuketici WHERE ingestion_batch_id = %s AND is_active",
            (batch,),
        )
        assert cur.fetchone()[0] == 2


def test_batch_sahiplen_atomik_ikinci_cagri_basarisiz(conn) -> None:  # type: ignore[no-untyped-def]
    """Adım 3 (dokumanlar/01 §4): 'queued' -> 'running' geçişi ATOMİK. Aynı
    batch_id üzerinde ikinci çağrı (batch zaten sahiplenilmiş/'running')
    False döner - iki worker aynı batch'i aynı anda işlemeye kalkışamaz."""
    batch_id = _yeni_batch(conn, "test-sahiplen")

    birinci = ingest.batch_sahiplen(conn, batch_id)
    assert birinci is True

    ikinci = ingest.batch_sahiplen(conn, batch_id)
    assert ikinci is False

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id = %s", (batch_id,)
        )
        assert cur.fetchone()[0] == "running"


def test_is_kuyruk_atomik_sahiplenme(conn) -> None:  # type: ignore[no-untyped-def]
    """Faz 1: is_sahiplen() bir 'queued' işi bulup 'running'e taşır, attempt_count
    1'e çıkar; hemen ardından ikinci bir sahiplenme denemesi (henüz heartbeat
    bayat değil) None döner - iki worker aynı işi paylaşamaz."""
    job_id = ingest.is_kaydi_olustur(conn, "test-correlation-1")

    job = ingest.is_sahiplen(conn, "worker-a")
    assert job is not None
    assert job.job_id == job_id
    assert job.correlation_id == "test-correlation-1"
    assert job.attempt_count == 1

    ikinci = ingest.is_sahiplen(conn, "worker-b")
    assert ikinci is None

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, locked_by FROM job_status WHERE job_id = %s", (job_id,)
        )
        assert cur.fetchone() == ("running", "worker-a")


def test_is_basarisiz_once_deneme_retrying_esik_ustunde_dead_letter(  # type: ignore[no-untyped-def]
    conn,
) -> None:
    """attempt_count eşiğin (_MAX_DENEME=5) altındaysa 'retrying' + üstel
    geri çekilme; eşiğe ulaşmışsa 'dead_letter'. Gerçek backoff süresini
    beklemeden test etmek için IsKaydi elle, farklı attempt_count'larla
    oluşturuluyor."""
    job_id = ingest.is_kaydi_olustur(conn, "test-correlation-2")

    ilk_deneme = ingest.IsKaydi(
        job_id=job_id, correlation_id="test-correlation-2", attempt_count=1
    )
    durum = ingest.is_basarisiz(conn, ilk_deneme)
    assert durum == "retrying"
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, next_retry_at IS NOT NULL FROM job_status WHERE job_id = %s",
            (job_id,),
        )
        assert cur.fetchone() == ("retrying", True)

    son_deneme = ingest.IsKaydi(
        job_id=job_id, correlation_id="test-correlation-2", attempt_count=5
    )
    durum = ingest.is_basarisiz(conn, son_deneme)
    assert durum == "dead_letter"
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM job_status WHERE job_id = %s", (job_id,))
        assert cur.fetchone() == ("dead_letter",)


def test_is_sahiplen_bayat_heartbeat_geri_alir(conn) -> None:  # type: ignore[no-untyped-def]
    """Bir worker bir işi sahiplenip çökerse (heartbeat_at güncellenmeyi
    bırakırsa), _STALE_ESIK_SANIYE'den eskiyse başka bir is_sahiplen() çağrısı
    onu 'queued'a geri alıp yeniden sahiplenir - kalıcı olarak kilitli kalmaz."""
    job_id = ingest.is_kaydi_olustur(conn, "test-correlation-3")
    ilk = ingest.is_sahiplen(conn, "worker-cokecek")
    assert ilk is not None
    assert ilk.attempt_count == 1

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE job_status SET heartbeat_at = now() - interval '20 minutes' WHERE job_id = %s",
            (job_id,),
        )

    kurtaran = ingest.is_sahiplen(conn, "worker-kurtaran")
    assert kurtaran is not None
    assert kurtaran.job_id == job_id
    assert kurtaran.attempt_count == 2  # ikinci deneme

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, locked_by FROM job_status WHERE job_id = %s", (job_id,)
        )
        assert cur.fetchone() == ("running", "worker-kurtaran")


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
