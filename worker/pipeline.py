"""EPP — EPDK aylık dosyayı uçtan uca işler (Faz 0 senkron + Faz 1 asenkron).

Kaynak: dokumanlar/01_kavramsal_tasarim.md §4 (Uçtan Uca Veri Akışı):
1. SHA-256 hash
2. source_asset (source_kind='file') + ingestion_batch (status='queued')
3. Worker batch'i ATOMİK sahiplenir (queued -> running)
4. Parse + doğrula + önizleme/onay -> kabul edilen satırlar fact_*'a is_active=false
5. Aktivasyon transaction -> is_active=true (eski sürüm pasif)
6. Dashboard güncel aktif sürümü gösterir (Faz 2, kapsam dışı)

İki çağrı yolu vardır, ikisi de adım 4'ün gövdesini (_isle_govde) paylaşır:
- **Senkron (Faz 0):** epdk_aylik_isle() adım 1-4'ü TEK çağrıda, aynı süreçte
  yapar (CLI/manuel/test kullanımı — bkz. worker/scripts/gercek_dosya_dogrula.py).
- **Asenkron (Faz 1):** epdk_isi_kuyruga_al() yalnız adım 1-2'yi yapar (+
  job_status'a 'queued' bir kayıt) ve HEMEN döner — parse etmez. Dosya
  baytları content-addressed olarak diske yazılır (source_asset.storage_path).
  worker/job_worker.py daha sonra (ayrı bir çalıştırmada/süreçte) bu job'ı
  atomik sahiplenir, dosyayı storage_path'ten okur, _isle_govde()'yi çağırır.

Adım 5 (aktivasyon) BİLİNÇLİ OLARAK AYRI bir fonksiyondadır (batch_onayla) —
is_active=false ile yazılmış "önizleme" verisi ile "aktivasyon" arasındaki
gerçek boşluğu korur. ingestion_batch.status yalnız şu değerleri alabilir
(db/schema.sql CHECK): queued/running/succeeded/failed/retrying/dead_letter —
bu yüzden "önizleme, henüz aktive edilmedi" durumu ayrı bir status değeriyle
DEĞİL, 'running'in devamı olarak temsil edilir; yalnız batch_onayla() sonunda
'succeeded'e geçer.

Faz 0'da (senkron) batch_onayla() çağrısı her zaman bilinçli/elle yapılırdı
(UI yoktu). Faz 1'de worker/job_worker.py, otomatik_onaya_uygun() eşiğini
geçen batch'leri OTOMATİK aktive eder (kullanıcı kararı, 2026-08-30): tüm
mutabakat sonuçları False değilse (True/None kabul) VE hiçbir tabloda red/
karantina yoksa, worker batch_onayla()'yı kendisi çağırır. Eşik tutmazsa
batch 'running'de bırakılır, net bir log/uyarı düşülür — elle batch_onayla()
beklenir (Faz 0'daki gibi). Amaç: temiz geçen aylar otomatik aksın, şüpheli
olanlar insan gözünden kaçmasın.

Kapsam (tek bir EPDK aylık dosya -> tüm fact tablolarına yazma):
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
from pathlib import Path
from typing import TYPE_CHECKING

import openpyxl
import pandas as pd

from worker import ingest, kpi, parser

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet
    from psycopg import Connection

# Yalnız fact tablosuna YAZAN tablolar zorunlu; T7/T9 (mutabakat-only) hariç.
_ZORUNLU_TABLOLAR = ["Tablo 1", "Tablo 4", "Tablo 10", "Tablo 11", "Tablo 13"]

# worker/job_worker.py'nin işleyeceği dosyaların content-addressed yazıldığı
# varsayılan dizin (self-host: yerel disk, harici depolama bağımlılığı yok).
# .gitignore'da 'var/' — hiçbir yüklenen dosya repoya girmez.
VARSAYILAN_DEPO_DIZINI = Path("var/uploads")


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


@dataclass
class KuyrukSonucu:
    """epdk_isi_kuyruga_al()'ın döndürdüğü kimlikler — worker/job_worker.py
    job_id'yi job_status'tan sahiplenir, correlation_id üzerinden batch_id'ye ulaşır."""

    job_id: int
    batch_id: int
    source_asset_id: int


def otomatik_onaya_uygun(sonuc: IslemSonucu) -> tuple[bool, str]:
    """Faz 1 otomatik aktivasyon eşiği (kullanıcı kararı, 2026-08-30):
    TÜM mutabakat sonuçları False DEĞİL (True/None kabul) VE HER tabloda
    red=0 VE karantina=0 olmalı. Biri tutmazsa (False, sebep) döner —
    worker/job_worker.py batch'i aktive etmeden bırakır, elle batch_onayla()
    beklenir (Faz 0'daki gibi)."""
    for anahtar, deger in sonuc.mutabakat.items():
        if deger is False:
            return False, f"mutabakat uyuşmadı: {anahtar}"
    for tablo, t in sonuc.tablolar.items():
        if t.red > 0:
            return False, f"{tablo}: {t.red} satır reddedildi"
        if t.karantina > 0:
            return False, f"{tablo}: {t.karantina} satır karantinada"
    return True, ""


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
    """SENKRON yol (Faz 0): adım 1-4'ü TEK çağrıda yapar — hash ->
    source_asset(file)+batch(queued) -> atomik sahiplenme -> _isle_govde().
    Adım 5 (aktivasyon) BURADA YAPILMAZ — bkz. modül notu, batch_onayla().
    Asenkron/kuyruklu yol için bkz. epdk_isi_kuyruga_al()."""
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

    return _isle_govde(
        conn,
        batch_id,
        icerik,
        tarih_id,
        actor_name=uploaded_by or "system:epdk_aylik_isle",
    )


def epdk_isi_kuyruga_al(
    conn: Connection,
    *,
    dosya_adi: str,
    icerik: bytes,
    tarih_id: int,
    source_period: str,
    parser_version: str = "0.1",
    schema_version: str = "1",
    uploaded_by: str | None = None,
    depo_dizini: Path | str = VARSAYILAN_DEPO_DIZINI,
) -> KuyrukSonucu:
    """ASENKRON yol (Faz 1): adım 1-2'yi yapar (+ job_status'a 'queued' kayıt)
    ve HEMEN döner — PARSE ETMEZ. Dosya baytları content-addressed olarak
    diske yazılır (source_asset.storage_path); worker/job_worker.py daha
    sonra bu job'ı sahiplenip _isle_govde()'yi çağırır. Aynı dosya birden
    çok kez kuyruğa alınırsa her seferinde yeni bir source_asset satırı
    açılır (bilinçli — source_asset bir audit log, bkz. worker/ingest.py
    modül notu); disk yazımı content-addressed olduğundan tekrar edilmez."""
    depo = Path(depo_dizini)
    depo.mkdir(parents=True, exist_ok=True)
    hedef_yol = depo / f"{ingest.dosya_hash(icerik)}.xlsx"
    if not hedef_yol.exists():
        hedef_yol.write_bytes(icerik)

    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi=dosya_adi,
        icerik=icerik,
        donem_tipi=ingest.tarih_bilesenleri(tarih_id)["donem_tipi"],
        source_period=source_period,
        uploaded_by=uploaded_by,
        storage_path=str(hedef_yol),
    )
    batch_id = ingest.batch_olustur(
        conn, source_asset_id, parser_version, schema_version
    )
    job_id = ingest.is_kaydi_olustur(conn, str(batch_id))
    return KuyrukSonucu(
        job_id=job_id, batch_id=batch_id, source_asset_id=source_asset_id
    )


def _isle_govde(
    conn: Connection,
    batch_id: int,
    icerik: bytes,
    tarih_id: int,
    actor_name: str = "system",
) -> IslemSonucu:
    """Adım 4'ün gövdesi: parse + doğrula + yükle (is_active=false). batch'in
    zaten var olduğunu ve sahiplenildiğini varsayar (çağıran sorumludur) —
    hem epdk_aylik_isle() (senkron) hem worker/job_worker.py (asenkron) bunu
    paylaşır.

    `actor_name`: audit_log'a düşecek "kim/ne işledi" bilgisi (epdk_aylik_isle()
    çağıranın uploaded_by'ı ya da worker/job_worker.py'nin sabit değeri).
    Adım 4 (bu fonksiyon) TAMAMLANDIĞINDA audit_log'a bir INSERT kaydı düşülür:
    her tablonun toplam/red/karantina/yüklenen/atlanan sayıları + RED
    satırlarının TAM detayı (genelde az sayıda, sıfır tolerans kuralı gereği)
    + KARANTİNA satırlarının yalnız sayısı ve ilk 20 örneği (tam döküm değil -
    büyük olabilir, bkz. dokumanlar/06_canli_veri_operasyon_gunlugu.md)."""
    sonuc = IslemSonucu(batch_id=batch_id)
    wb = openpyxl.load_workbook(BytesIO(icerik), data_only=True)
    sonuc.eksik_tablolar = parser.eksik_tablolari_bul(wb.sheetnames, _ZORUNLU_TABLOLAR)
    if sonuc.eksik_tablolar:
        ingest.batch_durumu_guncelle(
            conn,
            batch_id,
            "failed",
            error_summary=f"eksik tablo(lar): {', '.join(sonuc.eksik_tablolar)}",
        )
        ingest.audit_log_yaz(
            conn,
            table_name="ingestion_batch",
            record_id=batch_id,
            action_type="UPDATE",
            actor_name=actor_name,
            payload={
                "olay": "ingest_basarisiz",
                "eksik_tablolar": sonuc.eksik_tablolar,
            },
        )
        return sonuc

    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)

    toplam_satir = 0
    toplam_yuklenen = 0
    toplam_atlanan = 0
    # audit_log payload'ı için: RED satırlarının TAM detayı (genelde az sayıda,
    # sıfır tolerans kuralı gereği) + KARANTİNA'nın yalnız sayısı + ilk 20
    # örneği (tam döküm değil - potansiyel olarak büyük olabilir).
    audit_tablolar: dict[str, dict[str, object]] = {}

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
        audit_tablolar[anahtar] = {
            "toplam": len(ham),
            "red": len(dogrulanan.red),
            "karantina": len(dogrulanan.karantina),
            "yuklenen": yuklenen,
            "atlanan": atlanan,
            "red_satirlari": dogrulanan.red.to_dict("records"),
            "karantina_ornekleri": dogrulanan.karantina.head(20).to_dict("records"),
        }

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
    # T11 KÜMÜLATİF veri döndürür (yıl başından bu aya kadar - EPDK'nın kendi
    # başlığı "Kümülatif Faturalanan Elektrik Tüketimi..." der, 2026-08-31'de
    # bulundu). Aylık değeri, aynı yılın önceki aktif aylarının toplamını
    # çıkararak türetiyoruz - bkz. ingest.yil_ici_onceki_tuketim_toplami()
    # docstring'i. Yılın ilk ayında (öncesi yok) fark 0, kümülatif=aylık.
    tuketim_kumulatif = parser.tablo11_tuketim_oku(_sayfa(wb, 11), tarih_id)
    onceki_toplam = ingest.yil_ici_onceki_tuketim_toplami(
        conn, tarih_id // 100, tarih_id
    )
    tuketim_ham = tuketim_kumulatif.merge(
        onceki_toplam, on=["il_kodu", "grup", "baglanti"], how="left"
    )
    tuketim_ham["onceki_toplam"] = tuketim_ham["onceki_toplam"].fillna(0.0)
    tuketim_ham["tuketim_mwh"] = (
        tuketim_ham["tuketim_mwh"] - tuketim_ham["onceki_toplam"]
    )
    tuketim_ham = tuketim_ham.drop(columns=["onceki_toplam"])
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
    ingest.audit_log_yaz(
        conn,
        table_name="ingestion_batch",
        record_id=batch_id,
        action_type="INSERT",
        actor_name=actor_name,
        payload={
            "olay": "ingest_tamamlandi",
            "tarih_id": tarih_id,
            "mutabakat": sonuc.mutabakat,
            "tablolar": audit_tablolar,
        },
    )
    return sonuc


def batch_onayla(
    conn: Connection, batch_id: int, actor_name: str = "system"
) -> list[str]:
    """Adım 5 (dokumanlar/01 §4): Faz 0'da onay UI'ı yok — bu fonksiyonun
    BİLİNÇLİ OLARAK çağrılması onay yerine geçer. epdk_aylik_isle()'ın
    is_active=false yazdığı HER fact tablosu için tek tek aktivasyon_yap()
    çağırır (P0-4), sonunda batch'i 'succeeded' yapar.

    Kasıtlı olarak yalnız `batch_id: int` alır, IslemSonucu DEĞİL — bu
    fonksiyon SIK SIK epdk_aylik_isle()'ı çağıran süreçten AYRI bir süreçte
    çağrılır (elle/gecikmeli onay: bir CLI — worker/scripts/onayla.py —, bir
    job kuyruğu, ya da bir insan; bkz. dokumanlar/06_canli_veri_operasyon_
    gunlugu.md). IslemSonucu bellek içi bir dataclass'tır (pandas DataFrame'ler
    içerir) ve süreç sınırını aşamaz; hangi tabloların aktive edileceği bu
    yüzden DB'den sorgulanır (ingest.batch_dolu_tablolari_bul), IslemSonucu.
    tablolar'ın anahtarlarından DEĞİL — ki zaten bu fonksiyon önceden de
    yalnız o anahtarları kullanıyordu, DataFrame içeriğine hiç dokunmuyordu.

    Aynı süreçte, epdk_aylik_isle()'ın döndürdüğü sonuc ile hemen ardından
    çağrılıyorsa (örn. worker/job_worker.py) `batch_onayla(conn, sonuc.batch_id)`
    şeklinde çağrılır — sonuc.batch_id zaten mevcuttur.

    `actor_name`: kim onayladı (worker/job_worker.py'nin otomatik yolu,
    worker/scripts/onayla.py'nin --actor'ı, ya da bir test) — audit_log'a
    düşer (2026-08-31'de bulunan boşluk: bu fonksiyon daha önce audit_log'a
    HİÇ yazmıyordu, bkz. dokumanlar/06_canli_veri_operasyon_gunlugu.md).

    Döndürdüğü liste, aktive edilen tablo adlarıdır (audit/log amaçlı)."""
    tablolar = ingest.batch_dolu_tablolari_bul(conn, batch_id)
    for tablo in tablolar:
        ingest.aktivasyon_yap(conn, tablo, batch_id)
    ingest.batch_durumu_guncelle(conn, batch_id, "succeeded")
    ingest.audit_log_yaz(
        conn,
        table_name="ingestion_batch",
        record_id=batch_id,
        action_type="UPDATE",
        actor_name=actor_name,
        payload={"olay": "batch_onaylandi", "aktive_edilen_tablolar": tablolar},
    )
    return tablolar


def kapsam_disi_isaretle(
    conn: Connection,
    *,
    tarih_id: int,
    fact_tablosu: str,
    sebep: str,
    karar_referansi: str,
    nitelik: str = "(tumu)",
) -> None:
    """Karar 1 (T13/fact_serbest_tuketici) ve Karar 3 (T1/fact_uretim
    Lisanslı) — dokumanlar/07_word_parser_kapsam.md — için beklenen
    "kaynakta yok" işaretleme mekanizması (migration 20260819_0012,
    `veri_kapsam_disi` tablosu).

    `ingestion_batch`'ten BİLİNÇLİ OLARAK bağımsızdır — bir dönem için o
    fact tablosunda hiçbir batch/yükleme girişimi bile olmayabilir (Word
    kaynağında T13 hiç aranmıyor, T1 için Word'de il×kaynak birleşik
    tablo hiç yok). Amaç: "parser hatası yüzünden 0 satır" ile "kaynakta
    gerçekten yok" durumunu KPI/dashboard seviyesinde her zaman ayırt
    edebilmek (bkz. Karar 1'in orijinal gerekçesi).

    `fact_tablosu` DB'deki CHECK kısıtıyla (aynı 4'lü whitelist —
    `worker/ingest.py`'nin `_DOGAL_ANAHTAR`'ıyla aynı tablolar) doğrulanır;
    burada AYRICA bir Python-taraflı liste TUTULMAZ (tek doğruluk kaynağı
    DB'de — Karar 1'in "paralel yol icat etme" ilkesi).

    `nitelik`: aynı fact tablosunun İÇİNDE kısmi kapsam dışılık olabilir
    (örn. Karar 3 — fact_uretim'in yalnız Lisanslı kesiti yok, Lisanssız
    var); varsayılan `'(tumu)'` tüm tablo bu dönem için kapsam dışı demektir.

    Aynı `(tarih_id, fact_tablosu, nitelik)` için İKİNCİ bir çağrı HATA
    FIRLATMAZ — UPSERT yapar (`sebep`/`karar_referansi` güncellenir,
    `created_at` yenilenir). Neden: bu fonksiyon tipik olarak bir backfill
    script'i içinde AYNI dönem için tekrar tekrar çağrılabilir (örn. bir
    yılın 12 ayı için döngüde) — "zaten var" durumunda patlamak yerine
    fikrini güncelleyebilmek (örn. gerekçe metni netleştiğinde) daha
    kullanışlı; bu tablo `ingestion_batch` gibi versiyonlu/append-only bir
    audit izi DEĞİL, GÜNCEL bir "durum" kaydı."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO veri_kapsam_disi
                (tarih_id, fact_tablosu, nitelik, sebep, karar_referansi)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (tarih_id, fact_tablosu, nitelik) DO UPDATE SET
                sebep = EXCLUDED.sebep,
                karar_referansi = EXCLUDED.karar_referansi,
                created_at = now()
            """,
            (tarih_id, fact_tablosu, nitelik, sebep, karar_referansi),
        )
