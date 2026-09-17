"""EPP — `worker/scripts/mutabakat_ulke_geneli.py` KARDİNALİTE kontrolü
testi (2026-09-17, doğrulama turu — kapsam_raporu.md Madde 2/3).

Gerçek 2023-01/02 (Adıyaman/Kahramanmaraş, EPDK'nın kendi mücbir-sebep
notu) senaryosunu KÜÇÜLTÜLMÜŞ/sentetik olarak yeniden üretir: 81 ilden
2'si (79/81) bir grup için eksik, `fact_tuketim_ulke_geneli`'nin DEĞERİ
de AYNI eksik toplamla ayarlanmış (EPDK'nın kendi Genel Toplam satırının
da aynı kaynaktan geldiğini taklit eder) — bu yüzden mevcut DEĞER
kontrolü (`mutabakat_kontrol_et`) bunu UYUMLU görür (fark ~0), YENİ
kardinalite kontrolü (`il_kardinalite_kontrol_et`) İSE yakalar. İKİSİ DE
bu tek testte gösterilir (kullanıcı talimatı: "ikisini de göster")."""

from __future__ import annotations

import os

import psycopg
import pytest

from worker import ingest
from worker.scripts import mutabakat_ulke_geneli as mug

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
        source_period="2097-01",
    )
    return ingest.batch_olustur(conn, source_asset_id, parser_version, "v1")


def _grup_id(conn, grup_adi: str) -> int:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = %s", (grup_adi,)
        )
        return cur.fetchone()[0]


def _tuketim_ekle(
    conn, tarih_id: int, il_kodu: int, grup_id: int, mwh: float, batch_id: int
) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_tuketim
                (il_kodu, tarih_id, grup_id, baglanti, tuketim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, 'dagitim', %s, %s, true)
            """,
            (il_kodu, tarih_id, grup_id, mwh, batch_id),
        )


def _ulke_geneli_ekle(
    conn, tarih_id: int, grup_id: int, mwh: float, batch_id: int
) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_tuketim_ulke_geneli
                (tarih_id, grup_id, tuketim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, %s, true)
            """,
            (tarih_id, grup_id, mwh, batch_id),
        )


# 2023-01/02'deki GERÇEK eksik iller (Adıyaman=2, Kahramanmaraş=46) —
# aynı il_kodu'ları kullanıyoruz, gerçek dim_il satırları zaten mevcut.
_EKSIK_IL_KODLARI = (2, 46)
_TARIH_ID = 209701  # sentetik, izole tarih_id (gerçek 2023-01 DEĞİL)


def test_deger_kontrolu_79_81_ili_yakalamaz_ama_kardinalite_yakalar(conn) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, _TARIH_ID)
    mesken_id = _grup_id(conn, "Mesken")
    tuketim_batch = _yeni_batch(conn, "test-kardinalite-tuketim")
    # mutabakat_kontrol_et()'in varsayılan `parser_version_deseni`si
    # ("word-%-ulke-geneli-v1") ile eşleşmeli, yoksa bu satır sorgusuna
    # hiç girmez.
    ug_batch = _yeni_batch(conn, "word-2097-ulke-geneli-v1")

    # 79/81 il: TÜM iller HARİÇ 2 tanesi (gerçek 2023-01/02 desenini taklit
    # eder) — her il için aynı (deterministik) değer, toplamı hesaplamak
    # kolay olsun diye.
    il_basina_deger = 1000.0
    dahil_edilen_il_sayisi = 0
    with conn.cursor() as cur:
        cur.execute("SELECT il_kodu FROM dim_il ORDER BY il_kodu")
        tum_iller = [r[0] for r in cur.fetchall()]
    for il_kodu in tum_iller:
        if il_kodu in _EKSIK_IL_KODLARI:
            continue
        _tuketim_ekle(
            conn, _TARIH_ID, il_kodu, mesken_id, il_basina_deger, tuketim_batch
        )
        dahil_edilen_il_sayisi += 1
    assert dahil_edilen_il_sayisi == 79

    # fact_tuketim_ulke_geneli'nin DEĞERİ de AYNI 79 ilin toplamıyla
    # ayarlandı — EPDK'nın kendi "Genel Toplam" satırının da aynı eksik
    # kaynaktan geldiğini taklit eder (asıl bulgu: bu yüzden fark ~0).
    ulke_geneli_deger = dahil_edilen_il_sayisi * il_basina_deger
    _ulke_geneli_ekle(conn, _TARIH_ID, mesken_id, ulke_geneli_deger, ug_batch)

    # --- ESKİ (DEĞER) KONTROLÜ: bu ayı UYUMLU görür, YAKALAMAZ ---
    _, detaylar = mug.mutabakat_kontrol_et(conn)
    bu_kayit = next(
        d for d in detaylar if d["tarih_id"] == _TARIH_ID and d["grup"] == "Mesken"
    )
    assert bu_kayit["uyumlu"] is True
    assert bu_kayit["fark"] == pytest.approx(0.0, abs=0.01)

    # --- YENİ (KARDİNALİTE) KONTROLÜ: bu ayı YAKALAR ---
    sapmalar = mug.il_kardinalite_kontrol_et(conn)
    bu_sapma = next(
        (s for s in sapmalar if s["tarih_id"] == _TARIH_ID and s["grup"] == "Mesken"),
        None,
    )
    assert bu_sapma is not None
    assert bu_sapma["il_sayisi"] == 79
    assert bu_sapma["beklenen_il_sayisi"] == 81


def test_kardinalite_kontrolu_tam_81_ilde_sapma_bulmaz(conn) -> None:  # type: ignore[no-untyped-def]
    tarih_id = 209702
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
    mesken_id = _grup_id(conn, "Mesken")
    batch_id = _yeni_batch(conn, "test-kardinalite-tam")
    with conn.cursor() as cur:
        cur.execute("SELECT il_kodu FROM dim_il ORDER BY il_kodu")
        tum_iller = [r[0] for r in cur.fetchall()]
    assert len(tum_iller) == 81
    for il_kodu in tum_iller:
        _tuketim_ekle(conn, tarih_id, il_kodu, mesken_id, 500.0, batch_id)

    sapmalar = mug.il_kardinalite_kontrol_et(conn)
    assert not any(s["tarih_id"] == tarih_id for s in sapmalar)
