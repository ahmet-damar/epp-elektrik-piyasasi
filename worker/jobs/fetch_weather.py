"""EPP — Faz 3: Open-Meteo'dan aylık il bazlı hava verisi çeker.

Kaynak: dokumanlar/01_kavramsal_tasarim.md §7 (Faz 3), dokumanlar/02_srs_ozet.md
(OD-1/OD-2, SÜRÜMLEME KURALI), dokumanlar/03_veri_modeli.md (fact_hava_aylik
notu). scheduled-refresh.yml tarafından günlük (04:00 UTC) --incremental ile
çağrılır.

Open-Meteo Historical Weather API (archive-api.open-meteo.com) 81 ili TEK
istekte çeker — çoklu-konum desteği (virgülle ayrılmış lat/lon, dim_il.lat/lon
migration 20260819_0008), 81 ayrı istek yerine. Günlük veri Python tarafında
aylığa (t_ort=ortalama, hdd/cdd=worker/kpi.py ile — aynı degree-day mantığı
tekrar yazılmaz, radyasyon=aylık toplam, ruzgar=aylık ortalama) toplanır.

HDD/CDD **il merkezi** koordinatından hesaplanır — il geneli ağırlıklı
ortalama DEĞİL (bkz. dokumanlar/03_veri_modeli.md notu).

P0-3: source_asset source_kind='api' (source_uri + request_hash) ile açılır.
fact_hava_aylik DİĞER fact tablolarından FARKLI - UPSERT (is_active/batch-
versiyonlama YOK), her değişiklik fact_hava_aylik_log'a JSONB olarak
yazılır (bkz. worker/ingest.py fact_hava_aylik_upsert()).

Kullanım:
    python -m worker.jobs.fetch_weather --incremental   # bir önceki tam ay
    python -m worker.jobs.fetch_weather --tarih-id 202601  # belirli bir dönem (manuel/test)
"""

from __future__ import annotations

import argparse
import os
import sys
from calendar import monthrange
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
import requests

REPO_KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_KOK))

from worker import analytics, ingest, kpi

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
GUNLUK_DEGISKENLER = "temperature_2m_mean,shortwave_radiation_sum,wind_speed_10m_mean"
_ZAMAN_ASIMI_SN = 60


def _hedef_tarih_id(bugun: date | None = None) -> int:
    """--incremental'ın varsayılan hedefi: bir önceki TAM ay (içinde
    bulunulan ay henüz tamamlanmadığından degree-day hesapları eksik olur)."""
    b = bugun or datetime.now(tz=UTC).date()
    if b.month == 1:
        return (b.year - 1) * 100 + 12
    return b.year * 100 + (b.month - 1)


def _ay_araligi(tarih_id: int) -> tuple[str, str]:
    yil, ay = divmod(tarih_id, 100)
    ilk_gun = date(yil, ay, 1)
    son_gun_no = monthrange(yil, ay)[1]
    son_gun = date(yil, ay, son_gun_no)
    return ilk_gun.isoformat(), son_gun.isoformat()


def _il_koordinatlari_getir(conn: psycopg.Connection) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT il_kodu, il_adi, lat, lon FROM dim_il WHERE lat IS NOT NULL AND lon IS NOT NULL ORDER BY il_kodu"
        )
        satirlar = cur.fetchall()
    return pd.DataFrame(satirlar, columns=["il_kodu", "il_adi", "lat", "lon"])


def _open_meteo_cek(
    iller: pd.DataFrame, baslangic: str, bitis: str
) -> list[dict[str, Any]]:
    """81 ili TEK istekte çeker. Dönen liste iller DataFrame'iyle AYNI SIRADA
    (Open-Meteo çoklu-konum yanıtı, istek sırasını korur)."""
    parametreler = {
        "latitude": ",".join(f"{v:.5f}" for v in iller["lat"]),
        "longitude": ",".join(f"{v:.5f}" for v in iller["lon"]),
        "start_date": baslangic,
        "end_date": bitis,
        "daily": GUNLUK_DEGISKENLER,
        "timezone": "auto",
    }
    yanit = requests.get(OPEN_METEO_URL, params=parametreler, timeout=_ZAMAN_ASIMI_SN)
    yanit.raise_for_status()
    veri = yanit.json()
    # Tek il istenirse Open-Meteo tek bir dict döner (liste değil) - burada
    # her zaman 81 il istendiğinden pratikte hep liste gelir, savunma amaçlı.
    return veri if isinstance(veri, list) else [veri]


def _gunluk_degerler(gunluk: dict[str, Any], anahtar: str) -> list[float]:
    return [v for v in gunluk.get("daily", {}).get(anahtar, []) if v is not None]


def _aylik_ozet_cikar(
    gunluk: dict[str, Any], hdd_baz_c: float, cdd_baz_c: float
) -> dict[str, float | None]:
    """Bir ilin bir ayının günlük Open-Meteo yanıtından aylık özet çıkarır.
    hdd/cdd worker/kpi.py'nin ZATEN test edilmiş kpi_23_hdd/kpi_24_cdd'si ile
    hesaplanır (degree-day mantığı burada tekrar yazılmaz)."""
    sicakliklar = _gunluk_degerler(gunluk, "temperature_2m_mean")
    if not sicakliklar:
        return {
            "t_ort": None,
            "hdd": None,
            "cdd": None,
            "radyasyon": None,
            "ruzgar": None,
        }

    gunluk_df = pd.DataFrame({"t_ort": sicakliklar})
    t_ort = float(gunluk_df["t_ort"].mean())
    hdd = kpi.kpi_23_hdd(gunluk_df, hdd_baz_c)
    cdd = kpi.kpi_24_cdd(gunluk_df, cdd_baz_c)

    radyasyon_degerler = _gunluk_degerler(gunluk, "shortwave_radiation_sum")
    radyasyon = float(sum(radyasyon_degerler)) if radyasyon_degerler else None

    ruzgar_degerler = _gunluk_degerler(gunluk, "wind_speed_10m_mean")
    ruzgar = (
        float(sum(ruzgar_degerler) / len(ruzgar_degerler)) if ruzgar_degerler else None
    )

    return {
        "t_ort": t_ort,
        "hdd": hdd,
        "cdd": cdd,
        "radyasyon": radyasyon,
        "ruzgar": ruzgar,
    }


def hava_verisi_cek_ve_yaz(conn: psycopg.Connection, tarih_id: int) -> dict[str, int]:
    """Bir dönem (tarih_id) için 81 ilin hava verisini çeker, UPSERT eder.
    Döner: {'yazilan': N, 'veri_yok': M} (Open-Meteo'nun o il için veri
    döndürmediği durumlar - t_ort/hdd/cdd None kalır, UPSERT yine de yapılır
    ama 'veri_yok' sayacına eklenir)."""
    iller = _il_koordinatlari_getir(conn)
    if iller.empty:
        raise RuntimeError(
            "dim_il'de koordinatı olan hiçbir il yok (migration 20260819_0008 uygulanmamış olabilir)"
        )

    baslangic, bitis = _ay_araligi(tarih_id)
    parametreler = analytics.sistem_parametre_getir(conn)
    hdd_baz_c = parametreler["hdd_baz_c"]
    cdd_baz_c = parametreler["cdd_baz_c"]

    istek_imzasi = (
        f"{OPEN_METEO_URL}?start={baslangic}&end={bitis}&il_sayisi={len(iller)}"
    )
    source_asset_id = ingest.api_kaynak_olustur(
        conn,
        source_type="acik_meteo_aylik",
        source_uri=OPEN_METEO_URL,
        request_hash=ingest.dosya_hash(istek_imzasi.encode()),
        donem_tipi="aylik",
        source_period=f"{tarih_id // 100}-{tarih_id % 100:02d}",
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, "fetch-weather-1", "1")
    ingest.batch_sahiplen(conn, batch_id)
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)

    yanitlar = _open_meteo_cek(iller, baslangic, bitis)
    yazilan = 0
    veri_yok = 0
    for (_, il_satir), gunluk in zip(iller.iterrows(), yanitlar, strict=True):
        olcumler = _aylik_ozet_cikar(gunluk, hdd_baz_c, cdd_baz_c)
        if olcumler["t_ort"] is None:
            veri_yok += 1
        ingest.fact_hava_aylik_upsert(
            conn, int(il_satir["il_kodu"]), tarih_id, olcumler, batch_id
        )
        yazilan += 1

    ingest.batch_durumu_guncelle(
        conn,
        batch_id,
        "succeeded",
        total_row_count=len(iller),
        accepted_row_count=yazilan,
    )
    return {"yazilan": yazilan, "veri_yok": veri_yok}


def main() -> None:
    ap = argparse.ArgumentParser(
        description="EPP Faz 3: Open-Meteo aylık hava verisi çek"
    )
    grup = ap.add_mutually_exclusive_group(required=True)
    grup.add_argument(
        "--incremental",
        action="store_true",
        help="bir önceki tam ayı çek (scheduled-refresh.yml için)",
    )
    grup.add_argument(
        "--tarih-id", type=int, help="belirli bir dönem (YYYYMM) - manuel/test için"
    )
    args = ap.parse_args()

    tarih_id = args.tarih_id if args.tarih_id is not None else _hedef_tarih_id()
    database_url = os.environ["DATABASE_URL"]

    with psycopg.connect(database_url) as conn:
        sonuc = hava_verisi_cek_ve_yaz(conn, tarih_id)
        conn.commit()

    print(
        f"[fetch_weather] tarih_id={tarih_id}: {sonuc['yazilan']} il yazıldı "
        f"({sonuc['veri_yok']} il için Open-Meteo veri döndürmedi)."
    )


if __name__ == "__main__":
    main()
