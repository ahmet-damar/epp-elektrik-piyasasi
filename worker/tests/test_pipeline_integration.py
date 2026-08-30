"""EPP — Orkestrasyon (worker/pipeline.py) entegrasyon testi.

worker/tests/test_parser.py'nin gerçek dosyayla doğrulanmış sentetik xlsx'ini
(_sentetik_workbook) yeniden kullanır — bu dosyanın parser/kpi doğruluğu
zaten o dosyada ayrıntılı test edilmiştir; burada yalnız orkestrasyonun
(hash -> source_asset+batch -> atomik sahiplenme -> parse+doğrula+yükle ->
onay -> aktivasyon) doğru bağlandığı doğrulanır. DATABASE_URL yoksa (yerel
geliştirme) atlanır — bkz. worker/tests/test_ingest_integration.py.
"""

from __future__ import annotations

import os
from io import BytesIO

import openpyxl
import psycopg
import pytest

from worker import pipeline
from worker.tests.test_parser import _sentetik_workbook

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


def _wb_bytes(wb: openpyxl.Workbook) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _isle(conn, icerik: bytes, parser_version: str, schema_version: str = "s1"):  # type: ignore[no-untyped-def]
    """Testlerde ortak olan dosya_adi/tarih_id/source_period ile epdk_aylik_isle()'ı çağırır."""
    return pipeline.epdk_aylik_isle(
        conn,
        dosya_adi="test_pipeline.xlsx",
        icerik=icerik,
        tarih_id=202601,
        source_period="2026-01",
        parser_version=parser_version,
        schema_version=schema_version,
    )


def test_epdk_aylik_isle_uctan_uca(conn) -> None:  # type: ignore[no-untyped-def]
    icerik = _wb_bytes(_sentetik_workbook())

    sonuc = _isle(conn, icerik, "pipeline-test-v1")

    assert sonuc.sahiplenildi is True
    assert sonuc.eksik_tablolar == []
    assert set(sonuc.tablolar) == {
        "fact_uretim",
        "fact_abone",
        "fact_tuketim",
        "fact_serbest_tuketici",
    }
    # T7<->T11 (tuketim) tam eşleşiyor, T9<->T10 (abone) %0,5 tolerans içinde -
    # ikisi de sentetik veride mutabık (bkz. _sentetik_workbook rakamları).
    assert sonuc.mutabakat["fact_tuketim"] is True
    assert sonuc.mutabakat["fact_abone"] is True

    # Adım 4 tamamlandı: her tablo için raporlanan yuklenen sayısı, DB'de
    # is_active=false yazılan satır sayısıyla birebir eşleşmeli.
    with conn.cursor() as cur:
        # tablo, epdk_aylik_isle()'ın sonuc.tablolar'a yazdığı sabit anahtar
        # kümesinden (fact_uretim/fact_abone/fact_tuketim/fact_serbest_tuketici)
        # geliyor, kullanıcı girdisi değil.
        for tablo, tablo_sonucu in sonuc.tablolar.items():
            assert tablo_sonucu.yuklenen > 0
            cur.execute(
                f"SELECT count(*) FROM {tablo} WHERE ingestion_batch_id = %s AND NOT is_active",  # nosec B608
                (sonuc.batch_id,),
            )
            assert cur.fetchone()[0] == tablo_sonucu.yuklenen
            cur.execute(
                f"SELECT count(*) FROM {tablo} WHERE ingestion_batch_id = %s AND is_active",  # nosec B608
                (sonuc.batch_id,),
            )
            assert cur.fetchone()[0] == 0  # adım 5 henüz çağrılmadı

        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id = %s", (sonuc.batch_id,)
        )
        assert cur.fetchone()[0] == "running"  # bkz. modül notu: onay bekliyor

    # Adım 5: Faz 0'da UI yok — bu çağrı onay yerine geçer.
    pipeline.batch_onayla(conn, sonuc)

    with conn.cursor() as cur:
        for tablo, tablo_sonucu in sonuc.tablolar.items():
            cur.execute(
                f"SELECT count(*) FROM {tablo} WHERE ingestion_batch_id = %s AND is_active",  # nosec B608
                (sonuc.batch_id,),
            )
            assert cur.fetchone()[0] == tablo_sonucu.yuklenen

        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id = %s", (sonuc.batch_id,)
        )
        assert cur.fetchone()[0] == "succeeded"


def test_epdk_aylik_isle_eksik_tablo_reddedilir(conn) -> None:  # type: ignore[no-untyped-def]
    wb = _sentetik_workbook()
    wb.remove(wb["Tablo 11"])
    icerik = _wb_bytes(wb)

    sonuc = _isle(conn, icerik, "pipeline-test-eksik")

    assert sonuc.eksik_tablolar == ["Tablo 11"]
    assert sonuc.tablolar == {}  # hiçbir tablo işlenmedi

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, error_summary FROM ingestion_batch WHERE batch_id = %s",
            (sonuc.batch_id,),
        )
        status, ozet = cur.fetchone()
        assert status == "failed"
        assert "Tablo 11" in ozet

        cur.execute(
            "SELECT count(*) FROM fact_tuketim WHERE ingestion_batch_id = %s",
            (sonuc.batch_id,),
        )
        assert cur.fetchone()[0] == 0


def test_epdk_aylik_isle_p0_5_ikinci_cagri_sahiplenemez(conn) -> None:  # type: ignore[no-untyped-def]
    """Aynı (source_asset_id, parser_version, schema_version) -> aynı batch_id
    (P0-5); ilk çağrı zaten 'running'e taşıdığından ikinci çağrı sahiplenemez."""
    icerik = _wb_bytes(_sentetik_workbook())

    birinci = _isle(conn, icerik, "pipeline-test-tekil")
    assert birinci.sahiplenildi is True

    ikinci = _isle(conn, icerik, "pipeline-test-tekil")
    assert ikinci.sahiplenildi is False
    assert ikinci.batch_id == birinci.batch_id
    assert ikinci.tablolar == {}  # tekrar parse/yükleme yapılmadı
