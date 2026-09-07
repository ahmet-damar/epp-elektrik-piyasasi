"""EPP — fact_tuketim_ulke_geneli mutabakat kontrolü (kalıcı, standart
mantık, 2026-09-08 kök neden bulgusuyla düzeltildi).

fact_tuketim'in (il bazlı, `baglanti` SUM ile katlanmış) aktif toplamı
ile fact_tuketim_ulke_geneli'nin (T11'in kendi "Genel Toplam" satırı)
değeri karşılaştırılır — Sanayi HARİÇ 4 grup için (Karar 2, Sanayi zaten
fact_tuketim'e hiç yazılmıyor).

**KRİTİK bulgu (2026-09-08, 120 ay backfill'inin ardından 39 ay "uyumsuz"
çıkmasının kök nedeni):** `kpi.dogrula_tuketim()`'in negatif değer reddi
İL seviyesinde de uygulanıyor (`worker/ingest.py:fact_tuketim_yukle()`
zaten bu doğrulamadan geçmiş veriyi alır) — bir ilin Tarımsal/Aydınlatma
değeri negatifse o SATIR `fact_tuketim`'e hiç yazılmaz (audit_log'un
`red_satirlari`'nda kayıtlıdır). Ama `fact_tuketim_ulke_geneli`'nin
kaynağı olan T11'in Genel Toplam satırı, EPDK'nın KENDİ NETLEŞTİRDİĞİ
(bu negatif düzeltmeleri ZATEN içeren) ülke geneli toplamdır. Sonuç:
`fact_tuketim`'in aktif il toplamı, reddedilen (negatif) illerin payı
kadar SİSTEMATİK OLARAK YÜKSEK çıkar — bu bir veri hatası DEĞİL, aynı P0
kuralının iki farklı granülaritede (il vs ülke) BAĞIMSIZ uygulanmasının
matematiksel, beklenen bir sonucudur. 2026-09-05/07 backfill'inde bu
düzeltme UYGULANMADAN 120 aydan 39'u böyle YANLIŞLIKLA "uyumsuz" çıkmıştı
(120'nin 1'i hariç, 20260905_0002 sonrası backfill kaydı, dokumanlar/
06_canli_veri_operasyon_gunlugu.md'ye bkz.) — bu script o bulguyla
DÜZELTİLMİŞ, kalıcı standart mantığı taşır. Gelecekteki her yeni ay için
de AYNI durum (bir ilde negatif düzeltme varsa) tekrar çıkabilir — bu
BEKLENEN bir davranıştır, tekrar "bulunmasına" gerek yoktur.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg

from worker.db import get_database_url

SANAYI_DISI_GRUPLAR = frozenset(
    {"Aydınlatma", "Mesken", "Tarımsal", "Kamu ve Özel Hizmetler"}
)
_ULKE_GENELI_PARSER_DESENI = "word-%-ulke-geneli-v1"


def _reddedilen_toplam(
    conn: psycopg.Connection, batch_id: int, tarih_id: int, grup: str
) -> float:
    """Bir fact_tuketim batch'inin audit_log'undaki (INSERT, `ingest_
    tamamlandi` olayı) `red_satirlari`'ndan, verilen (tarih_id, grup)
    için reddedilen (negatif) değerlerin toplamını döner (zaten negatif
    — çağıran doğrudan toplama ekleyebilir). audit_log kaydı yoksa/eski
    formatta değilse 0.0 döner (bilinçli — tahmin ETMEZ, yalnız KAYITLI
    reddedilen satırları hesaba katar)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT payload FROM audit_log
            WHERE table_name = 'ingestion_batch' AND record_id = %s
              AND action_type = 'INSERT'
            ORDER BY audit_id LIMIT 1
            """,
            (batch_id,),
        )
        row = cur.fetchone()
    if row is None:
        return 0.0
    payload = row[0]
    if isinstance(payload, str):
        payload = json.loads(payload)
    red_satirlari = (
        payload.get("tablolar", {}).get("fact_tuketim", {}).get("red_satirlari", [])
    )
    return sum(
        float(r.get("tuketim_mwh", 0.0))
        for r in red_satirlari
        if r.get("grup") == grup and r.get("tarih_id") == tarih_id
    )


def mutabakat_kontrol_et(
    conn: psycopg.Connection,
    *,
    parser_version_deseni: str = _ULKE_GENELI_PARSER_DESENI,
    tolerans_oran: float = 0.005,
    tolerans_min_mwh: float = 1.0,
) -> tuple[set[int], list[dict]]:
    """fact_tuketim_ulke_geneli'nin (parser_version_deseni ile eşleşen
    batch'ler) her (tarih_id, grup) satırını, fact_tuketim'in AYNI (tarih_
    id, grup) için aktif il toplamından reddedilen negatif satırların
    (audit_log) çıkarılmasıyla (`il_toplami + red_toplam`, red_toplam
    zaten negatif) elde edilen DÜZELTİLMİŞ toplamla karşılaştırır.

    Döner: `(uyumsuz_batch_idler, detaylar)` — `uyumsuz_batch_idler`
    tolerans dışı kalan fact_tuketim_ulke_geneli batch_id'lerinin kümesi
    (aktivasyona uygun DEĞİL), `detaylar` her (tarih_id, grup) için
    hesaplanan değerlerin tam listesi (rapor/log için)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ft.tarih_id, dg.grup_adi, sum(ft.tuketim_mwh),
                   (array_agg(DISTINCT ft.ingestion_batch_id))[1]
            FROM fact_tuketim ft
            JOIN dim_tuketici_grubu dg ON dg.grup_id = ft.grup_id
            WHERE ft.is_active AND dg.grup_adi = ANY(%s)
            GROUP BY ft.tarih_id, dg.grup_adi
            """,
            (list(SANAYI_DISI_GRUPLAR),),
        )
        il_toplami: dict[tuple[int, str], float] = {}
        il_batch_id: dict[tuple[int, str], int] = {}
        for tarih_id, grup, toplam, batch_id in cur.fetchall():
            il_toplami[(tarih_id, grup)] = float(toplam)
            il_batch_id[(tarih_id, grup)] = batch_id

        cur.execute(
            """
            SELECT fug.tarih_id, dg.grup_adi, fug.tuketim_mwh, fug.ingestion_batch_id
            FROM fact_tuketim_ulke_geneli fug
            JOIN dim_tuketici_grubu dg ON dg.grup_id = fug.grup_id
            JOIN ingestion_batch ib ON ib.batch_id = fug.ingestion_batch_id
            WHERE ib.parser_version LIKE %s
            """,
            (parser_version_deseni,),
        )
        satirlar = cur.fetchall()

    uyumsuz_batch_idler: set[int] = set()
    detaylar: list[dict] = []
    for tarih_id, grup, deger_ug, ug_batch_id in satirlar:
        deger_ug = float(deger_ug)
        if grup not in SANAYI_DISI_GRUPLAR:
            continue
        deger_il = il_toplami.get((tarih_id, grup))
        if deger_il is None:
            detaylar.append(
                {
                    "tarih_id": tarih_id,
                    "grup": grup,
                    "durum": "il_toplami_yok",
                    "ulke_geneli": deger_ug,
                }
            )
            uyumsuz_batch_idler.add(ug_batch_id)
            continue

        red_toplam = _reddedilen_toplam(
            conn, il_batch_id[(tarih_id, grup)], tarih_id, grup
        )
        duzeltilmis = deger_il + red_toplam  # red_toplam zaten negatif
        fark = abs(duzeltilmis - deger_ug)
        tolerans = max(tolerans_min_mwh, abs(deger_ug) * tolerans_oran)
        uyumlu = fark <= tolerans
        detaylar.append(
            {
                "tarih_id": tarih_id,
                "grup": grup,
                "il_toplami": deger_il,
                "red_toplam": red_toplam,
                "duzeltilmis": duzeltilmis,
                "ulke_geneli": deger_ug,
                "fark": fark,
                "uyumlu": uyumlu,
            }
        )
        if not uyumlu:
            uyumsuz_batch_idler.add(ug_batch_id)

    return uyumsuz_batch_idler, detaylar


def main() -> int:
    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1
    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        uyumsuz, detaylar = mutabakat_kontrol_et(conn)
    uyumlu_sayisi = sum(1 for d in detaylar if d.get("uyumlu"))
    print(f"Kontrol edilen (tarih_id, grup) çifti: {len(detaylar)}")
    print(f"Uyumlu: {uyumlu_sayisi}, uyumsuz batch: {len(uyumsuz)}")
    for d in detaylar:
        if not d.get("uyumlu", True):
            print(" ", d)
    return 0 if not uyumsuz else 1


if __name__ == "__main__":
    sys.exit(main())
