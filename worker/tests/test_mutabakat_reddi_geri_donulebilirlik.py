"""EPP — İş C3 (2026-09-18): "mutabakat_reddedildi" bir KAPAN OLMAMALI —
aynı dönem, DEĞİŞİK bir kaynak dosyasıyla (farklı `file_hash`, örn. EPDK'nın
revize ettiği bir belge) normal şekilde yeniden yüklenip aktive
edilebilmeli. Uçtan uca disposable'da kanıtlanır (kullanıcı talimatı:
"Bu test geçmiyorsa tasarım yanlıştır")."""

from __future__ import annotations

import os

import psycopg
import pytest

from worker import ingest, pipeline
from worker.scripts import mutabakat_uretim

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


def _batch_ac(conn, icerik: bytes, parser_version: str, source_period: str) -> int:  # type: ignore[no-untyped-def]
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik_word",
        dosya_adi=f"test-{source_period}.docx",
        icerik=icerik,
        donem_tipi="aylik",
        source_period=source_period,
    )
    return ingest.batch_olustur(conn, source_asset_id, parser_version, "1")


def _kaynak_geneli_satiri_ekle(
    conn, tarih_id: int, batch_id: int, kaynak_id: int, lisans_id: int, mwh: float
) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_uretim_kaynak_geneli
                (tarih_id, kaynak_id, lisans_id, uretim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, %s, %s, false)
            """,
            (tarih_id, kaynak_id, lisans_id, mwh, batch_id),
        )


def test_reddedilen_batch_sonrasi_revize_dosya_normal_aktive_olur(conn) -> None:  # type: ignore[no-untyped-def]
    tarih_id = 209601
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
    with conn.cursor() as cur:
        cur.execute("SELECT lisans_id FROM dim_lisans WHERE tur = 'Lisansli'")
        lisans_id = cur.fetchone()[0]
        cur.execute("SELECT kaynak_id FROM dim_kaynak WHERE kaynak_adi = 'Rüzgar'")
        kaynak_id = cur.fetchone()[0]

    # --- 1) ORİJİNAL dosya: yüklenir, mutabakat REDDEDER (elle taklit
    # edilir — gerçek mutabakat_kontrol_et()'i tetiklemek bu testin
    # amacı değil, yalnız 'mutabakat_reddedildi' sonrası GERİ DÖNÜLEBİLİRLİK
    # test ediliyor) ---
    orijinal_batch = _batch_ac(
        conn, b"orijinal-dosya-icerigi-hatali", "word-2024-uretim-geneli-v1", "2096-01"
    )
    _kaynak_geneli_satiri_ekle(
        conn, tarih_id, orijinal_batch, kaynak_id, lisans_id, 1000.0
    )
    mutabakat_uretim.mutabakat_reddini_kaydet(
        conn,
        batch_id=orijinal_batch,
        tarih_id=tarih_id,
        sebep="test: il≠kaynak toplamı (taklit)",
        actor_name="test-c3",
    )

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, error_summary FROM ingestion_batch WHERE batch_id=%s",
            (orijinal_batch,),
        )
        durum, sebep_kayitli = cur.fetchone()
    assert durum == "mutabakat_reddedildi"
    assert "il≠kaynak toplamı" in sebep_kayitli
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM audit_log WHERE table_name='ingestion_batch' "
            "AND record_id=%s AND action_type='UPDATE'",
            (orijinal_batch,),
        )
        assert cur.fetchone()[0] == 1

    # --- 2) REVİZE dosya: AYNI dönem, AYNI parser_version, ama FARKLI
    # içerik (=FARKLI file_hash) — EPDK'nın düzeltilmiş bir belge
    # yayınladığını taklit eder. YENİ, AYRI bir source_asset+batch. ---
    revize_batch = _batch_ac(
        conn,
        b"revize-dosya-icerigi-duzeltilmis",
        "word-2024-uretim-geneli-v1",
        "2096-01",
    )
    assert revize_batch != orijinal_batch
    _kaynak_geneli_satiri_ekle(
        conn, tarih_id, revize_batch, kaynak_id, lisans_id, 1234.5
    )

    # --- 3) Revize batch NORMAL şekilde aktive edilebiliyor mu? ---
    aktive_edilen_tablolar = pipeline.batch_onayla(
        conn, revize_batch, actor_name="test-c3"
    )
    assert "fact_uretim_kaynak_geneli" in aktive_edilen_tablolar

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id=%s", (revize_batch,)
        )
        assert cur.fetchone()[0] == "succeeded"
        cur.execute(
            "SELECT is_active, uretim_mwh FROM fact_uretim_kaynak_geneli WHERE ingestion_batch_id=%s",
            (revize_batch,),
        )
        aktif, deger = cur.fetchone()
        assert aktif is True
        assert float(deger) == pytest.approx(1234.5)

    # --- 4) Reddedilen ORİJİNAL batch'in kendisi DOKUNULMADAN kaldı mı? ---
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id=%s", (orijinal_batch,)
        )
        assert cur.fetchone()[0] == "mutabakat_reddedildi"
        cur.execute(
            "SELECT is_active FROM fact_uretim_kaynak_geneli WHERE ingestion_batch_id=%s",
            (orijinal_batch,),
        )
        assert cur.fetchone()[0] is False  # hiç aktive edilmemişti, hâlâ pasif
