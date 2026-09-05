"""EPP — Ingestion pipeline: source_asset → ingestion_batch → fact_*
(Faz 0, senkron) + job_status (Faz 1, asenkron kuyruk).

Kaynak: dokumanlar/01_kavramsal_tasarim.md (§4 Uçtan Uca Veri Akışı),
dokumanlar/02_srs_ozet.md (P0-2..P0-5), dokumanlar/03_veri_modeli.md.

Akış: dosya yüklenir → source_asset (SHA-256 hash) → ingestion_batch (queued/
running) → doğrulanmış satırlar fact_* tablosuna is_active=false yazılır →
aktivasyon_yap() TEK transaction içinde eski aktif sürümü pasifler ve yeni
batch'i aktifler (P0-4). Tüm sorgular parametrelidir (SQL injection'a karşı).

Faz 1: job_status (db/schema.sql'de tanımlı ama Faz 0'da hiç kullanılmayan
tablo) worker/job_worker.py'nin harici bir broker (Redis/Celery/RabbitMQ)
OLMADAN, salt Postgres polling ile çalışan asenkron kuyruğunu destekler —
bkz. is_sahiplen()/is_basarili()/is_basarisiz() ve worker/pipeline.py'nin
epdk_isi_kuyruga_al(). job_status = iş YÜRÜTME/retry/kilit takibi (altyapı);
ingestion_batch.status = veri YAŞAM DÖNGÜSÜ (iş) takibi — ayrı ama
correlation_id (=str(batch_id)) ile bağlı. Tek iş türü (EPDK dosya işleme)
olduğundan job_status'a henüz bir job_type kolonu eklenmedi (YAGNI) —
ikinci bir iş türü (ör. Faz 3 hava/matview) gelince ayrı migration'la eklenir.

NOT: Bu modül gerçek bir PostgreSQL'e karşı yalnızca CI'nin 'integration'
job'ında (worker/tests/test_ingest_integration.py, DATABASE_URL ile) test
edilir; yerel geliştirme ortamında çalışan bir Postgres yoktu.
"""

from __future__ import annotations

import calendar
import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from psycopg import Connection

AY_ADLARI = [
    "",
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
]

_LISANS_KODU = {"Lisanslı": "Lisansli", "Lisanssız": "Lisanssiz"}


def dosya_hash(icerik: bytes) -> str:
    """Kaynak: dokumanlar/01 §4 — 'Kullanıcı EPDK dosyası yükler → SHA-256 hash'."""
    return hashlib.sha256(icerik).hexdigest()


def tarih_bilesenleri(tarih_id: int) -> dict[str, Any]:
    """tarih_id = YYYYMM (aylık) veya YYYY00 (yıllık, FR-15)."""
    yil, ay = divmod(tarih_id, 100)
    donem_tipi = "yillik" if ay == 0 else "aylik"
    ceyrek = 0 if ay == 0 else (ay - 1) // 3 + 1
    ay_adi = None if ay == 0 else AY_ADLARI[ay]
    yil_ay = str(yil) if ay == 0 else f"{yil}-{ay:02d}"
    return {
        "yil": yil,
        "ay": ay,
        "ceyrek": ceyrek,
        "ay_adi": ay_adi,
        "yil_ay": yil_ay,
        "donem_tipi": donem_tipi,
    }


def tarih_id_from_source_period(source_period: str, donem_tipi: str) -> int:
    """tarih_bilesenleri()'nin (tarih_id -> bilesen) tersi: source_period
    ('YYYY-MM' aylık / 'YYYY' yıllık) -> tarih_id (YYYYMM/YYYY00). Faz 1'de
    worker/job_worker.py, source_asset'te SAKLANMAYAN tarih_id'yi (yalnız
    source_period+donem_tipi saklanır) buradan yeniden türetir — ayrı bir
    DB alanı eklemeden."""
    if donem_tipi == "yillik":
        return int(source_period) * 100
    yil_str, ay_str = source_period.split("-")
    return int(yil_str) * 100 + int(ay_str)


def donem_saat_sayisi(tarih_id: int) -> float:
    """worker/kpi.py kpi_05_kapasite_faktoru()'nün 'saat' parametresi için:
    tarih_id'nin kapsadığı dönemdeki toplam saat sayısı (aylık: o ayın gün
    sayısı*24; yıllık: 365/366 gün*24). Faz 2 dashboard'unda kullanılır."""
    bilesen = tarih_bilesenleri(tarih_id)
    yil, ay = bilesen["yil"], bilesen["ay"]
    if ay == 0:
        gun_sayisi = 366 if calendar.isleap(yil) else 365
    else:
        gun_sayisi = calendar.monthrange(yil, ay)[1]
    return gun_sayisi * 24.0


def dim_tarih_getir_veya_olustur(conn: Connection, tarih_id: int) -> int:
    bilesen = tarih_bilesenleri(tarih_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_tarih (tarih_id, yil, ay, ceyrek, ay_adi, yil_ay, donem_tipi)
            VALUES (%(tarih_id)s, %(yil)s, %(ay)s, %(ceyrek)s, %(ay_adi)s, %(yil_ay)s, %(donem_tipi)s)
            ON CONFLICT (tarih_id) DO UPDATE SET tarih_id = EXCLUDED.tarih_id
            RETURNING tarih_id
            """,
            {"tarih_id": tarih_id, **bilesen},
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


def dim_grup_id_bul(conn: Connection, grup_adi: str) -> int:
    """dim_tuketici_grubu önceden seed edilmiştir (bkz. migrations/..._seed_dimensions.sql)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = %s", (grup_adi,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(
                f"Bilinmeyen tüketici grubu (dim_tuketici_grubu'nda yok): {grup_adi!r}"
            )
        return int(row[0])


def dim_kaynak_id_bul(conn: Connection, kaynak_adi: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT kaynak_id FROM dim_kaynak WHERE kaynak_adi = %s", (kaynak_adi,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(
                f"Bilinmeyen kaynak türü (dim_kaynak'ta yok): {kaynak_adi!r}"
            )
        return int(row[0])


def dim_lisans_id_bul(conn: Connection, lisans_etiketi: str) -> int:
    tur = _LISANS_KODU.get(lisans_etiketi, lisans_etiketi)
    with conn.cursor() as cur:
        cur.execute("SELECT lisans_id FROM dim_lisans WHERE tur = %s", (tur,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(
                f"Bilinmeyen lisans türü (dim_lisans'ta yok): {lisans_etiketi!r}"
            )
        return int(row[0])


def kaynak_asset_olustur(
    conn: Connection,
    *,
    source_type: str,
    dosya_adi: str,
    icerik: bytes,
    donem_tipi: str,
    source_period: str,
    uploaded_by: str | None = None,
    storage_path: str | None = None,
) -> int:
    """P0-3: source_kind='file' → file_name + file_hash zorunlu. storage_path
    Faz 1'de epdk_isi_kuyruga_al() tarafından set edilir (worker/job_worker.py
    dosyayı buradan okur); senkron (Faz 0) yolda None kalır."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO source_asset
                (source_type, source_kind, source_period, donem_tipi, file_name, file_hash, uploaded_by, storage_path)
            VALUES (%s, 'file', %s, %s, %s, %s, %s, %s)
            RETURNING source_asset_id
            """,
            (
                source_type,
                source_period,
                donem_tipi,
                dosya_adi,
                dosya_hash(icerik),
                uploaded_by,
                storage_path,
            ),
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


def api_kaynak_olustur(
    conn: Connection,
    *,
    source_type: str,
    source_uri: str,
    request_hash: str,
    donem_tipi: str,
    source_period: str,
    uploaded_by: str | None = None,
) -> int:
    """P0-3: source_kind='api' → source_uri + request_hash zorunlu (dosya
    kind'inin file_name/file_hash'ine karşılık gelir). Faz 3'te
    worker/jobs/fetch_weather.py (Open-Meteo) tarafından kullanılır —
    request_hash tipik olarak dosya_hash(istek_imzası.encode())."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO source_asset
                (source_type, source_kind, source_period, donem_tipi, source_uri, request_hash, uploaded_by)
            VALUES (%s, 'api', %s, %s, %s, %s, %s)
            RETURNING source_asset_id
            """,
            (
                source_type,
                source_period,
                donem_tipi,
                source_uri,
                request_hash,
                uploaded_by,
            ),
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


def batch_olustur(
    conn: Connection, source_asset_id: int, parser_version: str, schema_version: str
) -> int:
    """P0-5: (source_asset_id, parser_version, schema_version) tekil; varsa mevcut
    batch_id döner. Adım 2 (dokumanlar/01 §4): 'queued' ile açılır — 'running'e
    geçiş, worker'ın adım 3'te ATOMİK sahiplenmesiyle olur, bkz. batch_sahiplen()."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion_batch (source_asset_id, parser_version, schema_version, status)
            VALUES (%s, %s, %s, 'queued')
            ON CONFLICT (source_asset_id, parser_version, schema_version)
            DO UPDATE SET status = ingestion_batch.status
            RETURNING batch_id
            """,
            (source_asset_id, parser_version, schema_version),
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


def batch_sahiplen(conn: Connection, batch_id: int) -> bool:
    """Adım 3 (dokumanlar/01 §4): worker batch'i ATOMİK sahiplenir (queued ->
    running). Tek bir UPDATE...WHERE status='queued' cümlesi olduğundan aynı
    anda birden fazla worker aynı batch'i sahiplenmeye çalışırsa satır kilidi
    sayesinde yalnız biri rowcount=1 alır (True döner); diğerleri False alır."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ingestion_batch SET status = 'running' WHERE batch_id = %s AND status = 'queued'",
            (batch_id,),
        )
        return cur.rowcount == 1


def batch_durumu_guncelle(
    conn: Connection,
    batch_id: int,
    status: str,
    *,
    total_row_count: int | None = None,
    accepted_row_count: int | None = None,
    rejected_row_count: int | None = None,
    error_summary: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingestion_batch
            SET status = %s,
                total_row_count = COALESCE(%s, total_row_count),
                accepted_row_count = COALESCE(%s, accepted_row_count),
                rejected_row_count = COALESCE(%s, rejected_row_count),
                error_summary = COALESCE(%s, error_summary)
            WHERE batch_id = %s
            """,
            (
                status,
                total_row_count,
                accepted_row_count,
                rejected_row_count,
                error_summary,
                batch_id,
            ),
        )


def _sayisal_temiz(deger: object) -> float | None:
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        return None
    return float(deger)  # type: ignore[arg-type]


def yil_ici_onceki_tuketim_toplami(
    conn: Connection, yil: int, tarih_id: int
) -> pd.DataFrame:
    """T11 (tablo11_tuketim_oku) KÜMÜLATİF veri döndürür (yıl başından bu aya
    kadar) - EPDK'nın kendi başlığı 'Kümülatif Faturalanan Elektrik
    Tüketimi...' der (2026-08-31'de bulundu, bkz. dokumanlar/06_canli_veri_
    operasyon_gunlugu.md). Bu ayın AYLIK değerini türetmek için, aynı yıl
    içinde bu aydan ÖNCEKİ aktif fact_tuketim satırlarının (il_kodu, grup,
    baglanti) bazında toplamını döner - çağıran bunu kümülatif değerden
    çıkarır. Yılın ilk ayı için (öncesinde hiç ay yoksa) boş DataFrame döner
    (referans toplamı 0 sayılır - kümülatif=aylık, mevcut Ocak davranışıyla
    tutarlı)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ft.il_kodu, g.grup_adi, ft.baglanti, sum(ft.tuketim_mwh) AS onceki_toplam
            FROM fact_tuketim ft
            JOIN dim_tuketici_grubu g ON g.grup_id = ft.grup_id
            WHERE ft.is_active = true AND ft.tarih_id >= %s AND ft.tarih_id < %s
            GROUP BY ft.il_kodu, g.grup_adi, ft.baglanti
            """,
            (yil * 100, tarih_id),
        )
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["il_kodu", "grup", "baglanti", "onceki_toplam"])
    # psycopg, Postgres NUMERIC toplamini Decimal olarak dondurur - T11'in
    # (float) kumulatif degerinden cikarilirken tip uyusmazligi (TypeError)
    # yaratir, float'a cevir.
    if not df.empty:
        df["onceki_toplam"] = df["onceki_toplam"].astype(float)
    return df


def fact_tuketim_yukle(
    conn: Connection, df: pd.DataFrame, batch_id: int
) -> tuple[int, int]:
    """Kabul edilen tüketim satırlarını is_active=false yazar. (yuklenen, atlanan_null) döner."""
    yuklenen = 0
    atlanan = 0
    with conn.cursor() as cur:
        for satir in df.itertuples(index=False):
            deger = _sayisal_temiz(satir.tuketim_mwh)
            if deger is None:  # fact_tuketim.tuketim_mwh NOT NULL
                atlanan += 1
                continue
            grup_id = dim_grup_id_bul(conn, satir.grup)
            cur.execute(
                """
                INSERT INTO fact_tuketim
                    (il_kodu, tarih_id, grup_id, baglanti, tuketim_mwh, ingestion_batch_id, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, false)
                ON CONFLICT ON CONSTRAINT uq_fact_tuketim_batch DO NOTHING
                """,
                (
                    satir.il_kodu,
                    satir.tarih_id,
                    grup_id,
                    satir.baglanti,
                    deger,
                    batch_id,
                ),
            )
            yuklenen += 1
    return yuklenen, atlanan


def fact_tuketim_ulke_geneli_yukle(
    conn: Connection, df: pd.DataFrame, batch_id: int
) -> tuple[int, int]:
    """fact_tuketim_yukle() ile AYNI desen — tek fark: il_kodu/baglanti
    YOK (grain: tarih_id × grup_id yalnız), çünkü kaynak (T11 tablosunun
    kendi Genel Toplam satırı, bkz. worker/scripts/word_ortak.py:
    genel_toplam_satirini_oku()) zaten il kırılımsız. is_active=false
    yazar (aktivasyon adımı P0-4/P0-5 ile AYNI, bkz. aktivasyon_yap())."""
    yuklenen = 0
    atlanan = 0
    with conn.cursor() as cur:
        for satir in df.itertuples(index=False):
            deger = _sayisal_temiz(satir.tuketim_mwh)
            if deger is None:  # fact_tuketim_ulke_geneli.tuketim_mwh NOT NULL
                atlanan += 1
                continue
            grup_id = dim_grup_id_bul(conn, satir.grup)
            cur.execute(
                """
                INSERT INTO fact_tuketim_ulke_geneli
                    (tarih_id, grup_id, tuketim_mwh, ingestion_batch_id, is_active)
                VALUES (%s, %s, %s, %s, false)
                ON CONFLICT ON CONSTRAINT uq_fact_tuketim_ulke_geneli_batch DO NOTHING
                """,
                (satir.tarih_id, grup_id, deger, batch_id),
            )
            yuklenen += 1
    return yuklenen, atlanan


def fact_uretim_yukle(
    conn: Connection, df: pd.DataFrame, batch_id: int
) -> tuple[int, int]:
    """kurulu_guc_mw zorunlu (NOT NULL). uretim_mwh il×kaynak grain'inde aylık
    EPDK raporunda hiç mevcut değil (bkz. worker/parser.py modül notu) — bu
    yüzden nullable'dır (migration 20260819_0005); `df`'te sütun bile
    yoksa (T1/T4'ün ham çıktısı) NULL olarak yazılır."""
    yuklenen = 0
    atlanan = 0
    with conn.cursor() as cur:
        for satir in df.itertuples(index=False):
            kurulu = _sayisal_temiz(satir.kurulu_guc_mw)
            if kurulu is None:  # fact_uretim.kurulu_guc_mw NOT NULL
                atlanan += 1
                continue
            uretim = _sayisal_temiz(getattr(satir, "uretim_mwh", None))
            kaynak_id = dim_kaynak_id_bul(conn, satir.kaynak)
            lisans_id = dim_lisans_id_bul(conn, getattr(satir, "lisans", "Lisanslı"))
            cur.execute(
                """
                INSERT INTO fact_uretim
                    (il_kodu, tarih_id, kaynak_id, lisans_id, kurulu_guc_mw, uretim_mwh,
                     ingestion_batch_id, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, false)
                ON CONFLICT ON CONSTRAINT uq_fact_uretim_batch DO NOTHING
                """,
                (
                    satir.il_kodu,
                    satir.tarih_id,
                    kaynak_id,
                    lisans_id,
                    kurulu,
                    uretim,
                    batch_id,
                ),
            )
            yuklenen += 1
    return yuklenen, atlanan


def fact_abone_yukle(
    conn: Connection, df: pd.DataFrame, batch_id: int
) -> tuple[int, int]:
    yuklenen = 0
    atlanan = 0
    with conn.cursor() as cur:
        for satir in df.itertuples(index=False):
            deger = _sayisal_temiz(satir.abone_sayisi)
            if deger is None:
                atlanan += 1
                continue
            grup_id = dim_grup_id_bul(conn, satir.grup)
            cur.execute(
                """
                INSERT INTO fact_abone (il_kodu, tarih_id, grup_id, abone_sayisi, ingestion_batch_id, is_active)
                VALUES (%s, %s, %s, %s, %s, false)
                ON CONFLICT ON CONSTRAINT uq_fact_abone_batch DO NOTHING
                """,
                (satir.il_kodu, satir.tarih_id, grup_id, int(deger), batch_id),
            )
            yuklenen += 1
    return yuklenen, atlanan


def fact_serbest_tuketici_yukle(
    conn: Connection, df: pd.DataFrame, batch_id: int
) -> tuple[int, int]:
    """tuketim_mwh VE tuketici_sayisi ikisi de NOT NULL (migration 20260819_0006);
    biri eksikse satır atlanır. `atlanan` sayısı ingestion_batch.rejected_row_count'a
    yansıtılmak üzere döner — bkz. batch_durumu_guncelle()."""
    yuklenen = 0
    atlanan = 0
    with conn.cursor() as cur:
        for satir in df.itertuples(index=False):
            tuketim = _sayisal_temiz(satir.tuketim_mwh)
            sayisi = _sayisal_temiz(satir.tuketici_sayisi)
            if tuketim is None or sayisi is None:
                atlanan += 1
                continue
            grup_id = dim_grup_id_bul(conn, satir.grup)
            cur.execute(
                """
                INSERT INTO fact_serbest_tuketici
                    (il_kodu, tarih_id, tur, grup_id, tuketim_mwh, tuketici_sayisi,
                     ingestion_batch_id, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, false)
                ON CONFLICT ON CONSTRAINT uq_fact_serbest_tuketici_batch DO NOTHING
                """,
                (
                    satir.il_kodu,
                    satir.tarih_id,
                    satir.tur,
                    grup_id,
                    tuketim,
                    int(sayisi),
                    batch_id,
                ),
            )
            yuklenen += 1
    return yuklenen, atlanan


def fact_hava_aylik_upsert(
    conn: Connection,
    il_kodu: int,
    tarih_id: int,
    olcumler: dict[str, float | None],
    batch_id: int,
) -> None:
    """fact_hava_aylik DİĞER fact_*_yukle() fonksiyonlarından FARKLI çalışır
    (bkz. migration 20260819_0009 ve worker/pipeline.py'nin aksine burada
    is_active/batch-versiyonlama YOK): (il_kodu, tarih_id) üzerine gerçek
    UPSERT yapar (ON CONFLICT DO UPDATE), TEK güncel satır kalır. Her
    çağrıdan önceki değer (varsa) + yeni değer fact_hava_aylik_log'a
    append-only JSONB snapshot olarak yazılır (SÜRÜMLEME KURALI).
    olcumler anahtarları: t_ort, hdd, cdd, radyasyon, ruzgar."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT t_ort, hdd, cdd, radyasyon, ruzgar FROM fact_hava_aylik WHERE il_kodu = %s AND tarih_id = %s",
            (il_kodu, tarih_id),
        )
        eski = cur.fetchone()
        eski_json = (
            json.dumps(
                {
                    "t_ort": _decimal_to_float(eski[0]),
                    "hdd": _decimal_to_float(eski[1]),
                    "cdd": _decimal_to_float(eski[2]),
                    "radyasyon": _decimal_to_float(eski[3]),
                    "ruzgar": _decimal_to_float(eski[4]),
                }
            )
            if eski is not None
            else None
        )

        cur.execute(
            """
            INSERT INTO fact_hava_aylik
                (il_kodu, tarih_id, t_ort, hdd, cdd, radyasyon, ruzgar, ingestion_batch_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (il_kodu, tarih_id) DO UPDATE SET
                t_ort = EXCLUDED.t_ort, hdd = EXCLUDED.hdd, cdd = EXCLUDED.cdd,
                radyasyon = EXCLUDED.radyasyon, ruzgar = EXCLUDED.ruzgar,
                ingestion_batch_id = EXCLUDED.ingestion_batch_id
            """,
            (
                il_kodu,
                tarih_id,
                olcumler.get("t_ort"),
                olcumler.get("hdd"),
                olcumler.get("cdd"),
                olcumler.get("radyasyon"),
                olcumler.get("ruzgar"),
                batch_id,
            ),
        )
        cur.execute(
            """
            INSERT INTO fact_hava_aylik_log (il_kodu, tarih_id, old_data, new_data, ingestion_batch_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (il_kodu, tarih_id, eski_json, json.dumps(olcumler), batch_id),
        )


def _decimal_to_float(deger: object) -> float | None:
    return None if deger is None else float(deger)  # type: ignore[arg-type]


_DOGAL_ANAHTAR = {
    "fact_tuketim": ["il_kodu", "tarih_id", "grup_id", "baglanti"],
    "fact_uretim": ["il_kodu", "tarih_id", "kaynak_id", "lisans_id"],
    "fact_abone": ["il_kodu", "tarih_id", "grup_id"],
    "fact_serbest_tuketici": ["il_kodu", "tarih_id", "tur", "grup_id"],
    "fact_tuketim_ulke_geneli": ["tarih_id", "grup_id"],
}


def audit_log_yaz(
    conn: Connection,
    *,
    table_name: str,
    record_id: int | None,
    action_type: str,
    actor_name: str,
    payload: dict[str, Any],
) -> None:
    """audit_log'a TEK bir satır ekler (append-only, UPDATE/DELETE yok — bkz.
    db/schema.sql RLS notu). `payload` json.dumps(..., default=str) ile
    serileştirilir: pandas/numpy tipleri (int64, float64, NaT, Decimal) bu
    sayede hataya düşmeden string'e döner - audit_log bir teşhis/iz kaydı,
    tip-birebir bir veri kopyası değil."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_log (table_name, record_id, action_type, actor_name, payload)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                table_name,
                record_id,
                action_type,
                actor_name,
                json.dumps(payload, ensure_ascii=False, default=str),
            ),
        )


def batch_dolu_tablolari_bul(conn: Connection, batch_id: int) -> list[str]:
    """Bir batch_id için hangi fact tablolarının (varsa) satır yazdığını DB'den
    sorgular — worker/pipeline.py'nin batch_onayla()'sı, süreç sınırını
    (ayrı bir CLI/script çağrısı — elde yalnız batch_id vardır, epdk_aylik_isle()
    tarafından döndürülen IslemSonucu bellek nesnesi DEĞİL) aşarken hangi
    tabloları aktive edeceğini bununla belirler. Bir batch bazı tablolara hiç
    satır yazmamışsa (örn. o tablonun tüm satırları reddedildi/karantinaya
    düştü) o tablo listeye girmez — aktivasyon_yap() hiç çağrılmaz, o tablodaki
    önceki aktif sürüm dokunulmadan kalır (doğru davranış: bu batch o tabloyu
    hiç etkilemedi)."""
    bulunanlar = []
    with conn.cursor() as cur:
        for tablo in _DOGAL_ANAHTAR:
            cur.execute(
                f"SELECT EXISTS(SELECT 1 FROM {tablo} WHERE ingestion_batch_id = %s)",  # nosec B608
                (batch_id,),
            )
            row = cur.fetchone()
            assert row is not None
            if row[0]:
                bulunanlar.append(tablo)
    return bulunanlar


def aktivasyon_yap(conn: Connection, tablo: str, batch_id: int) -> None:
    """P0-4: eski aktif sürümü pasifler + yeni batch'i TEK transaction'da aktifler.

    Eşzamanlılık için tablo bazlı advisory lock kullanılır (aynı anda iki
    batch aynı tabloyu aktive etmeye çalışırsa biri diğerini bekler).
    """
    if tablo not in _DOGAL_ANAHTAR:
        raise ValueError(f"Bilinmeyen fact tablosu: {tablo!r}")
    kolonlar = ", ".join(_DOGAL_ANAHTAR[tablo])

    with conn.transaction(), conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (tablo,))
        # bandit B608 bu iki execute'ta bastırıldı: tablo/kolonlar kullanıcı
        # girdisi değil - tablo yukarıda _DOGAL_ANAHTAR'a (sabit 3 değerlik
        # whitelist) karşı doğrulandı, kolonlar da aynı whitelist'ten
        # türetildi. Değerler (batch_id) ayrı parametre olarak geçiyor.
        cur.execute(
            f"""
            UPDATE {tablo}
            SET is_active = false
            WHERE is_active = true
              AND ({kolonlar}) IN (
                  SELECT {kolonlar} FROM {tablo} WHERE ingestion_batch_id = %s
              )
            """,  # nosec B608
            (batch_id,),
        )
        cur.execute(
            f"UPDATE {tablo} SET is_active = true WHERE ingestion_batch_id = %s",  # nosec B608
            (batch_id,),
        )


# ---------------------------------------------------------------------------
# job_status — Faz 1 asenkron kuyruk (bkz. modül notu)
# ---------------------------------------------------------------------------

_STALE_ESIK_SANIYE = 600  # 10 dk: heartbeat bu kadar eskiyse worker çökmüş sayılır
_MAX_DENEME = 5


@dataclass
class IsKaydi:
    job_id: int
    correlation_id: str
    attempt_count: int


def is_kaydi_olustur(conn: Connection, correlation_id: str) -> int:
    """epdk_isi_kuyruga_al()'ın adım 2'ye eklediği parça: batch oluşturulduktan
    sonra job_status'a 'queued' bir satır ekler (worker/job_worker.py'nin
    daha sonra sahipleneceği iş). correlation_id konvansiyonu: str(batch_id)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO job_status (correlation_id, status) VALUES (%s, 'queued') RETURNING job_id",
            (correlation_id,),
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


def is_sahiplen(conn: Connection, worker_id: str) -> IsKaydi | None:
    """worker/job_worker.py'nin ana poll adımı. Önce heartbeat'i bayat
    ('running' ama _STALE_ESIK_SANIYE'den uzun süredir güncellenmemiş,
    yani worker çökmüş) işleri 'queued'a geri alır (ayrı bir reaper süreci
    gerekmez), sonra kuyruktan (queued VEYA zamanı gelmiş retrying) TEK bir
    işi FOR UPDATE SKIP LOCKED ile atomik sahiplenir — aynı batch_sahiplen()
    deseni gibi, birden fazla worker aynı işi asla paylaşamaz. attempt_count
    burada +1 edilir (bu bir deneme sayılır); is_basarisiz() eşik kontrolünü
    döndürülen attempt_count'a göre yapar. Kuyrukta iş yoksa None döner."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE job_status SET status = 'queued', locked_by = NULL
            WHERE status = 'running'
              AND heartbeat_at < now() - (%s || ' seconds')::interval
            """,
            (_STALE_ESIK_SANIYE,),
        )
        cur.execute(
            """
            UPDATE job_status
            SET status = 'running', locked_by = %s, heartbeat_at = now(),
                attempt_count = attempt_count + 1, updated_at = now()
            WHERE job_id = (
                SELECT job_id FROM job_status
                WHERE status = 'queued'
                   OR (status = 'retrying' AND next_retry_at <= now())
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING job_id, correlation_id, attempt_count
            """,
            (worker_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return IsKaydi(
            job_id=int(row[0]), correlation_id=row[1], attempt_count=int(row[2])
        )


def is_basarili(conn: Connection, job_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE job_status SET status = 'succeeded', updated_at = now() WHERE job_id = %s",
            (job_id,),
        )


def _backoff_saniye(attempt_count: int) -> int:
    """Üstel geri çekilme, 1 saatte tavanlanır: 30, 60, 120, 240, ... saniye."""
    return min(30 * 2 ** (attempt_count - 1), 3600)


def is_basarisiz(conn: Connection, job: IsKaydi) -> str:
    """attempt_count _MAX_DENEME'ye ulaştıysa 'dead_letter', değilse üstel
    geri çekilmeyle 'retrying'e geçer; hangisi olduğunu döner ki çağıran
    (worker/job_worker.py) ingestion_batch.status'u aynı karara göre
    senkronize edebilsin. Hata metni job_status'ta SAKLANMAZ (kolon yok,
    bilinçli - bkz. modül notu); çağıran ingestion_batch.error_summary'ye yazar."""
    with conn.cursor() as cur:
        if job.attempt_count >= _MAX_DENEME:
            cur.execute(
                "UPDATE job_status SET status = 'dead_letter', updated_at = now() WHERE job_id = %s",
                (job.job_id,),
            )
            return "dead_letter"
        bekleme = _backoff_saniye(job.attempt_count)
        cur.execute(
            """
            UPDATE job_status
            SET status = 'retrying',
                next_retry_at = now() + (%s || ' seconds')::interval,
                updated_at = now()
            WHERE job_id = %s
            """,
            (bekleme, job.job_id),
        )
        return "retrying"
