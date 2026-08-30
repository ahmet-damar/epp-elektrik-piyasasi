"""EPP — worker/jobs/fetch_weather.py entegrasyon testi (gerçek DB + mocklu
Open-Meteo). Ağ çağrısı worker.jobs.fetch_weather._open_meteo_cek() seviyesinde
mock'lanır — HTTP mekaniği (istek kurulumu, JSON ayrıştırma) burada DEĞİL,
gerçek API'ye karşı throwaway CI dalında ayrıca doğrulanır (bkz. Faz 3 planı
adım 7). DATABASE_URL yoksa (yerel geliştirme) atlanır.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import psycopg
import pytest

from worker.jobs import fetch_weather as fw

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


def _sahte_gunluk_yanit(gun_sayisi: int, t_ort: float) -> dict[str, Any]:
    return {
        "daily": {
            "temperature_2m_mean": [t_ort] * gun_sayisi,
            "shortwave_radiation_sum": [10.0] * gun_sayisi,
            "wind_speed_10m_mean": [3.0] * gun_sayisi,
        }
    }


def test_hava_verisi_cek_ve_yaz_mock_ile_dogru_yazar(conn) -> None:  # type: ignore[no-untyped-def]
    ay_gun_sayisi = 31  # 202601 Ocak
    iller = fw._il_koordinatlari_getir(conn)
    assert len(iller) == 81  # migration 20260819_0008 tüm illeri koordinatladı

    with patch.object(fw, "_open_meteo_cek") as sahte_cek:
        sahte_cek.return_value = [
            _sahte_gunluk_yanit(ay_gun_sayisi, 10.0) for _ in range(len(iller))
        ]
        sonuc = fw.hava_verisi_cek_ve_yaz(conn, 202601)

    assert sonuc["yazilan"] == 81
    assert sonuc["veri_yok"] == 0

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM fact_hava_aylik WHERE tarih_id = %s", (202601,)
        )
        assert cur.fetchone()[0] == 81
        cur.execute(
            "SELECT count(*) FROM fact_hava_aylik_log WHERE tarih_id = %s", (202601,)
        )
        assert cur.fetchone()[0] == 81  # ilk yazım - hepsi yeni log, old_data=NULL
        cur.execute(
            "SELECT old_data FROM fact_hava_aylik_log WHERE tarih_id = %s LIMIT 1",
            (202601,),
        )
        assert cur.fetchone()[0] is None

    # aynı dönem TEKRAR çekilirse UPSERT olmalı (satır sayısı ARTMAMALI),
    # log'a ikinci bir satır (old_data DOLU) eklenmeli - sürüm çakışması yok
    # ama değişiklik geçmişi korunuyor.
    with patch.object(fw, "_open_meteo_cek") as sahte_cek2:
        sahte_cek2.return_value = [
            _sahte_gunluk_yanit(ay_gun_sayisi, 12.0) for _ in range(len(iller))
        ]
        fw.hava_verisi_cek_ve_yaz(conn, 202601)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM fact_hava_aylik WHERE tarih_id = %s", (202601,)
        )
        assert cur.fetchone()[0] == 81  # hâlâ 81 - UPSERT, çoğulluk yok
        cur.execute(
            "SELECT count(*) FROM fact_hava_aylik_log WHERE tarih_id = %s", (202601,)
        )
        assert cur.fetchone()[0] == 162  # iki çağrı x 81 il
        cur.execute(
            "SELECT t_ort FROM fact_hava_aylik WHERE tarih_id = %s LIMIT 1", (202601,)
        )
        assert cur.fetchone()[0] == pytest.approx(12.0)  # güncel değer


def test_hava_verisi_cek_ve_yaz_veri_yok_durumu(conn) -> None:  # type: ignore[no-untyped-def]
    """Open-Meteo bir il için sıcaklık döndürmezse satır yine UPSERT edilir
    (t_ort/hdd/cdd NULL) ama 'veri_yok' sayacına yansır - sessizce atlanmaz."""
    iller = fw._il_koordinatlari_getir(conn)
    with patch.object(fw, "_open_meteo_cek") as sahte_cek:
        yanitlar = [_sahte_gunluk_yanit(28, 5.0) for _ in range(len(iller))]
        yanitlar[0] = {"daily": {"temperature_2m_mean": []}}  # ilk il: veri yok
        sahte_cek.return_value = yanitlar
        sonuc = fw.hava_verisi_cek_ve_yaz(conn, 202602)

    assert sonuc["veri_yok"] == 1
    assert sonuc["yazilan"] == 81
