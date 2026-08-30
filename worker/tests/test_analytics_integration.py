"""EPP — Faz 2 worker/analytics.py entegrasyon testi.

Golden CSV fixture'larını (worker/tests/golden/input/) yükleyip aktive eder,
sonra analytics.py'nin join+is_active filtresinin doğru çalıştığını, ve
worker/kpi.py'nin beklediği kolon şekli/tiplerini ürettiğini doğrular.
DATABASE_URL yoksa (yerel geliştirme) atlanır.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from worker import analytics, ingest, kpi

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
        connection.rollback()


@pytest.fixture
def aktif_batch(conn) -> int:  # type: ignore[no-untyped-def]
    """tuketim/uretim/abone golden CSV'lerini yükleyip aktive eden ortak bir
    batch hazırlar - her analytics testinin tekrar tekrar kurmasına gerek kalmaz."""
    ingest.dim_tarih_getir_veya_olustur(conn, 202601)
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi="test_analytics.xlsx",
        icerik=b"test-analytics",
        donem_tipi="aylik",
        source_period="2026-01",
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, "test-analytics", "s1")
    ingest.batch_sahiplen(conn, batch_id)

    tuketim = kpi.yukle_tuketim(GOLDEN_INPUT / "tuketim.csv").kabul
    uretim = kpi.yukle_uretim(GOLDEN_INPUT / "uretim.csv").kabul
    abone = kpi.yukle_abone(GOLDEN_INPUT / "abone.csv").kabul
    ingest.fact_tuketim_yukle(conn, tuketim, batch_id)
    ingest.fact_uretim_yukle(conn, uretim, batch_id)
    ingest.fact_abone_yukle(conn, abone, batch_id)

    for tablo in ("fact_tuketim", "fact_uretim", "fact_abone"):
        ingest.aktivasyon_yap(conn, tablo, batch_id)
    return batch_id


def test_uretim_getir_sekil_ve_lisans_gorunumu(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    """dim_lisans.tur DB'de ASCII ('Lisansli') saklanır - uretim_getir()'in
    bunu görünüm formuna ('Lisanslı') çevirdiği, kpi_07_lisanssiz_pay()'ın
    beklediği değerle eşleştiği doğrulanır."""
    df = analytics.uretim_getir(conn, 202601)
    assert len(df) == 5
    assert set(df.columns) == {
        "il",
        "il_kodu",
        "kaynak",
        "yenilenebilir",
        "lisans",
        "kurulu_guc_mw",
        "uretim_mwh",
    }
    assert (df["lisans"] == "Lisanslı").all()  # Türkçe görünüm formu, ASCII değil
    assert (df["il"] == "Eskişehir").all()
    assert df["uretim_mwh"].sum() == pytest.approx(880000.0)
    assert df["kurulu_guc_mw"].sum() == pytest.approx(2000.0)

    # kpi.py fonksiyonları değişiklik gerektirmeden bu şekli tüketebilmeli
    assert kpi.kpi_02_toplam_uretim(df) == pytest.approx(880000.0)
    assert kpi.kpi_07_lisanssiz_pay(df) == pytest.approx(0.0)  # hepsi lisanslı


def test_tuketim_getir_ve_p0_2(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    df = analytics.tuketim_getir(conn, 202601)
    assert len(df) == 6
    assert kpi.kpi_08_toplam_tuketim(df) == pytest.approx(445000.0)

    p0_2 = kpi.p0_2_sanayi(df)
    assert p0_2["sanayi_iletim"] == pytest.approx(150000.0)
    assert p0_2["sanayi_dagitim"] == pytest.approx(90000.0)


def test_abone_getir_ve_kpi_10(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    tuketim = analytics.tuketim_getir(conn, 202601)
    abone = analytics.abone_getir(conn, 202601)
    assert len(abone) == 5
    abone_basi = kpi.kpi_10_abone_basi(tuketim, abone, "Mesken")
    assert abone_basi == pytest.approx(120000.0 / 250000.0)


def test_il_kodu_filtresi(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    """il_kodu=26 (Eskişehir) veriyi döndürür; başka bir il için boş döner."""
    dolu = analytics.tuketim_getir(conn, 202601, il_kodu=26)
    assert len(dolu) == 6
    bos = analytics.tuketim_getir(conn, 202601, il_kodu=6)  # Ankara - veri yok
    assert bos.empty
    assert list(bos.columns) == ["il", "il_kodu", "grup", "baglanti", "tuketim_mwh"]


def test_hava_getir_bos_ama_dogru_kolonlarla_doner(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    """fact_hava_aylik Faz 2'de hiç doldurulmadı (Faz 3) - boş dönmeli, ama
    kolon şekli dashboard.py'nin 'veri yok' kontrolü için tutarlı olmalı."""
    df = analytics.hava_getir(conn, 202601)
    assert df.empty
    assert list(df.columns) == [
        "il",
        "il_kodu",
        "t_ort",
        "hdd",
        "cdd",
        "radyasyon",
        "ruzgar",
    ]


def test_donemler_getir_yalniz_aktif_donemleri_dondurur(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    df = analytics.donemler_getir(conn)
    assert (df["tarih_id"] == 202601).any()
    satir = df.loc[df["tarih_id"] == 202601].iloc[0]
    assert satir["yil_ay"] == "2026-01"


def test_iller_getir_81_il(conn) -> None:  # type: ignore[no-untyped-def]
    df = analytics.iller_getir(conn)
    assert len(df) == 81
    assert "Eskişehir" in df["il_adi"].tolist()
