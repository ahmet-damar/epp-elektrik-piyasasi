"""EPP — Madde 1c araştırması (2026-09-17, doğrulama turu — kapsam
raporu Madde 1): batch 732 `running` dururken, 2024-02 AYNI parser
sürümüyle yeniden yüklenebilir mi?

**Kod okuması (worker/scripts/word_2024.py:isle_ay_uretim_geneli()):**
yükleme fonksiyonu, DB'ye yazmadan ÖNCE `SELECT ... WHERE source_period=
%s AND parser_version=%s AND status != 'failed'` kontrolü yapar — bir
satır bulursa `[ATLA]` yazıp `None` döner, YENİ bir batch OLUŞTURMAZ.
Bu test o UYGULAMA-KATMANI kontrolünü DEĞİL, ALTINDAKİ ŞEMA KISITINI
(ingestion_batch UNIQUE(source_asset_id, parser_version, schema_version))
izole olarak sınar — çünkü `kaynak_asset_olustur()` HER ÇAĞRIDA yeni bir
`source_asset_id` üretir (dosya hash'i AYNI olsa bile dedup YOK, bkz.
worker/ingest.py:kaynak_asset_olustur() — sade bir INSERT, ON CONFLICT
yok). Sonuç: UNIQUE kısıt yalnız AYNI source_asset_id'yi tekrar
denerken devreye girer (`batch_olustur()`'ın `ON CONFLICT DO UPDATE`
deseniyle var olan batch_id'yi döner, DUPLICATE OLUŞMAZ) — ama YENİ bir
source_asset_id ile (her gerçek dosya yükleme denemesinde olduğu gibi)
denendiğinde şema TAMAMEN SESSİZ kalır ve YENİ, AYRI bir batch satırı
OLUŞTURULUR. Yani gerçek "aynı dönem tekrar yüklenemez" garantisi
TAMAMEN uygulama katmanındaki (`word_2024.py`'nin kendi SELECT
kontrolü) bir disiplin meselesidir — şema düzeyinde HİÇBİR koruma YOK."""

from __future__ import annotations

import os

import psycopg
import pytest

from worker import ingest

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


def test_ayni_source_asset_id_ile_tekrar_batch_olustur_DUPLICATE_URETMEZ(
    conn,
) -> None:  # type: ignore[no-untyped-def]
    """UNIQUE(source_asset_id, parser_version, schema_version) — beklenen
    koruma: AYNI source_asset_id ile ikinci bir `batch_olustur()` çağrısı
    YENİ bir satır OLUŞTURMAZ, var olan `batch_id`'yi döner."""
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik_word",
        dosya_adi="test-2024-02.docx",
        icerik=b"sabit-icerik",
        donem_tipi="aylik",
        source_period="2095-02",
    )
    ilk_batch_id = ingest.batch_olustur(
        conn, source_asset_id, "word-2024-uretim-geneli-v1", "1"
    )
    ikinci_batch_id = ingest.batch_olustur(
        conn, source_asset_id, "word-2024-uretim-geneli-v1", "1"
    )

    assert ikinci_batch_id == ilk_batch_id
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM ingestion_batch WHERE source_asset_id = %s",
            (source_asset_id,),
        )
        assert cur.fetchone()[0] == 1


def test_farkli_source_asset_id_ile_ayni_donem_AYNI_PARSER_ILE_YENI_BATCH_URETIR(
    conn,
) -> None:  # type: ignore[no-untyped-def]
    """KRİTİK bulgu: gerçek bir dosya yükleme denemesi HER ZAMAN YENİ bir
    `source_asset_id` üretir (kaynak_asset_olustur() dedup yapmaz) — bu
    yüzden UNIQUE kısıtı, batch 732 `running` dururken 2024-02'nin AYNI
    parser sürümüyle (`word-2024-uretim-geneli-v1`) tekrar yüklenmesini
    ŞEMA SEVİYESİNDE ENGELLEMEZ. Gerçek koruma yalnız `word_2024.py`'nin
    KENDİ `SELECT ... status != 'failed'` ön kontrolündedir (kod okuması,
    bkz. modül notu) — bu test o ön kontrolü BİLEREK ATLAYIP yalnız şema
    davranışını izole gösterir."""
    source_asset_1 = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik_word",
        dosya_adi="test-2024-02-birinci-deneme.docx",
        icerik=b"ayni-donem-farkli-cagri-1",
        donem_tipi="aylik",
        source_period="2095-02",
    )
    batch_1 = ingest.batch_olustur(
        conn, source_asset_1, "word-2024-uretim-geneli-v1", "1"
    )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ingestion_batch SET status = 'running' WHERE batch_id = %s",
            (batch_1,),
        )

    # "Batch 1 hâlâ running dururken" — gerçek bir word_2024.py çalıştırması
    # SELECT ön kontrolünü BYPASS etseydi (ya da hiç yoksaydı) ne olurdu?
    source_asset_2 = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik_word",
        dosya_adi="test-2024-02-ikinci-deneme.docx",
        icerik=b"ayni-donem-farkli-cagri-2",
        donem_tipi="aylik",
        source_period="2095-02",
    )
    batch_2 = ingest.batch_olustur(
        conn, source_asset_2, "word-2024-uretim-geneli-v1", "1"
    )

    # Şema kısıtı bunu ENGELLEMEDİ — iki AYRI, geçerli batch_id üretildi.
    assert batch_2 != batch_1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) FROM ingestion_batch ib
            JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
            WHERE sa.source_period = '2095-02' AND ib.parser_version = 'word-2024-uretim-geneli-v1'
            """
        )
        assert (
            cur.fetchone()[0] == 2
        )  # İKİ batch, AYNI dönem+parser_version, şema izin verdi
