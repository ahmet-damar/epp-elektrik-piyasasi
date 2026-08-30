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

    # Adım 5: Faz 0'da UI yok — bu çağrı onay yerine geçer. Yalnız batch_id
    # alır (IslemSonucu DEĞİL) - bkz. pipeline.batch_onayla() docstring'i.
    aktive_edilen = pipeline.batch_onayla(conn, sonuc.batch_id)
    assert set(aktive_edilen) == set(sonuc.tablolar)

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


def test_batch_onayla_hicbir_tabloya_veri_yazilmamis_batch_hata_vermez(  # type: ignore[no-untyped-def]
    conn,
) -> None:
    """batch_onayla() artık batch_id alıyor (bkz. modül notu, ayrı süreçte
    çağrılabilme) — hiçbir fact tablosuna hiç satır yazmamış bir batch
    (tüm satırları reddedildi senaryosu) üzerinde çağrıldığında hata
    FIRLATMAMALI, yalnız hiçbir tabloyu aktive etmeden batch'i
    'succeeded' yapmalı."""
    from worker import ingest

    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi="test_bos_batch.xlsx",
        icerik=b"bos-batch-testi",
        donem_tipi="aylik",
        source_period="2026-01",
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, "test-bos-batch-v1", "s1")

    aktive_edilen = pipeline.batch_onayla(conn, batch_id)
    assert aktive_edilen == []

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id = %s", (batch_id,)
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


# NOT: adım 3'ün (atomik sahiplenme) "zaten sahiplenilmiş" yolu bilinçli olarak
# BURADA test edilmiyor. kaynak_asset_olustur() şu an file_hash'e göre HİÇ
# tekilleştirmiyor (her çağrı yeni bir source_asset satırı açıyor) - bu yüzden
# epdk_aylik_isle()'ı aynı bayt içerikle iki kez çağırmak farklı
# source_asset_id üretir ve P0-5'in (source_asset_id, parser_version,
# schema_version) tekilliği hiç devreye girmez; batch_sahiplen()'in False
# dönme yolu bu üst seviye arayüzden erişilemez. batch_sahiplen()'in atomik
# davranışı, aynı source_asset_id üzerinde doğrudan çalışıldığı düzeyde
# worker/tests/test_ingest_integration.py'de test ediliyor (bkz.
# test_batch_sahiplen_atomik_ikinci_cagri_basarisiz). source_asset'in
# file_hash'e göre tekilleştirilip tekilleştirilmeyeceği ayrı, açık bir karar
# olarak kullanıcıya soruldu (2026-08-30).
