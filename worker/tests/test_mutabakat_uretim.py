"""EPP — `worker/scripts/mutabakat_uretim.py` entegrasyon testi
(2026-09-09, gece çalışması — Aşama 3/ADIM 3 madde 3).

Yalnızca DATABASE_URL tanımlıysa çalışır (bkz. worker/tests/
test_ingest_integration.py modül notuyla AYNI desen). `fact_uretim_il_
geneli`/`fact_uretim_kaynak_geneli` için henüz özel bir `ingest.py`
yükleme fonksiyonu YOK (bu ADIM 3 madde 4'te gelecek) — bu yüzden test
verisi doğrudan SQL INSERT ile, `_yeni_batch()` (test_ingest_
integration.py ile AYNI desen) üretilen gerçek bir `ingestion_batch`
kaydına bağlanarak yazılıyor."""

from __future__ import annotations

import os

import psycopg
import pytest

from worker import ingest
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


def _yeni_batch(conn, parser_version: str) -> int:  # type: ignore[no-untyped-def]
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi=f"test_{parser_version}.xlsx",
        icerik=parser_version.encode(),
        donem_tipi="aylik",
        source_period="2098-01",
    )
    return ingest.batch_olustur(conn, source_asset_id, parser_version, "v1")


def _lisans_id(conn, tur: str) -> int:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute("SELECT lisans_id FROM dim_lisans WHERE tur = %s", (tur,))
        return cur.fetchone()[0]


def _kaynak_id(conn, kaynak_adi: str) -> int:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT kaynak_id FROM dim_kaynak WHERE kaynak_adi = %s", (kaynak_adi,)
        )
        return cur.fetchone()[0]


def _il_ekle(
    conn, tarih_id: int, batch_id: int, il_kodu: int, lisans_id: int, mwh: float
) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_uretim_il_geneli
                (tarih_id, il_kodu, lisans_id, uretim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, %s, %s, false)
            """,
            (tarih_id, il_kodu, lisans_id, mwh, batch_id),
        )


def _kaynak_ekle(
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


def test_mutabakat_uyumlu_veri_gecer(conn) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, 209801)
    lisans_id = _lisans_id(conn, "Lisansli")
    ruzgar = _kaynak_id(conn, "Rüzgar")
    hidrolik = _kaynak_id(conn, "Hidrolik")

    il_batch = _yeni_batch(conn, "test-mutabakat-uretim-uyumlu-il")
    kaynak_batch = _yeni_batch(conn, "test-mutabakat-uretim-uyumlu-kaynak")

    # İl toplamı: 700 + 300 = 1000. Kaynak toplamı: 600 (Rüzgar) + 400 (Hidrolik) = 1000.
    # (Kırılımlar FARKLI olabilir — yalnız TOPLAMLAR eşleşmeli, bkz. modül notu.)
    _il_ekle(conn, 209801, il_batch, 26, lisans_id, 700.0)  # Eskişehir
    _il_ekle(conn, 209801, il_batch, 6, lisans_id, 300.0)  # Ankara
    _kaynak_ekle(conn, 209801, kaynak_batch, ruzgar, lisans_id, 600.0)
    _kaynak_ekle(conn, 209801, kaynak_batch, hidrolik, lisans_id, 400.0)

    uyumsuz, detaylar = mutabakat_uretim.mutabakat_kontrol_et(conn)
    bu_periyot = [d for d in detaylar if d["tarih_id"] == 209801]
    assert len(bu_periyot) == 1
    assert bu_periyot[0]["uyumlu"] is True
    assert bu_periyot[0]["il_toplami"] == pytest.approx(1000.0)
    assert bu_periyot[0]["kaynak_toplami"] == pytest.approx(1000.0)
    assert il_batch not in uyumsuz
    assert kaynak_batch not in uyumsuz


def test_mutabakat_uyumsuz_veri_yakalanir(conn) -> None:  # type: ignore[no-untyped-def]
    """Kasıtlı olarak uyumsuz veri üretilir (kullanıcı talimatı) — script'in
    gerçekten yakaladığı, hem detayda hem uyumsuz_batch_idler kümesinde
    kanıtlanır."""
    ingest.dim_tarih_getir_veya_olustur(conn, 209802)
    lisans_id = _lisans_id(conn, "Lisansli")
    ruzgar = _kaynak_id(conn, "Rüzgar")

    il_batch = _yeni_batch(conn, "test-mutabakat-uretim-uyumsuz-il")
    kaynak_batch = _yeni_batch(conn, "test-mutabakat-uretim-uyumsuz-kaynak")

    # İl toplamı: 1000. Kaynak toplamı: 850 — %15 fark, ±%0,5 toleransın
    # ÇOK üstünde (bir parser hatasını simüle ediyor — ör. bir kaynak
    # kolonu hiç okunmamış gibi).
    _il_ekle(conn, 209802, il_batch, 26, lisans_id, 1000.0)
    _kaynak_ekle(conn, 209802, kaynak_batch, ruzgar, lisans_id, 850.0)

    uyumsuz, detaylar = mutabakat_uretim.mutabakat_kontrol_et(conn)
    bu_periyot = [d for d in detaylar if d["tarih_id"] == 209802]
    assert len(bu_periyot) == 1
    assert bu_periyot[0]["uyumlu"] is False
    assert bu_periyot[0]["fark"] == pytest.approx(150.0)
    # HEM il HEM kaynak batch'i bloklanmalı — hangisinin hatalı olduğu
    # script seviyesinde belli değil (bkz. modül notu).
    assert il_batch in uyumsuz
    assert kaynak_batch in uyumsuz


def test_periyot_aktivasyona_uygun_mu_uyumlu(conn) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, 209803)
    lisans_id = _lisans_id(conn, "Lisanssiz")
    ruzgar = _kaynak_id(conn, "Rüzgar")

    il_batch = _yeni_batch(conn, "test-mutabakat-uretim-gate-uyumlu-il")
    kaynak_batch = _yeni_batch(conn, "test-mutabakat-uretim-gate-uyumlu-kaynak")
    _il_ekle(conn, 209803, il_batch, 26, lisans_id, 500.0)
    _kaynak_ekle(conn, 209803, kaynak_batch, ruzgar, lisans_id, 500.0)

    uygun, sebep = mutabakat_uretim.periyot_aktivasyona_uygun_mu(conn, 209803)
    assert uygun is True
    assert sebep == ""


def test_periyot_aktivasyona_uygun_mu_uyumsuz_engeller(conn) -> None:  # type: ignore[no-untyped-def]
    """MADDE 3'ün asıl amacı: uyumsuzsa aktivasyon ENGELLENMELİ (yalnız
    uyarı değil) — bu, `otomatik_onaya_uygun()` ile AYNI (bool, sebep)
    imzasıyla, ADIM 3 madde 4'ün pipeline kodunun çağıracağı gate."""
    ingest.dim_tarih_getir_veya_olustur(conn, 209804)
    lisans_id = _lisans_id(conn, "Lisanssiz")
    ruzgar = _kaynak_id(conn, "Rüzgar")

    il_batch = _yeni_batch(conn, "test-mutabakat-uretim-gate-uyumsuz-il")
    kaynak_batch = _yeni_batch(conn, "test-mutabakat-uretim-gate-uyumsuz-kaynak")
    _il_ekle(conn, 209804, il_batch, 26, lisans_id, 1000.0)
    _kaynak_ekle(conn, 209804, kaynak_batch, ruzgar, lisans_id, 1.0)

    uygun, sebep = mutabakat_uretim.periyot_aktivasyona_uygun_mu(conn, 209804)
    assert uygun is False
    assert "209804" in sebep
