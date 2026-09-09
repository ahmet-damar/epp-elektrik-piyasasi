"""EPP — Faz 2 worker/analytics.py entegrasyon testi.

Golden CSV fixture'larını (worker/tests/golden/input/) yükleyip aktive eder,
sonra analytics.py'nin join+is_active filtresinin doğru çalıştığını, ve
worker/kpi.py'nin beklediği kolon şekli/tiplerini ürettiğini doğrular.
DATABASE_URL yoksa (yerel geliştirme) atlanır.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
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


def _kaynak_geneli_satir_ekle(
    conn,
    tarih_id: int,
    kaynak_adi: str,
    lisans_etiketi: str,
    uretim_mwh: float,
    batch_id: int,
) -> None:  # type: ignore[no-untyped-def]
    """Test yardımcısı: `fact_uretim_kaynak_geneli`'ye tek bir aktif satır
    ekler (ADIM 5 madde 2/3 testleri için ortak)."""
    kaynak_id = ingest.dim_kaynak_id_bul(conn, kaynak_adi)
    lisans_id = ingest.dim_lisans_id_bul(conn, lisans_etiketi)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_uretim_kaynak_geneli
                (tarih_id, kaynak_id, lisans_id, uretim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, %s, %s, true)
            """,
            (tarih_id, kaynak_id, lisans_id, uretim_mwh, batch_id),
        )


def test_uretim_kaynak_geneli_getir_sekil_ve_lisans_gorunumu(conn) -> None:  # type: ignore[no-untyped-def]
    """ADIM 5 madde 2 (2026-09-09) — KPI-02/03/06/07'nin yeni girdisi.
    `uretim_getir()` (il×kaynak) ile AYNI lisans görünüm çevrimi (ASCII ->
    Türkçe) burada da uygulanmalı, ama il/il_kodu/kurulu_guc_mw YOK (bu
    tablo il kırılımsız ve STOK değil, AKIŞ)."""
    tarih_id = 218601
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi="test_kaynak_geneli.xlsx",
        icerik=b"test-kaynak-geneli",
        donem_tipi="aylik",
        source_period="2186-01",
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, "test-kaynak-geneli", "s1")
    _kaynak_geneli_satir_ekle(conn, tarih_id, "Rüzgar", "Lisanslı", 100_000.0, batch_id)
    _kaynak_geneli_satir_ekle(conn, tarih_id, "Güneş", "Lisanssız", 5_000.0, batch_id)

    df = analytics.uretim_kaynak_geneli_getir(conn, tarih_id)

    assert len(df) == 2
    assert set(df.columns) == {"kaynak", "yenilenebilir", "lisans", "uretim_mwh"}
    assert set(df["lisans"]) == {"Lisanslı", "Lisanssız"}  # Türkçe görünüm, ASCII değil
    assert df["uretim_mwh"].sum() == pytest.approx(105_000.0)

    # kpi.py değişiklik gerektirmeden bu şekli tüketebilmeli
    assert kpi.kpi_02_toplam_uretim(df) == pytest.approx(105_000.0)
    lisansli = df.loc[df["lisans"] == "Lisanslı"]
    assert kpi.kpi_02_toplam_uretim(lisansli) == pytest.approx(100_000.0)
    assert kpi.kpi_07_lisanssiz_pay(df) == pytest.approx(
        round(5_000.0 / 105_000.0 * 100, 1)
    )


def test_uretim_kaynak_geneli_getir_donem_bos_ise_veri_yok(conn) -> None:  # type: ignore[no-untyped-def]
    """Hiç yüklenmemiş bir dönem (örn. Word yılları, ADIM 4 öncesi) için
    boş ama doğru kolon şekilli bir DataFrame döner - dashboard'un 'veri
    yok' kapısı (`kaynak_geneli_var`) buna dayanır."""
    tarih_id = 218602
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
    df = analytics.uretim_kaynak_geneli_getir(conn, tarih_id)
    assert df.empty
    assert list(df.columns) == ["kaynak", "yenilenebilir", "lisans", "uretim_mwh"]


def test_kapasite_faktoru_girdisi_lisans_filtresi_olmadan_yanilticidir(conn) -> None:  # type: ignore[no-untyped-def]
    """ADIM 5 madde 3 (2026-09-09) — SESSİZ HATA testi.

    Kurgu: aynı dönemde 1000 MW Lisanslı + 500 MW Lisanssız kurulu güç var
    (fact_uretim, T1+T4 karışık) - Lisanslı üretim (fact_uretim_kaynak_
    geneli, T2) 300.000 MWh, saat=720.

    ÖNCE yanlış (filtresiz) yolu GERÇEKTEN hesaplayıp doğru yoldan
    FARKLI ve DAHA DÜŞÜK çıktığını kanıtlıyoruz (payda gereğinden büyük
    olduğu için) - sonra `kapasite_faktoru_girdisi_getir()`'in doğru
    (Lisanslı-filtreli) sonucu ürettiğini pinliyoruz."""
    tarih_id = 218603
    saat = 720.0
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)

    # --- fact_uretim: payda tarafı (Lisanslı 1000 MW + Lisanssız 500 MW) ---
    uretim_source_asset = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi="test_kapasite_kurulu.xlsx",
        icerik=b"test-kapasite-kurulu",
        donem_tipi="aylik",
        source_period="2186-03",
    )
    uretim_batch_id = ingest.batch_olustur(
        conn, uretim_source_asset, "test-kapasite-kurulu", "s1"
    )
    kaynak_sorgu = "SELECT kaynak_id FROM dim_kaynak WHERE kaynak_adi = 'Rüzgar'"
    for lisans_etiketi, kurulu_mw in (("Lisanslı", 1000.0), ("Lisanssız", 500.0)):
        lisans_id = ingest.dim_lisans_id_bul(conn, lisans_etiketi)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO fact_uretim
                    (il_kodu, tarih_id, kaynak_id, lisans_id, kurulu_guc_mw,
                     ingestion_batch_id, is_active)
                VALUES (26, %s, ({kaynak_sorgu}), %s, %s, %s, true)
                """,  # nosec B608 - kaynak_sorgu sabit metin, kullanıcı girdisi değil
                (tarih_id, lisans_id, kurulu_mw, uretim_batch_id),
            )

    # --- fact_uretim_kaynak_geneli: pay tarafı (yalnız Lisanslı, 300.000 MWh) ---
    kaynak_geneli_source_asset = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi="test_kapasite_uretim.xlsx",
        icerik=b"test-kapasite-uretim",
        donem_tipi="aylik",
        source_period="2186-03",
    )
    kaynak_geneli_batch_id = ingest.batch_olustur(
        conn, kaynak_geneli_source_asset, "test-kapasite-uretim", "s1"
    )
    _kaynak_geneli_satir_ekle(
        conn, tarih_id, "Rüzgar", "Lisanslı", 300_000.0, kaynak_geneli_batch_id
    )

    # --- YANLIŞ (filtresiz) yol: kasıtlı olarak lisans_id'yi payda'da HİÇ
    # filtrelemeden hesapla - gerçek bir geliştiricinin yapabileceği hata. ---
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(SUM(kurulu_guc_mw), 0) FROM fact_uretim "
            "WHERE tarih_id = %s AND is_active",
            (tarih_id,),
        )
        (kurulu_filtresiz,) = cur.fetchone()
    yanlis_df = pd.DataFrame(
        [{"kurulu_guc_mw": float(kurulu_filtresiz), "uretim_mwh": 300_000.0}]
    )
    yanlis_kf = kpi.kpi_05_kapasite_faktoru(yanlis_df, saat)

    # --- DOĞRU (lisans-filtreli) yol: analytics.py'nin merkezi fonksiyonu ---
    girdi = analytics.kapasite_faktoru_girdisi_getir(conn, tarih_id)
    assert girdi["kurulu_guc_mw"].iloc[0] == pytest.approx(1000.0)  # yalnız Lisanslı
    assert girdi["uretim_mwh"].iloc[0] == pytest.approx(300_000.0)
    dogru_kf = kpi.kpi_05_kapasite_faktoru(girdi, saat)

    beklenen_dogru = 300_000.0 / (1000.0 * saat) * 100  # ≈ %41.7
    beklenen_yanlis = 300_000.0 / (1500.0 * saat) * 100  # ≈ %27.8

    assert dogru_kf == pytest.approx(round(beklenen_dogru, 1))
    assert yanlis_kf == pytest.approx(round(beklenen_yanlis, 1))
    # Yakalanması gereken bulgu: filtresiz yol SESSİZCE (hatasız) daha
    # düşük bir kapasite faktörü üretiyor - iki sonuç GERÇEKTEN farklı.
    assert dogru_kf is not None and yanlis_kf is not None
    assert dogru_kf > yanlis_kf
    assert dogru_kf != yanlis_kf


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


def test_kapsam_disi_getir_isaretli_kaydi_dondurur(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    """Aşama 7 (dokumanlar/06_canli_veri_operasyon_gunlugu.md) — dashboard'un
    'bu dönem için kaynakta yok' bilgi kutusunun beslediği fonksiyon."""
    from worker import pipeline

    pipeline.kapsam_disi_isaretle(
        conn,
        tarih_id=202601,
        fact_tablosu="fact_serbest_tuketici",
        sebep="Word kaynağında T13 hiç yok (Karar 1).",
        karar_referansi="Karar 1",
    )

    df = analytics.kapsam_disi_getir(conn, 202601)

    assert len(df) == 1
    assert df.iloc[0]["fact_tablosu"] == "fact_serbest_tuketici"
    assert df.iloc[0]["nitelik"] == "(tumu)"
    assert "Karar 1" in df.iloc[0]["sebep"] or "T13" in df.iloc[0]["sebep"]


def test_kapsam_disi_getir_isaretli_kayit_yoksa_bos_doner(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    df = analytics.kapsam_disi_getir(conn, 202601)
    assert df.empty
    assert list(df.columns) == ["fact_tablosu", "nitelik", "sebep"]


def test_son_batchler_getir_aktif_batch_gorunur(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    """Dashboard 'Sistem Durumu' bölümünün beslediği fonksiyon.

    `aktif_batch` fixture'ı yalnız `ingest.aktivasyon_yap()` çağırıyor
    (fact tablolarını is_active=true yapıyor) — `batch_onayla()`'yı HİÇ
    çağırmıyor, o yüzden `ingestion_batch.status` 'running' kalır
    (`batch_sahiplen()`'in queued->running geçişinden beri hiç
    değişmedi). 'succeeded' beklemek YANLIŞ bir varsayımdı — düzeltildi."""
    df = analytics.son_batchler_getir(conn, limit=20)
    assert (df["batch_id"] == aktif_batch).any()
    satir = df.loc[df["batch_id"] == aktif_batch].iloc[0]
    assert satir["status"] == "running"
    assert satir["source_type"] == "epdk_aylik"


def test_son_job_durumlari_getir_kuyruklanmis_is_gorunur(conn, aktif_batch) -> None:  # type: ignore[no-untyped-def]
    from worker import ingest

    job_id = ingest.is_kaydi_olustur(conn, str(aktif_batch))

    df = analytics.son_job_durumlari_getir(conn, limit=20)

    assert (df["job_id"] == job_id).any()
    satir = df.loc[df["job_id"] == job_id].iloc[0]
    assert satir["status"] == "queued"
    assert satir["correlation_id"] == str(aktif_batch)


# ---------------------------------------------------------------------------
# Faz 3 (hava normalizasyonu): sistem_parametre, hava_getir (UPSERT modeli),
# kpi_11_12_hesapla, yıllık seriler + CAGR.
# ---------------------------------------------------------------------------


def test_sistem_parametre_getir_seed_degerleri(conn) -> None:  # type: ignore[no-untyped-def]
    parametreler = analytics.sistem_parametre_getir(conn)
    assert parametreler["hdd_baz_c"] == 18.0
    assert parametreler["cdd_baz_c"] == 22.0
    assert parametreler["hava_norm_yil"] == 10.0
    assert parametreler["tuketim_norm_yil"] == 5.0


def _bos_batch(conn, parser_version: str) -> int:  # type: ignore[no-untyped-def]
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="acik_meteo",
        dosya_adi=f"test_{parser_version}",
        icerik=parser_version.encode(),
        donem_tipi="aylik",
        source_period="2020-01",
    )
    return ingest.batch_olustur(conn, source_asset_id, parser_version, "v1")


def _hava_upsert(
    conn, il_kodu: int, tarih_id: int, hdd: float, cdd: float, batch_id: int
) -> None:  # type: ignore[no-untyped-def]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_hava_aylik (il_kodu, tarih_id, t_ort, hdd, cdd, ingestion_batch_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (il_kodu, tarih_id) DO UPDATE
                SET hdd = EXCLUDED.hdd, cdd = EXCLUDED.cdd,
                    ingestion_batch_id = EXCLUDED.ingestion_batch_id
            """,
            (il_kodu, tarih_id, 15.0, hdd, cdd, batch_id),
        )


def test_hava_getir_is_active_kolonu_yok_dogrudan_calisir(conn) -> None:  # type: ignore[no-untyped-def]
    """Faz 3 migration 20260819_0009: fact_hava_aylik'ta is_active YOK,
    hava_getir() bunu bekleyip patlamamalı."""
    ingest.dim_tarih_getir_veya_olustur(conn, 202601)
    batch_id = _bos_batch(conn, "test-hava-upsert")
    _hava_upsert(conn, 26, 202601, hdd=250.0, cdd=10.0, batch_id=batch_id)

    df = analytics.hava_getir(conn, 202601, il_kodu=26)
    assert len(df) == 1
    assert df["hdd"].iloc[0] == pytest.approx(250.0)

    # UPSERT: aynı (il,tarih_id) tekrar yazılırsa tek satır kalmalı (çoğulluk yok)
    _hava_upsert(conn, 26, 202601, hdd=260.0, cdd=12.0, batch_id=batch_id)
    df2 = analytics.hava_getir(conn, 202601, il_kodu=26)
    assert len(df2) == 1
    assert df2["hdd"].iloc[0] == pytest.approx(260.0)


def _tuketim_hava_gecmisi_kur(conn) -> int:  # type: ignore[no-untyped-def]
    """il_kodu=26 için 2090-2092 tam yıl (36 ay) + 2093 Ocak (hedef dönem) —
    kpi_11_12_hesapla'nın regresyon (min 12 gözlem) VE hava_norm_yil=3/
    tuketim_norm_yil=2 (testte küçültülmüş pencereler) için yeterli geçmiş.
    Yıllar bilinçli olarak uzak-gelecek sentinel (worker/tests/
    test_job_worker_integration.py'deki tarih_id=209912 deseniyle tutarlı) -
    başka hiçbir testle çakışmaz. hdd yalnız 'ay'a, cdd HEM 'ay' HEM 'yil'e
    bağlı (kolineer DEĞİL) - aksi halde OLS β/γ'yi ayrı ayrı tahmin edemez
    (yalnız toplam etkiyi görür, gerçek katsayılar kurtarılamaz)."""
    il_kodu = 26
    batch_id = _bos_batch(conn, "test-kpi-11-12")
    donemler = [(yil, ay) for yil in (2090, 2091, 2092) for ay in range(1, 13)]
    donemler.append((2093, 1))
    for yil, ay in donemler:
        tarih_id = yil * 100 + ay
        ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
        hdd = max(0.0, 300.0 - (ay - 1) * 20.0)
        cdd = float(ay) * 5.0 + float(yil - 2090) * 20.0
        tuketim_mwh = 5000.0 + 4.0 * hdd + 2.0 * cdd
        _hava_upsert(conn, il_kodu, tarih_id, hdd, cdd, batch_id)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fact_tuketim
                    (il_kodu, tarih_id, grup_id, baglanti, tuketim_mwh, ingestion_batch_id, is_active)
                VALUES (%s, %s, (SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = 'Mesken'),
                        'dagitim', %s, %s, true)
                ON CONFLICT ON CONSTRAINT uq_fact_tuketim_batch DO NOTHING
                """,
                (il_kodu, tarih_id, tuketim_mwh, batch_id),
            )
    return il_kodu


def test_kpi_11_12_hesapla_yeterli_gecmisle_hesaplanir(conn) -> None:  # type: ignore[no-untyped-def]
    il_kodu = _tuketim_hava_gecmisi_kur(conn)
    sonuc = analytics.kpi_11_12_hesapla(
        conn, il_kodu, 209301, hava_norm_yil=3, tuketim_norm_yil=2
    )
    assert sonuc["beta"] is not None
    assert sonuc["beta"] == pytest.approx(4.0, abs=0.01)
    assert sonuc["gamma"] == pytest.approx(2.0, abs=0.01)
    assert sonuc["hava_norm_hdd"] is not None
    assert sonuc["tuketim_norm"] is not None
    assert sonuc["arindirilmis"] is not None
    # gürültüsüz sentetik veri: arındırılmış tüketim, tüketim normuna çok yakın olmalı
    assert sonuc["arindirilmis"] == pytest.approx(sonuc["tuketim_norm"], abs=1.0)
    assert sonuc["kpi_12"] is not None
    assert sonuc["kpi_12"] == pytest.approx(0.0, abs=0.5)


def test_kpi_11_12_hesapla_yetersiz_gecmis_hesaplanamaz(conn) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, 202601)
    batch_id = _bos_batch(conn, "test-kpi-11-12-yetersiz")
    _hava_upsert(conn, 26, 202601, hdd=200.0, cdd=5.0, batch_id=batch_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_tuketim
                (il_kodu, tarih_id, grup_id, baglanti, tuketim_mwh, ingestion_batch_id, is_active)
            VALUES (26, 202601, (SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = 'Mesken'),
                    'dagitim', 6000.0, %s, true)
            """,
            (batch_id,),
        )

    sonuc = analytics.kpi_11_12_hesapla(conn, 26, 202601)
    assert sonuc == {
        "beta": None,
        "gamma": None,
        "hava_norm_hdd": None,
        "hava_norm_cdd": None,
        "tuketim_norm": None,
        "arindirilmis": None,
        "kpi_12": None,
    }


_TUM_GRUPLAR = ("Mesken", "Sanayi", "Tarımsal", "Aydınlatma", "Kamu ve Özel Hizmetler")


def _ulke_geneli_tam_yil_ekle(
    conn, batch_id: int, yil: int, yillik_toplam: float
) -> None:  # type: ignore[no-untyped-def]
    """Test yardımcısı (2026-09-08, Asama 2/C5): fact_tuketim_ulke_geneli'ye
    TAM bir yıl (12 ay × 5 grup = 60 satır) ekler — `yillik_toplam`, 60
    satıra eşit bölünür (yalnız yıl toplamı önemli, aylık/grup kırılımı
    testler için önemsiz)."""
    pay = yillik_toplam / 60
    for ay in range(1, 13):
        tarih_id = yil * 100 + ay
        ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
        with conn.cursor() as cur:
            for grup in _TUM_GRUPLAR:
                cur.execute(
                    """
                    INSERT INTO fact_tuketim_ulke_geneli
                        (tarih_id, grup_id, tuketim_mwh, ingestion_batch_id, is_active)
                    VALUES (%s, (SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = %s),
                            %s, %s, true)
                    """,
                    (tarih_id, grup, pay, batch_id),
                )


def test_yillik_serilerinden_cagr(conn) -> None:  # type: ignore[no-untyped-def]
    """yillik_tuketim_serisi_getir() (KPI-25, 2026-09-08'den beri
    `fact_tuketim_ulke_geneli`'nden okur — bkz. Asama 2/C5 kararı, docstring
    detayı analytics.py'de) TÜM ülke geneli tüketimi toplar. Yıllar
    bilinçli olarak uzak-gelecek sentinel'e (2196/2200) izole edilir, canlı
    veriyle karışmaz."""
    batch_id = _bos_batch(conn, "test-cagr-ulke-geneli")
    for yil, tuketim_carpan in ((2196, 1.0), (2200, 1.4641)):  # %10/yıl, n=4
        _ulke_geneli_tam_yil_ekle(conn, batch_id, yil, 1000.0 * tuketim_carpan)

    seri = analytics.yillik_tuketim_serisi_getir(conn)
    izole_seri = seri[seri["yil"].isin([2196, 2200])]
    cagr = analytics.cagr_seriden_hesapla(izole_seri, "tuketim_mwh")
    assert cagr is not None
    assert cagr == pytest.approx(10.0, abs=0.1)


def test_kpi_25_eksik_yil_seriye_girmez(conn) -> None:  # type: ignore[no-untyped-def]
    """KPI-25 (2026-09-08 düzeltmesi, Asama 2/C5): tam yıl (12 ay) VE 5/5
    grup şartını KARŞILAMAYAN bir yıl seriye HİÇ girmez — 2016-12
    Tarımsal'ın kaynakta hiç yüklenmemesiyle (bkz. master §11.3) AYNI
    davranış deseni, burada bilerek yeniden üretiliyor: sentinel yılın bir
    ayında (Aralık) bir grup (Tarımsal) EKSİK bırakılıyor (59/60 satır)."""
    batch_id = _bos_batch(conn, "test-kpi25-eksik-yil")
    yil_tam, yil_eksik = 2191, 2187

    # Tam yıl - seriye girmeli
    _ulke_geneli_tam_yil_ekle(conn, batch_id, yil_tam, 5000.0)

    # Eksik yıl - Aralık ayında Tarımsal YOK (2016-12'nin taklidi) - 59/60 satır
    for ay in range(1, 13):
        tarih_id = yil_eksik * 100 + ay
        ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
        with conn.cursor() as cur:
            for grup in _TUM_GRUPLAR:
                if ay == 12 and grup == "Tarımsal":
                    continue  # bilerek atlanan satır
                cur.execute(
                    """
                    INSERT INTO fact_tuketim_ulke_geneli
                        (tarih_id, grup_id, tuketim_mwh, ingestion_batch_id, is_active)
                    VALUES (%s, (SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = %s),
                            9999.0, %s, true)
                    """,
                    (tarih_id, grup, batch_id),
                )

    seri = analytics.yillik_tuketim_serisi_getir(conn)
    yillar = set(seri["yil"])
    assert yil_tam in yillar, "Tam yıl (12 ay × 5 grup) seriye girmeli"
    assert yil_eksik not in yillar, "Eksik yıl (59/60 satır) seriye HİÇ girmemeli"

    # Yalnız bu iki sentinel yılın görüldüğü alt-kümeyle CAGR'ı izole test et
    # (canlı DB'de başka tam yıllar da olabilir - o zaman None beklemek
    # yanlış olur, bu yüzden filtrelenmiş alt-kümeyi kullanıyoruz).
    izole_seri = seri[seri["yil"].isin([yil_tam, yil_eksik])]
    assert len(izole_seri) == 1  # yalnız yil_tam kaldı
    assert analytics.cagr_seriden_hesapla(izole_seri, "tuketim_mwh") is None


def test_yillik_tuketim_sanayi_haric_serisi_ve_kpi_27_hesaplanir(conn) -> None:  # type: ignore[no-untyped-def]
    """KPI-27 (Sanayi-hariç tüketim CAGR, YENİ 2026-09-03): Sanayi grubu
    TÜM yıllardan çıkarılır (yıl filtrelenmez, grup filtrelenir - KPI-25'in
    TERSİ stratejisi), yalnız TAM yıllar (12 ay) dahil edilir. Değerler
    canlı DB'de 2023→2024 için doğrulanan +%9,4 büyümeyi TAM FORMÜLLE
    (sabit yazmadan) yeniden üretecek şekilde seçildi: 2094 niteliksel
    ay-başı 100.000 MWh × 12 = 1.200.000 (Sanayi hariç), 2095 ay-başı
    109.400 × 12 = 1.312.800 → (1.312.800/1.200.000)^(1/1) - 1 = %9,4.
    Her iki yıla da BÜYÜK bir Sanayi satırı eklenir - dışlanmazsa toplam
    tamamen farklı (ve testin kendi assertion'ı) çıkar, dışlamanın
    GERÇEKTEN çalıştığını kanıtlar."""
    il_kodu = 26
    batch_id = _bos_batch(conn, "test-kpi27")
    veri = {
        2094: {"ay_basi_mesken": 100_000.0, "sanayi_distractor": 500_000.0},
        2095: {"ay_basi_mesken": 109_400.0, "sanayi_distractor": 999_000_000.0},
    }
    for yil, degerler in veri.items():
        for ay in range(1, 13):
            tarih_id = yil * 100 + ay
            ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fact_tuketim
                        (il_kodu, tarih_id, grup_id, baglanti, tuketim_mwh, ingestion_batch_id, is_active)
                    VALUES (%s, %s, (SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = 'Mesken'),
                            'dagitim', %s, %s, true)
                    """,
                    (il_kodu, tarih_id, degerler["ay_basi_mesken"], batch_id),
                )
        # Sanayi yalnız BİR aya (Ocak) yazılıyor - dışlanmazsa toplamı
        # devasa şekilde bozar, ay sayısını (12) etkilemez.
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fact_tuketim
                    (il_kodu, tarih_id, grup_id, baglanti, tuketim_mwh, ingestion_batch_id, is_active)
                VALUES (%s, %s, (SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = 'Sanayi'),
                        'dagitim', %s, %s, true)
                """,
                (il_kodu, yil * 100 + 1, degerler["sanayi_distractor"], batch_id),
            )

    seri = analytics.yillik_tuketim_sanayi_haric_serisi_getir(conn)
    izole_seri = seri[seri["yil"].isin([2094, 2095])].sort_values("yil")
    assert len(izole_seri) == 2
    assert izole_seri["tuketim_mwh"].iloc[0] == pytest.approx(1_200_000.0)
    assert izole_seri["tuketim_mwh"].iloc[1] == pytest.approx(1_312_800.0)

    kpi_27 = analytics.cagr_seriden_hesapla(izole_seri, "tuketim_mwh")
    assert kpi_27 is not None
    assert kpi_27 == pytest.approx(9.4, abs=0.05)


def test_yillik_yenilenebilir_kurulu_guc_serisi_yil_sonu_alir(conn) -> None:  # type: ignore[no-untyped-def]
    """Kurulu güç stok metriği - aylar TOPLANMAZ, yılın en güncel ayı alınır."""
    il_kodu = 26
    batch_id = _bos_batch(conn, "test-cagr-kurulu-guc")
    kaynak_sorgu = "SELECT kaynak_id FROM dim_kaynak WHERE kaynak_adi = 'Rüzgar'"
    lisans_sorgu = "SELECT lisans_id FROM dim_lisans WHERE tur = 'Lisansli'"
    # kaynak_sorgu/lisans_sorgu sabit metin (kullanıcı girdisi değil), f-string
    # yalnız bu ikisini gömer - değerler (il_kodu vb.) ayrı parametre.
    for tarih_id, kurulu_guc in ((209801, 100.0), (209806, 150.0), (209812, 200.0)):
        ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO fact_uretim
                    (il_kodu, tarih_id, kaynak_id, lisans_id, kurulu_guc_mw, ingestion_batch_id, is_active)
                VALUES (%s, %s, ({kaynak_sorgu}), ({lisans_sorgu}), %s, %s, true)
                """,  # nosec B608
                (il_kodu, tarih_id, kurulu_guc, batch_id),
            )

    seri = analytics.yillik_yenilenebilir_kurulu_guc_serisi_getir(conn)
    satir = seri.loc[seri["yil"] == 2098]
    assert len(satir) == 1
    assert satir["kurulu_guc_mw"].iloc[0] == pytest.approx(
        200.0
    )  # aralık (en son ay), 300 (toplam) DEĞİL


# ---------------------------------------------------------------------------
# Görev 3/4 (2026-09-05): kpi_esik + KPI-11/12 "Türkiye Geneli" (Seçenek A)
# ---------------------------------------------------------------------------


def test_kpi_esikleri_getir_seed_verisi(conn) -> None:  # type: ignore[no-untyped-def]
    """20260905_0001_kpi_esik_seed.sql'in canlıya uygulandığını varsaymaz —
    yalnız BU testin kendi satırını ekleyip okuyarak fonksiyonu doğrular
    (migration'ın kendisi ayrı, canlıda elle doğrulanacak)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO kpi_esik (kpi_id, surum, yesil_alt, sari_alt, yon) "
            "VALUES ('KPI-99-TEST', 'v1', 3.0, 0.0, 'yukselik')"
        )

    esikler = analytics.kpi_esikleri_getir(conn)

    assert "KPI-99-TEST" in esikler
    assert esikler["KPI-99-TEST"] == {
        "yesil_alt": 3.0,
        "sari_alt": 0.0,
        "yon": "yukselik",
    }


def test_kpi_11_12_ulusal_hesapla_tek_il_gecmisiyle(conn) -> None:  # type: ignore[no-untyped-def]
    """Görev 4, Seçenek A: yalnız 1 ilin (26=Eskişehir) yeterli geçmişi
    varken, ulusal toplamın O İLİN kendi sonucuyla BİREBİR eşleşmesi
    gerekir (diğer 80 il veri yokluğundan sessizce dışlanır,
    kapsam_il_sayisi=1 ile GÖRÜNÜR şekilde işaretlenir)."""
    il_kodu = _tuketim_hava_gecmisi_kur(conn)
    tekil = analytics.kpi_11_12_hesapla(
        conn, il_kodu, 209301, hava_norm_yil=3, tuketim_norm_yil=2
    )

    ulusal = analytics.kpi_11_12_ulusal_hesapla(
        conn, 209301, hava_norm_yil=3, tuketim_norm_yil=2
    )

    assert ulusal["kapsam_il_sayisi"] == 1
    assert ulusal["arindirilmis"] == pytest.approx(tekil["arindirilmis"], abs=0.01)
    assert ulusal["kpi_12"] == pytest.approx(tekil["kpi_12"], abs=0.01)


def test_kpi_11_12_ulusal_hesapla_hic_gecmis_yoksa_hesaplanamaz(conn) -> None:  # type: ignore[no-untyped-def]
    """Sentinel bir dönemde HİÇBİR ilin geçmişi yoksa (81 il de dışlanır)
    sahte bir 0 MWh/0.0 YERİNE None ('hesaplanamaz') dönmeli."""
    ingest.dim_tarih_getir_veya_olustur(conn, 209401)

    ulusal = analytics.kpi_11_12_ulusal_hesapla(conn, 209401)

    assert ulusal == {"arindirilmis": None, "kpi_12": None, "kapsam_il_sayisi": 0}
