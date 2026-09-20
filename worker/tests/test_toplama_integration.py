"""EPP — `worker/toplama.py` (toplama katmanı) entegrasyon testi.
(`Claude outputs/PROMPT_TOPLAMA_KATMANI_2026-09-19.md`, 2026-09-19/20)

PROMPT'un açıkça istediği madde 4/5/6/7 testleri + madde 2/3/8 pure
testleri (bkz. `test_toplama_pure.py`). DATABASE_URL yoksa (yerel
geliştirme) atlanır."""

from __future__ import annotations

import os

import psycopg
import pytest

from worker import ingest, toplama

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


def _batch_ac(conn, source_period: str, etiket: str) -> int:  # type: ignore[no-untyped-def]
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi=f"test_toplama_{etiket}.xlsx",
        icerik=f"{etiket}-{source_period}".encode(),
        donem_tipi="aylik",
        source_period=source_period,
    )
    return ingest.batch_olustur(conn, source_asset_id, f"test-toplama-{etiket}", "s1")


def _tuketim_ekle(conn, tarih_id, grup_adi, tuketim_mwh, batch_id, il_kodu=6) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
    grup_id = ingest.dim_grup_id_bul(conn, grup_adi)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_tuketim
                (il_kodu, tarih_id, grup_id, baglanti, tuketim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, 'dagitim', %s, %s, true)
            """,
            (il_kodu, tarih_id, grup_id, tuketim_mwh, batch_id),
        )


def _tuketim_ulke_geneli_ekle(
    conn, tarih_id, grup_adi, tuketim_mwh, batch_id, kumulatif=None
) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
    grup_id = ingest.dim_grup_id_bul(conn, grup_adi)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_tuketim_ulke_geneli
                (tarih_id, grup_id, tuketim_mwh, kumulatif_tuketim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, %s, %s, true)
            """,
            (tarih_id, grup_id, tuketim_mwh, kumulatif, batch_id),
        )


def _uretim_kaynak_geneli_ekle(
    conn, tarih_id, kaynak_adi, lisans_etiketi, uretim_mwh, batch_id
) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
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


def _uretim_il_geneli_ekle(
    conn, tarih_id, lisans_etiketi, uretim_mwh, batch_id, il_kodu=6
) -> None:  # type: ignore[no-untyped-def]
    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)
    lisans_id = ingest.dim_lisans_id_bul(conn, lisans_etiketi)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_uretim_il_geneli
                (tarih_id, il_kodu, lisans_id, uretim_mwh, ingestion_batch_id, is_active)
            VALUES (%s, %s, %s, %s, %s, true)
            """,
            (tarih_id, il_kodu, lisans_id, uretim_mwh, batch_id),
        )


# --- madde 1/3: çözünürlük+aralık bağımsızlığı, çeyrek = TAKVİM çeyreği ---


def test_grain_ay_ceyrek_yil_dogru_toplar(conn) -> None:  # type: ignore[no-untyped-def]
    """Aynı 4 aylık veri (Oca-Nis 2024) 3 farklı grain'de İSTİKRARLI
    toplanmalı: yıl toplamı = çeyrek toplamlarının toplamı = ay
    toplamlarının toplamı."""
    b = _batch_ac(conn, "2024-toplama-grain", "grain")
    degerler = {1: 100.0, 2: 200.0, 3: 300.0, 4: 400.0}
    for ay, deger in degerler.items():
        _tuketim_ulke_geneli_ekle(conn, 202400 + ay, "Mesken", deger, b)

    df_ay = toplama.tuketim_ulke_geneli_toplama_getir(conn, "ay", 202401, 202404)
    df_ceyrek = toplama.tuketim_ulke_geneli_toplama_getir(
        conn, "ceyrek", 202401, 202404
    )
    df_yil = toplama.tuketim_ulke_geneli_toplama_getir(conn, "yil", 202401, 202404)

    assert df_ay["deger"].sum() == pytest.approx(1000.0)
    assert df_yil["deger"].sum() == pytest.approx(1000.0)
    # Q1 (Oca-Mar) = 100+200+300=600, Q2 (Nis) = 400 — TAKVİM çeyreği (madde 3)
    q1 = df_ceyrek.loc[df_ceyrek["donem_anahtari"] == 20241, "deger"].iloc[0]
    q2 = df_ceyrek.loc[df_ceyrek["donem_anahtari"] == 20242, "deger"].iloc[0]
    assert q1 == pytest.approx(600.0)
    assert q2 == pytest.approx(400.0)


def test_ceyrek_mart_q1de_nisan_q2de(conn) -> None:  # type: ignore[no-untyped-def]
    """Madde 3 — çeyrek TAKVİM çeyreği: Mart (ay=3) Q1'de, Nisan (ay=4)
    Q2'de biter — mali yıl/başka bir çeyrek tanımı DEĞİL."""
    b = _batch_ac(conn, "2024-ceyrek-sinir", "ceyrek-sinir")
    _tuketim_ulke_geneli_ekle(conn, 202403, "Mesken", 1.0, b)
    _tuketim_ulke_geneli_ekle(conn, 202404, "Mesken", 1.0, b)
    df = toplama.tuketim_ulke_geneli_toplama_getir(conn, "ceyrek", 202403, 202404)
    anahtarlar = set(df["donem_anahtari"])
    assert anahtarlar == {20241, 20242}  # Mart Q1, Nisan Q2 — AYRI bucket'lar


# --- madde 4: ORAN KURALI (en kritik) ---


def test_oran_kurali_toplayip_sonra_oranla_dogru(conn) -> None:  # type: ignore[no-untyped-def]
    """**KANITLANDI olması gereken test (madde 4, en kritik):** 3 aylık
    yenilenebilir/toplam üretim, ayların KENDİ yüzdesi FARKLI ağırlıkta
    (farklı toplam büyüklüğünde) — "önce topla sonra oranla" ile
    "oranların ortalaması" FARKLI sonuç vermeli, fonksiyon DOĞRU olanı
    (SUM tabanlı) döndürmeli."""
    b = _batch_ac(conn, "2025-oran", "oran")
    # Ocak: 100/200=%50, Şubat: 10/100=%10, Mart: 90/90=%100 (motorin yok)
    _uretim_kaynak_geneli_ekle(conn, 202501, "Rüzgar", "Lisanslı", 100.0, b)
    _uretim_kaynak_geneli_ekle(conn, 202501, "Motorin", "Lisanslı", 100.0, b)
    _uretim_kaynak_geneli_ekle(conn, 202502, "Rüzgar", "Lisanslı", 10.0, b)
    _uretim_kaynak_geneli_ekle(conn, 202502, "Motorin", "Lisanslı", 90.0, b)
    _uretim_kaynak_geneli_ekle(conn, 202503, "Rüzgar", "Lisanslı", 90.0, b)
    # Mart'ta Motorin YOK (madde 7 senaryosuyla aynı fikstür, ayrıca ölçülüyor)

    dogru_pay = (100.0 + 10.0 + 90.0) / (200.0 + 100.0 + 90.0)  # = 0.512820...
    yanlis_ortalama = ((100 / 200) + (10 / 100) + (90 / 90)) / 3  # = 0.533333...
    assert dogru_pay != pytest.approx(yanlis_ortalama)  # senaryo GERÇEKTEN ayırt edici

    df = toplama.uretim_yenilenebilir_payi_getir(conn, "ceyrek", 202501, 202503)
    assert len(df) == 1
    assert df["pay"].iloc[0] == pytest.approx(dogru_pay)
    assert df["pay"].iloc[0] != pytest.approx(yanlis_ortalama)
    assert df["yenilenebilir_mwh"].iloc[0] == pytest.approx(200.0)
    assert df["toplam_mwh"].iloc[0] == pytest.approx(390.0)


# --- madde 5: KAPSAM BAYRAĞI (canlıdaki 4 gerçek boşluk deseni) ---


def test_kapsam_202402_tarzi_tablo_tam_ay_eksik(conn) -> None:  # type: ignore[no-untyped-def]
    """`fact_uretim_il_geneli`nin bir ayı (örn. gerçek 202402) HİÇ
    yüklenmemiş — TABLO düzeyinde kapsam sinyali bunu 2024 yıllık
    toplamda `tam_mi=False` olarak yakalamalı."""
    b = _batch_ac(conn, "2024-il-eksik", "il-eksik")
    for ay in range(1, 13):
        if ay == 2:
            continue  # 202402 hiç yüklenmedi (gerçek canlı örüntü)
        _uretim_il_geneli_ekle(conn, 202400 + ay, "Lisanslı", 50.0, b)

    df = toplama.uretim_il_toplama_getir(conn, "yil", 202401, 202412)
    satir = df.loc[df["lisans_turu"] == "Lisanslı"].iloc[0]
    assert satir["beklenen_donem_sayisi"] == 12
    assert satir["mevcut_donem_sayisi"] == 11
    assert satir["tam_mi"] is False or bool(satir["tam_mi"]) is False


def test_kapsam_2016_12_tarimsal_tarzi_kirilim_eksikligi(conn) -> None:  # type: ignore[no-untyped-def]
    """`fact_tuketim_ulke_geneli`de bir ay TABLO düzeyinde yüklü (diğer
    gruplar var) ama TEK bir grup (örn. gerçek 2016-12 Tarımsal) o ay
    hiç yok — KIRILIM düzeyi kapsam sinyali bunu Tarımsal'ın 2016 yıllık
    toplamında `tam_mi=False` yakalamalı, Mesken'inkini ETKİLEMEMELİ."""
    b = _batch_ac(conn, "2016-tarimsal-eksik", "tarimsal-eksik")
    for ay in range(1, 13):
        _tuketim_ulke_geneli_ekle(conn, 201600 + ay, "Mesken", 10.0, b)
        if ay != 12:
            _tuketim_ulke_geneli_ekle(conn, 201600 + ay, "Tarımsal", 5.0, b)
    # 2016-12 Tarımsal KALICI EKSİK (kasıtlı: yukarıda hiç insert edilmedi)

    df = toplama.tuketim_ulke_geneli_toplama_getir(conn, "yil", 201601, 201612)
    mesken = df.loc[df["grup_adi"] == "Mesken"].iloc[0]
    tarimsal = df.loc[df["grup_adi"] == "Tarımsal"].iloc[0]
    assert bool(mesken["tam_mi"]) is True
    assert mesken["mevcut_donem_sayisi"] == 12
    assert bool(tarimsal["tam_mi"]) is False
    assert tarimsal["mevcut_donem_sayisi"] == 11
    assert tarimsal["deger"] == pytest.approx(55.0)  # 11 ay x 5 — SESSİZCE 60 DEĞİL


def test_kapsam_il_kardinalitesi_2023_deprem_tarzi_eksiklik(conn) -> None:  # type: ignore[no-untyped-def]
    """`fact_tuketim`'in bir ayında (örn. gerçek 2023-01/02) yalnız
    79/81 il var (deprem, Adıyaman+Kahramanmaraş eksik) — diğer aylar
    81/81 — yıllık toplamda `il_sayisi_min` bunu yakalamalı VE
    `tam_mi=False` olmalı (SESSİZCE düşük bir ulusal toplam DÖNMEMELİ)."""
    b = _batch_ac(conn, "2023-il-kardinalite", "il-kardinalite")
    for ay in range(1, 13):
        tarih_id = 202300 + ay
        il_sayisi = 79 if ay in (1, 2) else 81
        for il_kodu in range(1, il_sayisi + 1):
            _tuketim_ekle(conn, tarih_id, "Mesken", 1.0, b, il_kodu=il_kodu)

    df = toplama.tuketim_toplama_getir(conn, "yil", 202301, 202312)
    satir = df.loc[df["grup_adi"] == "Mesken"].iloc[0]
    assert satir["il_sayisi_min"] == 79
    assert bool(satir["tam_mi"]) is False  # 81'den az il -> tam SAYILMAZ


# --- madde 6: KÜMÜLATİF KOLON TUZAĞI ---


def test_kumulatif_kolon_asla_toplanmaz(conn) -> None:  # type: ignore[no-untyped-def]
    """`kumulatif_tuketim_mwh` YANLIŞLIKLA toplanırsa sonuç 3-6 kat şişer
    (ama makul kalır — gözle yakalanmaz, PROMPT'un uyardığı tam da bu).
    Burada kümülatif kolona AYLIK değerden BİLEREK çok daha büyük bir
    değer yazılıp, toplamın yalnız `tuketim_mwh`'den geldiği kanıtlanır."""
    b = _batch_ac(conn, "2026-kumulatif-tuzak", "kumulatif")
    # Ocak: aylik=100, kumulatif=100 (yıl başı, eşit); Şubat: aylik=150,
    # kumulatif=250 (100+150) - kümülatif YANLIŞLIKLA toplansa 100+250=350
    # çıkardı, DOĞRUSU 100+150=250.
    _tuketim_ulke_geneli_ekle(conn, 202601, "Mesken", 100.0, b, kumulatif=100.0)
    _tuketim_ulke_geneli_ekle(conn, 202602, "Mesken", 150.0, b, kumulatif=250.0)

    df = toplama.tuketim_ulke_geneli_toplama_getir(conn, "yil", 202601, 202602)
    satir = df.loc[df["grup_adi"] == "Mesken"].iloc[0]
    assert satir["deger"] == pytest.approx(250.0)  # DOĞRU (aylık toplamı)
    assert satir["deger"] != pytest.approx(
        350.0
    )  # kümülatif yanlışlıkla toplansaydı bu çıkardı
    assert (
        "kumulatif_tuketim_mwh" not in df.columns
    )  # kolon YAPISAL OLARAK expose edilmiyor


# --- madde 7: "kaynak satırı yok" != "veri yok" ---


def test_kaynak_satiri_yok_mevcut_donem_sayisini_dusurmez(conn) -> None:  # type: ignore[no-untyped-def]
    """`fact_uretim_kaynak_geneli`de bir kaynak (örn. gerçek Motorin/
    Nafta) belirli bir ayda EPDK'nın kendi tablosunda hiç listelenmiyor
    — tablo o ay YÜKLÜ (başka bir kaynak var) — bu "üretim yok" demek,
    "veri eksik" değil: kaynağın kendi toplamı SESSİZCE 0 katkı alır AMA
    `mevcut_donem_sayisi`/`tam_mi` ETKİLENMEMELİ (TABLO düzeyi sinyal)."""
    b = _batch_ac(conn, "2025-kaynak-yok", "kaynak-yok")
    for ay in range(1, 4):
        tarih_id = 202500 + ay
        _uretim_kaynak_geneli_ekle(conn, tarih_id, "Rüzgar", "Lisanslı", 10.0, b)
        if ay != 3:
            _uretim_kaynak_geneli_ekle(conn, tarih_id, "Motorin", "Lisanslı", 5.0, b)
    # Mart'ta Motorin YOK ama tablo Mart'ta YÜKLÜ (Rüzgar var)

    df = toplama.uretim_kaynak_toplama_getir(conn, "yil", 202501, 202503)
    motorin = df.loc[df["kaynak_adi"] == "Motorin"].iloc[0]
    ruzgar = df.loc[df["kaynak_adi"] == "Rüzgar"].iloc[0]
    assert motorin["deger"] == pytest.approx(
        10.0
    )  # 2 ay x 5, Mart'tan 0 katkı — SESSİZCE düşük DEĞİL, DOĞRU
    assert (
        motorin["mevcut_donem_sayisi"] == 3
    )  # TABLO 3 ay da yüklü — kaynağın kendi yokluğu SAYILMAZ
    assert bool(motorin["tam_mi"]) is True
    assert bool(ruzgar["tam_mi"]) is True


# --- madde 2: R12 (kayan 12 aylık toplam) ---


def test_r12_kayan_12_aylik_toplam_dogru(conn) -> None:  # type: ignore[no-untyped-def]
    """12 ay boyunca aynı kaynaktan sabit 10 MWh/ay yükle — 202512
    noktasındaki R12 = 120 (tam 12 ay), `tam_mi=True`."""
    b = _batch_ac(conn, "2025-r12-tam", "r12-tam")
    for ay in range(1, 13):
        _uretim_kaynak_geneli_ekle(conn, 202500 + ay, "Rüzgar", "Lisanslı", 10.0, b)

    df = toplama.r12_getir(conn, "uretim_kaynak_geneli", 202512, 202512)
    assert len(df) == 1
    satir = df.iloc[0]
    assert satir["deger_r12"] == pytest.approx(120.0)
    assert satir["mevcut_donem_sayisi"] == 12
    assert bool(satir["tam_mi"]) is True


def test_r12_eksik_ay_varsa_tam_mi_false(conn) -> None:  # type: ignore[no-untyped-def]
    """Aynı senaryo ama Haziran (202506) hiç yüklenmemiş — 202512
    noktasındaki R12 penceresi 11 ay YAKALAR (RANGE, gap'i doğru
    algılar), `mevcut_donem_sayisi=11`, `tam_mi=False` — SESSİZCE eksik
    bir toplam DEĞİL, açıkça işaretli."""
    b = _batch_ac(conn, "2025-r12-eksik", "r12-eksik")
    for ay in range(1, 13):
        if ay == 6:
            continue
        _uretim_kaynak_geneli_ekle(conn, 202500 + ay, "Rüzgar", "Lisanslı", 10.0, b)

    df = toplama.r12_getir(conn, "uretim_kaynak_geneli", 202512, 202512)
    satir = df.iloc[0]
    assert satir["deger_r12"] == pytest.approx(110.0)
    assert satir["mevcut_donem_sayisi"] == 11
    assert bool(satir["tam_mi"]) is False
