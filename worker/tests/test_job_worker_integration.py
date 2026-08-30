"""EPP — Faz 1 asenkron worker (worker/job_worker.py) entegrasyon testi.

worker/tests/test_parser.py'nin gerçek dosyayla doğrulanmış sentetik xlsx'ini
(_sentetik_workbook) yeniden kullanır — burada yalnız kuyruk->worker->
otomatik-onay zincirinin doğru bağlandığı test edilir. DATABASE_URL yoksa
(yerel geliştirme) atlanır.
"""

from __future__ import annotations

import os
from io import BytesIO

import openpyxl
import psycopg
import pytest

from worker import ingest, job_worker, pipeline
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
        connection.rollback()


def _wb_bytes(wb: openpyxl.Workbook) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _wb_bytes_temiz(wb: openpyxl.Workbook) -> bytes:
    """_sentetik_workbook()'un T13'ünde bilinçli olarak negatif bir Mesken
    değeri (-5.0) var (kırmızı-satır/red testleri için, bkz. test_parser.py).
    'Tamamen temiz' (red=0, karantina=0) otomatik-aktivasyon yolunu test
    edebilmek için bu tek hücreyi nötrler - başka hiçbir tabloda red/karantina
    tetikleyen değer yok, mutabakat da T13'ten bağımsız (yalnız T7↔T11,
    T9↔T10) olduğundan bu değişiklik onu etkilemez."""
    t13 = wb["Tablo 13"]
    for row in t13.iter_rows():
        for cell in row:
            if cell.value == -5.0:
                cell.value = 0.0
    return _wb_bytes(wb)


# job_worker'ın gerçek dünya doğruluğu için _bir_is_isle() ara adımlarda
# conn.commit() ÇAĞIRMAK ZORUNDA (bkz. worker/job_worker.py modül notu) - bu
# yüzden bu dosyanın testleri CI'nin paylaşılan postgres:16'sında KALICI veri
# bırakır (diğer worker/tests/*.py dosyalarının aksine, connection.rollback()
# ile temizlenmez). Diğer dosyaların hepsi tarih_id=202601 (golden CSV/gerçek
# dosya) kullandığından, çakışmayı (örn. worker/tests/test_analytics_integration.py'nin
# satır sayısı beklentilerini bozmayı) önlemek için burada AYRI, sentinel bir
# tarih_id kullanılır.
_TEST_TARIH_ID = 209912
_TEST_SOURCE_PERIOD = "2099-12"


def _kuyruga_al(conn, icerik: bytes, parser_version: str, depo_dizini):  # type: ignore[no-untyped-def]
    return pipeline.epdk_isi_kuyruga_al(
        conn,
        dosya_adi="test_job_worker.xlsx",
        icerik=icerik,
        tarih_id=_TEST_TARIH_ID,
        source_period=_TEST_SOURCE_PERIOD,
        parser_version=parser_version,
        schema_version="s1",
        depo_dizini=depo_dizini,
    )


def test_job_worker_temiz_batch_otomatik_aktive_eder(conn, tmp_path) -> None:  # type: ignore[no-untyped-def]
    icerik = _wb_bytes_temiz(_sentetik_workbook())
    kuyruk = _kuyruga_al(conn, icerik, "job-worker-temiz", tmp_path)
    conn.commit()

    islenen = job_worker.calistir_once(conn, "test-worker-1")
    assert islenen == 1

    with conn.cursor() as cur:
        cur.execute("SELECT status FROM job_status WHERE job_id = %s", (kuyruk.job_id,))
        assert cur.fetchone() == ("succeeded",)

        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id = %s",
            (kuyruk.batch_id,),
        )
        assert cur.fetchone() == ("succeeded",)

        # otomatik aktive edildi: en az bir fact tablosunda is_active=true satır var
        cur.execute(
            "SELECT count(*) FROM fact_tuketim WHERE ingestion_batch_id = %s AND is_active",
            (kuyruk.batch_id,),
        )
        assert cur.fetchone()[0] > 0


def test_job_worker_supheli_batch_otomatik_aktive_etmez(conn, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Sentetik dosyanın T13'ünde bilinçli olarak negatif bir Mesken değeri
    var (bkz. test_parser._sentetik_workbook yorumu) - dogrula_serbest_tuketici
    bunu reddeder (red>0). otomatik_onaya_uygun() bu yüzden False döner;
    worker job'ı BAŞARILI sayar (parse/yükleme kendisi başarılı) ama batch'i
    aktive ETMEZ, 'running'de bırakır."""
    icerik = _wb_bytes(_sentetik_workbook())
    kuyruk = _kuyruga_al(conn, icerik, "job-worker-supheli", tmp_path)
    conn.commit()

    islenen = job_worker.calistir_once(conn, "test-worker-2")
    assert islenen == 1

    with conn.cursor() as cur:
        cur.execute("SELECT status FROM job_status WHERE job_id = %s", (kuyruk.job_id,))
        assert cur.fetchone() == ("succeeded",)  # iş kendisi başarılı

        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id = %s",
            (kuyruk.batch_id,),
        )
        assert cur.fetchone() == ("running",)  # ama aktive edilmedi

        cur.execute(
            "SELECT count(*) FROM fact_serbest_tuketici WHERE ingestion_batch_id = %s AND is_active",
            (kuyruk.batch_id,),
        )
        assert cur.fetchone()[0] == 0


def test_job_worker_eksik_tablo_retrying_yolu(conn, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Eksik tablo kalıcı bir hata - is_basarisiz() ilk denemede (attempt_count=1,
    eşiğin altında) 'retrying'e geçirir, ingestion_batch de senkron 'retrying' olur."""
    wb = _sentetik_workbook()
    wb.remove(wb["Tablo 11"])
    icerik = _wb_bytes(wb)
    kuyruk = _kuyruga_al(conn, icerik, "job-worker-eksik", tmp_path)
    conn.commit()

    islenen = job_worker.calistir_once(conn, "test-worker-3")
    assert islenen == 1

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, attempt_count FROM job_status WHERE job_id = %s",
            (kuyruk.job_id,),
        )
        assert cur.fetchone() == ("retrying", 1)

        cur.execute(
            "SELECT status, error_summary FROM ingestion_batch WHERE batch_id = %s",
            (kuyruk.batch_id,),
        )
        status, ozet = cur.fetchone()
        assert status == "retrying"
        assert "Tablo 11" in ozet

    # next_retry_at henüz gelmediğinden ikinci calistir_once hiçbir şey işlemez.
    assert ingest.is_sahiplen(conn, "test-worker-4") is None
