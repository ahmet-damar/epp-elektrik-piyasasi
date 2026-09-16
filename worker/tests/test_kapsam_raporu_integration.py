"""EPP — `worker/scripts/kapsam_raporu.py` entegrasyon testi (2026-09-17).

Yalnızca DATABASE_URL tanımlıysa çalışır (bkz. worker/tests/
test_mutabakat_uretim.py ile AYNI desen). `fact_tuketim_ulke_geneli`
üzerinde sentetik, izole bir tarih_id aralığı (2094) kullanılır —
tablonun GERÇEK verisinden bağımsız, `conn` fixture'ının rollback'i
sayesinde diğer testlerden de izole."""

from __future__ import annotations

import os

import psycopg
import pytest

from worker import ingest
from worker.scripts import kapsam_raporu as kr

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


def _yeni_batch(conn, parser_version: str) -> int:  # type: ignore[no-untyped-def]
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi=f"test_{parser_version}.xlsx",
        icerik=parser_version.encode(),
        donem_tipi="aylik",
        source_period="2094-01",
    )
    return ingest.batch_olustur(conn, source_asset_id, parser_version, "v1")


def _batch_durumunu_ayarla(conn, batch_id: int, status: str) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ingestion_batch SET status = %s WHERE batch_id = %s",
            (status, batch_id),
        )


def _grup_id(conn, grup_adi: str) -> int:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = %s", (grup_adi,)
        )
        return cur.fetchone()[0]


def _ulke_geneli_ekle(
    conn, tarih_id: int, batch_id: int, grup_id: int, mwh: float, is_active: bool
) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_tuketim_ulke_geneli
                (tarih_id, grup_id, tuketim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (tarih_id, grup_id, mwh, batch_id, is_active),
        )


_TUM_GRUPLAR = (
    "Mesken",
    "Sanayi",
    "Tarımsal",
    "Aydınlatma",
    "Kamu ve Özel Hizmetler",
)


def test_rapor_olustur_gercek_senaryo_eksik_kismi_ve_pasif_ay(conn) -> None:  # type: ignore[no-untyped-def]
    """Tek bir senaryoda üçünü birden kurar: 209401/209402 TAM (5/5 grup),
    209403 tamamen EKSİK (hiç aktif satır yok) ama YÜKLÜ-PASİF bir batch'i
    VAR (gerçek Bulgu J deseninin küçük ölçekli bir taklidi), 209404 KISMİ
    (yalnız 3/5 grup aktif)."""
    aktif_batch = _yeni_batch(conn, "test-kapsam-raporu-aktif")
    pasif_batch = _yeni_batch(conn, "test-kapsam-raporu-pasif")
    _batch_durumunu_ayarla(conn, pasif_batch, "succeeded")

    for tarih_id in (209401, 209402, 209403, 209404):
        ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)

    for tarih_id in (209401, 209402):
        for grup_adi in _TUM_GRUPLAR:
            _ulke_geneli_ekle(
                conn, tarih_id, aktif_batch, _grup_id(conn, grup_adi), 1000.0, True
            )

    # 209403: HİÇ aktif satır yok — yalnız pasif (yüklü ama aktive edilmemiş).
    _ulke_geneli_ekle(conn, 209403, pasif_batch, _grup_id(conn, "Mesken"), 500.0, False)

    # 209404: kısmi — yalnız 3/5 grup aktif.
    for grup_adi in ("Mesken", "Sanayi", "Tarımsal"):
        _ulke_geneli_ekle(
            conn, 209404, aktif_batch, _grup_id(conn, grup_adi), 1000.0, True
        )

    rapor = kr.rapor_olustur(conn)
    tr = next(t for t in rapor.tablolar if t.tanim.ad == "fact_tuketim_ulke_geneli")

    assert tr.min_tarih_id == 209401
    assert tr.max_tarih_id == 209404
    # 209403 aktif satır içermediği için eksik ay listesinde olmalı.
    assert tr.eksik_aylar == [209403]
    # Modal (en sık) grup sayısı 5 olmalı (209401/209402'den).
    assert tr.modal_kardinalite["grup_id"] == 5
    # 209404, 3 grupla modalden (5) sapıyor — kısmi ay olarak yakalanmalı.
    assert tr.kismi_aylar == {209404: {"grup_id": (3, 5)}}
    # 209403 pasif kayıtlar arasında (batch durumu 'succeeded') görünmeli.
    pasif_donemler = {p["tarih_id"]: p for p in tr.pasif_kayitlar}
    assert 209403 in pasif_donemler
    assert pasif_donemler[209403]["batch_status"] == "succeeded"
    assert pasif_donemler[209403]["ingestion_batch_id"] == pasif_batch


def test_veri_kapsam_disi_getir_gercek_satirlari_okur(conn) -> None:  # type: ignore[no-untyped-def]
    """`veri_kapsam_disi` canlı/disposable'da ZATEN mevcut olabilecek
    satırları (varsa) döndürür — yalnız fonksiyonun sorgu/şema uyumunu
    doğrular, belirli bir satır sayısı VARSAYMAZ."""
    satirlar = kr.veri_kapsam_disi_getir(conn)
    assert isinstance(satirlar, list)
    for satir in satirlar:
        assert {
            "tarih_id",
            "fact_tablosu",
            "nitelik",
            "sebep",
            "karar_referansi",
            "created_at",
        } <= satir.keys()
