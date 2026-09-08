"""EPP — `fact_uretim_il_geneli` ↔ `fact_uretim_kaynak_geneli` çapraz
mutabakat kontrolü (2026-09-09, gece çalışması — Aşama 3/ADIM 3 madde 3).

**Bu işin asıl güvencesi (kullanıcı talimatı):** iki tablo AYNI üretim
toplamının BAĞIMSIZ iki kırılımı (il-bazında vs kaynak-bazında,
`10_TEKNIK_MASTER_DOKUMAN.md` §5.7) — her (tarih_id, lisans_id) çifti
için toplamları eşleşmelidir. Eşleşmezse bu bir parser hatasına işaret
eder (yanlış ay kolonu, eksik/fazla satır, vb.) ve **aktivasyonu
ENGELLEMELİDİR** — yalnız uyarı vermek yetmez (`mutabakat_ulke_geneli.py`
ile AYNI ilke, ama o script'ten farklı olarak burada iki taraf da EŞİT
derecede "yeni" — biri uzun süredir aktif il bazlı bir tablo değil, ikisi
de aynı anda yükleniyor; bu yüzden `is_active` FİLTRELENMEZ, her iki
tarafın da EN SON batch'i (`ingestion_batch_id DESC`) karşılaştırılır —
`fact_tuketim_ulke_geneli`'nin batch-bağımlılığı dersiyle TUTARLI, bkz.
migration 20260908_0002).

**Kanıt (2026-09-09, gerçek 6 dosyaya karşı — worker/parser.py §5.8
düzeltmesi doğrulanırken):** T2 (kaynak) ile T3 (il) toplamları, VE T5
(kaynak) ile T6 (il) toplamları 6/6 ayda ONDALIK BASAMAĞA KADAR birebir
eşleşti — bu script'in ülke-geneli seviyede YEŞİL çıkması BEKLENİR
(gerçek veri backfill'i ADIM 3 madde 4'te)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg

from worker.db import get_database_url

TOLERANS_ORAN = 0.005
TOLERANS_MIN_MWH = 1.0


_TABLO_ADLARI = ("fact_uretim_il_geneli", "fact_uretim_kaynak_geneli")


def _en_son_batch_toplamlari(
    conn: psycopg.Connection, tablo: str
) -> dict[tuple[int, int], tuple[float, int]]:
    """`tablo`nun (`fact_uretim_il_geneli` veya `fact_uretim_kaynak_geneli`
    — `_TABLO_ADLARI` dışında bir değer KABUL EDİLMEZ, SQL enjeksiyonuna
    kapalı) her (tarih_id, lisans_id) çifti için EN SON batch'ine
    (aktivasyon durumundan BAĞIMSIZ — bkz. modül notu) ait `uretim_mwh`
    toplamını ve o batch_id'yi döner."""
    if tablo not in _TABLO_ADLARI:
        raise ValueError(f"Beklenmeyen tablo adı: {tablo!r}")
    with conn.cursor() as cur:
        cur.execute(
            f"""
            WITH en_son_batch AS (
                SELECT DISTINCT ON (tarih_id, lisans_id)
                    tarih_id, lisans_id, ingestion_batch_id
                FROM {tablo}
                ORDER BY tarih_id, lisans_id, ingestion_batch_id DESC
            )
            SELECT f.tarih_id, f.lisans_id, sum(f.uretim_mwh), esb.ingestion_batch_id
            FROM {tablo} f
            JOIN en_son_batch esb
              ON esb.tarih_id = f.tarih_id
             AND esb.lisans_id = f.lisans_id
             AND esb.ingestion_batch_id = f.ingestion_batch_id
            GROUP BY f.tarih_id, f.lisans_id, esb.ingestion_batch_id
            """
        )
        rows = cur.fetchall()
    return {
        (tarih_id, lisans_id): (float(toplam), batch_id)
        for tarih_id, lisans_id, toplam, batch_id in rows
    }


def mutabakat_kontrol_et(
    conn: psycopg.Connection,
    *,
    tolerans_oran: float = TOLERANS_ORAN,
    tolerans_min_mwh: float = TOLERANS_MIN_MWH,
) -> tuple[set[int], list[dict]]:
    """`fact_uretim_il_geneli` ile `fact_uretim_kaynak_geneli`'nin EN SON
    batch'lerini, her (tarih_id, lisans_id) çifti için karşılaştırır.

    Döner: `(uyumsuz_batch_idler, detaylar)` — `uyumsuz_batch_idler`
    tolerans dışı kalan (tarih_id, lisans_id) çiftlerinin İKİ tablodaki
    batch_id'lerinin BİRLEŞİMİ (aktivasyona uygun DEĞİL — hangi tablonun
    hatalı olduğu belli olmadığından ikisi de bloklanır), `detaylar` her
    çift için hesaplanan değerlerin tam listesi."""
    il = _en_son_batch_toplamlari(conn, "fact_uretim_il_geneli")
    kaynak = _en_son_batch_toplamlari(conn, "fact_uretim_kaynak_geneli")

    tum_anahtarlar = set(il) | set(kaynak)
    uyumsuz_batch_idler: set[int] = set()
    detaylar: list[dict] = []

    for tarih_id, lisans_id in sorted(tum_anahtarlar):
        il_deger = il.get((tarih_id, lisans_id))
        kaynak_deger = kaynak.get((tarih_id, lisans_id))

        if il_deger is None or kaynak_deger is None:
            detaylar.append(
                {
                    "tarih_id": tarih_id,
                    "lisans_id": lisans_id,
                    "durum": "bir_taraf_eksik",
                    "il_toplami": il_deger[0] if il_deger else None,
                    "kaynak_toplami": kaynak_deger[0] if kaynak_deger else None,
                    "uyumlu": False,
                }
            )
            if il_deger is not None:
                uyumsuz_batch_idler.add(il_deger[1])
            if kaynak_deger is not None:
                uyumsuz_batch_idler.add(kaynak_deger[1])
            continue

        il_toplam, il_batch_id = il_deger
        kaynak_toplam, kaynak_batch_id = kaynak_deger
        fark = abs(il_toplam - kaynak_toplam)
        tolerans = max(tolerans_min_mwh, abs(kaynak_toplam) * tolerans_oran)
        uyumlu = fark <= tolerans
        detaylar.append(
            {
                "tarih_id": tarih_id,
                "lisans_id": lisans_id,
                "il_toplami": il_toplam,
                "kaynak_toplami": kaynak_toplam,
                "fark": fark,
                "fark_yuzde": (fark / abs(kaynak_toplam) * 100)
                if kaynak_toplam
                else None,
                "uyumlu": uyumlu,
            }
        )
        if not uyumlu:
            uyumsuz_batch_idler.add(il_batch_id)
            uyumsuz_batch_idler.add(kaynak_batch_id)

    return uyumsuz_batch_idler, detaylar


def periyot_aktivasyona_uygun_mu(
    conn: psycopg.Connection, tarih_id: int
) -> tuple[bool, str]:
    """`otomatik_onaya_uygun()` ile AYNI `(bool, sebep)` imzası — ADIM 3
    madde 4'ün backfill/pipeline kodu, bu periyodun İKİ tablosunu da
    aktive etmeden ÖNCE bunu çağırmalı. Yalnız `tarih_id`e ait (tüm
    lisans_id'ler) satırları kontrol eder; başka periyotlardaki
    uyumsuzluklar bu periyodu ETKİLEMEZ."""
    _, detaylar = mutabakat_kontrol_et(conn)
    bu_periyot = [d for d in detaylar if d["tarih_id"] == tarih_id]
    if not bu_periyot:
        return False, f"tarih_id={tarih_id}: hiç veri bulunamadı"
    uyumsuzlar = [d for d in bu_periyot if not d.get("uyumlu", True)]
    if uyumsuzlar:
        return (
            False,
            f"tarih_id={tarih_id}: {len(uyumsuzlar)} lisans_id uyumsuz (il≠kaynak toplamı)",
        )
    return True, ""


def main() -> int:
    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1
    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        uyumsuz, detaylar = mutabakat_kontrol_et(conn)
    uyumlu_sayisi = sum(1 for d in detaylar if d.get("uyumlu"))
    print(f"Kontrol edilen (tarih_id, lisans_id) çifti: {len(detaylar)}")
    print(f"Uyumlu: {uyumlu_sayisi}, uyumsuz batch: {len(uyumsuz)}")
    for d in detaylar:
        if not d.get("uyumlu", True):
            print(" ", d)
    return 0 if not uyumsuz else 1


if __name__ == "__main__":
    sys.exit(main())
