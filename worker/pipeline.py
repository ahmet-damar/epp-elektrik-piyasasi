"""EPP — Faz 0 orkestrasyon: EPDK aylık dosyayı uçtan uca işler.

Kaynak: dokumanlar/01_kavramsal_tasarim.md §4 (Uçtan Uca Veri Akışı):
1. SHA-256 hash
2. source_asset (source_kind='file') + ingestion_batch (status='queued')
3. Worker batch'i ATOMİK sahiplenir (queued -> running)
4. Parse + doğrula + önizleme/onay -> kabul edilen satırlar fact_*'a is_active=false
5. Aktivasyon transaction -> is_active=true (eski sürüm pasif)
6. Dashboard güncel aktif sürümü gösterir (Faz 2, kapsam dışı)

Adım 1-4 TEK fonksiyonda (epdk_aylik_isle). Adım 5 BİLİNÇLİ OLARAK AYRI bir
fonksiyondadır (batch_onayla) — Faz 0'da henüz bir onay UI'ı yok; bu ayrım,
is_active=false ile yazılmış "önizleme" verisi ile "aktivasyon" arasındaki
gerçek boşluğu korur: epdk_aylik_isle() sonucundaki sayılar (tablo başına
yüklenen/atlanan/red/karantina + mutabakat) önce incelenir, ancak SONRA
batch_onayla() çağrılır. batch_onayla()'nın çağrılması, ileride UI'daki
"onayla" adımının Faz 0'daki karşılığıdır (otomatik değil, bilinçli ayrı
bir çağrı). ingestion_batch.status yalnız şu değerleri alabilir (db/schema.sql
CHECK): queued/running/succeeded/failed/retrying/dead_letter — bu yüzden
"önizleme, henüz aktive edilmedi" durumu ayrı bir status değeriyle DEĞİL,
'running'in devamı olarak temsil edilir; yalnız batch_onayla() sonunda
'succeeded'e geçer.

Kapsam (Faz 0, tek bir EPDK aylık dosya -> tüm fact tablolarına yazma):
- T1 + T4 (kurulu güç, lisanslı/lisanssız) -> fact_uretim. Yalnız
  kurulu_guc_mw yazılır; uretim_mwh bu grain'de (il×kaynak) kaynak dosyada
  hiç mevcut değil (bkz. worker/parser.py modül notu, migration 20260819_0005).
- T10 (abone, il×grup) -> fact_abone. T9 (ülke geneli) fact tablosuna
  YAZILMAZ, yalnız mutabakat_kontrol() ile T10'un toplamını doğrulamak için
  okunur.
- T11 (tüketim, il×grup, P0-2 Sanayi-İLETİM/DAĞITIM ayrımı) -> fact_tuketim.
  T7 (ülke geneli) aynı şekilde yalnız mutabakat için okunur.
  T7/T9'un fact tablosuna yazılmaması VARSAYIM DEĞİL: gerçek dosyada bu iki
  tablo yalnız ülke geneli tek satır içerir, il kırılımı YAPISAL OLARAK YOK
  (bkz. parser.tablo7_faturalanan_tur_oku/tablo9_abone_tur_oku docstring'i,
  "il yok") — dolayısıyla il_kodu NOT NULL olan fact_tuketim/fact_abone'ye
  hiç yazılamazlar.
- T13 (serbest tüketici, il×tur×grup) -> fact_serbest_tuketici.
- T2/T3/T5/T6/T8/T12 bu pipeline'ın kapsamı dışında (T8/T12 T11 ile
  redundant, T2/T3/T5/T6'da il×kaynak kesişimi hiç yok — bkz.
  worker/parser.py modül notu). eksik_tablolari_bul() bu yüzden yalnız
  T1/T4/T10/T11/T13'ü ZORUNLU sayar; T7/T9 eksikse batch reddedilmez,
  yalnız o mutabakat kontrolü atlanır (mutabakat[...]=None) — mutabakat
  uyuşmazlığı da (dokümanlı ±%0,5 kuralı) YUMUŞAK bırakılmıştır: batch'i
  reddetmez, yalnız IslemSonucu.mutabakat'a düşer. epdk_aylik_isle() /
  batch_onayla() ayrımı zaten bir insan-onay güvenlik ağı sağladığından
  ayrıca sert bir red gereksiz görüldü.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING

import openpyxl
import pandas as pd

from worker import ingest, kpi, parser

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet
    from psycopg import Connection

# Yalnız fact tablosuna YAZAN tablolar zorunlu; T7/T9 (mutabakat-only) hariç.
_ZORUNLU_TABLOLAR = ["Tablo 1", "Tablo 4", "Tablo 10", "Tablo 11", "Tablo 13"]


@dataclass
class TabloSonucu:
    """Bir fact tablosu için: parser çıktısının toplam satırı, doğrulamadan
    (kpi.dogrula_*) sonra red/karantina, ve DB'ye is_active=false yazılan/
    NOT NULL eksikliği yüzünden atlanan satır sayıları."""

    toplam: int = 0
    red: int = 0
    karantina: int = 0
    yuklenen: int = 0
    atlanan: int = 0


@dataclass
class IslemSonucu:
    """epdk_aylik_isle()'ın döndürdüğü önizleme özeti — adım 5'e (aktivasyon)
    geçmeden önce incelenecek veri budur."""

    batch_id: int
    sahiplenildi: bool = True
    eksik_tablolar: list[str] = field(default_factory=list)
    tablolar: dict[str, TabloSonucu] = field(default_factory=dict)
    mutabakat: dict[str, bool | None] = field(default_factory=dict)


def _sayfa(wb: openpyxl.Workbook, tablo_no: int) -> Worksheet:
    ws = parser.sayfa_bul(wb, tablo_no)
    if ws is None:
        # eksik_tablolari_bul() zaten aynı numaralandırmayla kontrol ettiğinden
        # buraya düşülmesi bir tutarsızlığa işaret eder.
        raise ValueError(
            f"Tablo {tablo_no} sayfası bulunamadı (eksik_tablolari_bul ile tutarsız)"
        )
    return ws


def _mutabakat(
    il_df: pd.DataFrame, ulusal_df: pd.DataFrame, deger_kolonu: str
) -> bool | None:
    """İl bazlı toplam ile ülke geneli (T7/T9) satırını karşılaştırır. Taraflardan
    biri boşsa (sayfa yok/beklenmedik yapı) None döner — 'kontrol edilemedi',
    'uyuşmadı' ile karıştırılmamalı."""
    if il_df.empty or ulusal_df.empty:
        return None
    hesaplanan = float(il_df[deger_kolonu].sum())
    resmi = float(ulusal_df[deger_kolonu].sum())
    return parser.mutabakat_kontrol(hesaplanan, resmi)


def epdk_aylik_isle(
    conn: Connection,
    *,
    dosya_adi: str,
    icerik: bytes,
    tarih_id: int,
    source_period: str,
    parser_version: str = "0.1",
    schema_version: str = "1",
    uploaded_by: str | None = None,
) -> IslemSonucu:
    """Adım 1-4: hash -> source_asset(file)+batch(queued) -> atomik sahiplenme
    -> parse + doğrula + yükle (is_active=false). Adım 5 (aktivasyon) BURADA
    YAPILMAZ — bkz. modül notu, batch_onayla()."""
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi=dosya_adi,
        icerik=icerik,
        donem_tipi=ingest.tarih_bilesenleri(tarih_id)["donem_tipi"],
        source_period=source_period,
        uploaded_by=uploaded_by,
    )
    batch_id = ingest.batch_olustur(
        conn, source_asset_id, parser_version, schema_version
    )
    sonuc = IslemSonucu(batch_id=batch_id)

    if not ingest.batch_sahiplen(conn, batch_id):
        # P0-5: aynı (source_asset_id, parser_version, schema_version) daha önce
        # sahiplenilmiş/tamamlanmış — burada tekrar işlemeye kalkışmıyoruz.
        sonuc.sahiplenildi = False
        return sonuc

    wb = openpyxl.load_workbook(BytesIO(icerik), data_only=True)
    sonuc.eksik_tablolar = parser.eksik_tablolari_bul(wb.sheetnames, _ZORUNLU_TABLOLAR)
    if sonuc.eksik_tablolar:
        ingest.batch_durumu_guncelle(
            conn,
            batch_id,
            "failed",
            error_summary=f"eksik tablo(lar): {', '.join(sonuc.eksik_tablolar)}",
        )
        return sonuc

    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)

    toplam_satir = 0
    toplam_yuklenen = 0
    toplam_atlanan = 0

    def _isle(
        anahtar: str,
        ham: pd.DataFrame,
        dogrulanan: kpi.DogrulamaSonucu,
        yuklenen: int,
        atlanan: int,
    ) -> None:
        nonlocal toplam_satir, toplam_yuklenen, toplam_atlanan
        sonuc.tablolar[anahtar] = TabloSonucu(
            toplam=len(ham),
            red=len(dogrulanan.red),
            karantina=len(dogrulanan.karantina),
            yuklenen=yuklenen,
            atlanan=atlanan,
        )
        toplam_satir += len(ham)
        toplam_yuklenen += yuklenen
        toplam_atlanan += atlanan + len(dogrulanan.red) + len(dogrulanan.karantina)

    # --- T1 + T4 -> fact_uretim (yalnız kurulu_guc_mw) ---
    uretim_ham = pd.concat(
        [
            parser.tablo1_kurulu_guc_oku(_sayfa(wb, 1), tarih_id),
            parser.tablo4_lisanssiz_kurulu_guc_oku(_sayfa(wb, 4), tarih_id),
        ],
        ignore_index=True,
    )
    dogrulanan = kpi.dogrula_uretim(uretim_ham)
    yuklenen, atlanan = ingest.fact_uretim_yukle(conn, dogrulanan.kabul, batch_id)
    _isle("fact_uretim", uretim_ham, dogrulanan, yuklenen, atlanan)

    # --- T10 -> fact_abone (+ T9 yumuşak mutabakat) ---
    abone_ham = parser.tablo10_abone_il_oku(_sayfa(wb, 10), tarih_id)
    dogrulanan = kpi.dogrula_abone(abone_ham)
    yuklenen, atlanan = ingest.fact_abone_yukle(conn, dogrulanan.kabul, batch_id)
    _isle("fact_abone", abone_ham, dogrulanan, yuklenen, atlanan)

    t9_ws = parser.sayfa_bul(wb, 9)
    t9_ham = (
        parser.tablo9_abone_tur_oku(t9_ws, tarih_id)
        if t9_ws is not None
        else pd.DataFrame()
    )
    sonuc.mutabakat["fact_abone"] = _mutabakat(abone_ham, t9_ham, "abone_sayisi")

    # --- T11 -> fact_tuketim (P0-2) (+ T7 yumuşak mutabakat) ---
    tuketim_ham = parser.tablo11_tuketim_oku(_sayfa(wb, 11), tarih_id)
    dogrulanan = kpi.dogrula_tuketim(tuketim_ham)
    yuklenen, atlanan = ingest.fact_tuketim_yukle(conn, dogrulanan.kabul, batch_id)
    _isle("fact_tuketim", tuketim_ham, dogrulanan, yuklenen, atlanan)

    t7_ws = parser.sayfa_bul(wb, 7)
    t7_ham = (
        parser.tablo7_faturalanan_tur_oku(t7_ws, tarih_id)
        if t7_ws is not None
        else pd.DataFrame()
    )
    sonuc.mutabakat["fact_tuketim"] = _mutabakat(tuketim_ham, t7_ham, "tuketim_mwh")

    # --- T13 -> fact_serbest_tuketici ---
    serbest_ham = parser.tablo13_serbest_tuketici_oku(_sayfa(wb, 13), tarih_id)
    dogrulanan = kpi.dogrula_serbest_tuketici(serbest_ham)
    yuklenen, atlanan = ingest.fact_serbest_tuketici_yukle(
        conn, dogrulanan.kabul, batch_id
    )
    _isle("fact_serbest_tuketici", serbest_ham, dogrulanan, yuklenen, atlanan)

    # Adım 4 tamamlandı: status kasıtlı olarak 'running' kalır (CHECK kısıtı
    # yalnız queued/running/succeeded/failed/retrying/dead_letter'a izin verir)
    # — 'succeeded'e geçiş yalnız batch_onayla()'nın aktivasyonuyla olur.
    ingest.batch_durumu_guncelle(
        conn,
        batch_id,
        "running",
        total_row_count=toplam_satir,
        accepted_row_count=toplam_yuklenen,
        rejected_row_count=toplam_atlanan,
    )
    return sonuc


def batch_onayla(conn: Connection, sonuc: IslemSonucu) -> None:
    """Adım 5 (dokumanlar/01 §4): Faz 0'da onay UI'ı yok — bu fonksiyonun
    BİLİNÇLİ OLARAK çağrılması onay yerine geçer. epdk_aylik_isle()'ın
    is_active=false yazdığı HER fact tablosu için tek tek aktivasyon_yap()
    çağırır (P0-4), sonunda batch'i 'succeeded' yapar."""
    for tablo in sonuc.tablolar:
        ingest.aktivasyon_yap(conn, tablo, sonuc.batch_id)
    ingest.batch_durumu_guncelle(conn, sonuc.batch_id, "succeeded")
