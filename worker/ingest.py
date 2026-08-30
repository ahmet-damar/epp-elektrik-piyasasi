"""EPP — Ingestion pipeline (Faz 0): source_asset → ingestion_batch → fact_*.

Kaynak: dokumanlar/01_kavramsal_tasarim.md (§4 Uçtan Uca Veri Akışı),
dokumanlar/02_srs_ozet.md (P0-2..P0-5), dokumanlar/03_veri_modeli.md.

Akış: dosya yüklenir → source_asset (SHA-256 hash) → ingestion_batch (queued/
running) → doğrulanmış satırlar fact_* tablosuna is_active=false yazılır →
aktivasyon_yap() TEK transaction içinde eski aktif sürümü pasifler ve yeni
batch'i aktifler (P0-4). Tüm sorgular parametrelidir (SQL injection'a karşı).

NOT: Bu modül gerçek bir PostgreSQL'e karşı yalnızca CI'nin 'integration'
job'ında (worker/tests/test_ingest_integration.py, DATABASE_URL ile) test
edilir; yerel geliştirme ortamında çalışan bir Postgres yoktu.
"""

from __future__ import annotations

import hashlib
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
) -> int:
    """P0-3: source_kind='file' → file_name + file_hash zorunlu."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO source_asset
                (source_type, source_kind, source_period, donem_tipi, file_name, file_hash, uploaded_by)
            VALUES (%s, 'file', %s, %s, %s, %s, %s)
            RETURNING source_asset_id
            """,
            (
                source_type,
                source_period,
                donem_tipi,
                dosya_adi,
                dosya_hash(icerik),
                uploaded_by,
            ),
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


def batch_olustur(
    conn: Connection, source_asset_id: int, parser_version: str, schema_version: str
) -> int:
    """P0-5: (source_asset_id, parser_version, schema_version) tekil; varsa mevcut batch_id döner."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion_batch (source_asset_id, parser_version, schema_version, status)
            VALUES (%s, %s, %s, 'running')
            ON CONFLICT (source_asset_id, parser_version, schema_version)
            DO UPDATE SET status = ingestion_batch.status
            RETURNING batch_id
            """,
            (source_asset_id, parser_version, schema_version),
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


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


_DOGAL_ANAHTAR = {
    "fact_tuketim": ["il_kodu", "tarih_id", "grup_id", "baglanti"],
    "fact_uretim": ["il_kodu", "tarih_id", "kaynak_id", "lisans_id"],
    "fact_abone": ["il_kodu", "tarih_id", "grup_id"],
    "fact_serbest_tuketici": ["il_kodu", "tarih_id", "tur", "grup_id"],
}


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
