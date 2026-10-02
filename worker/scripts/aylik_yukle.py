"""EPP — Aylık EPDK yüklemesini TEK KOMUTA indirger (2026-10-02/03,
`Claude outputs/PROMPT_AYLIK_YUKLEME_SCRIPTI_2026-10-02.md`).

**Neden gerekli:** Temmuz 2026 yüklemesi öncesi (ve denemesi) elle 6 adım
gerektiriyordu (dosyayı bul, manifest'e ekle, kuyrukla, işle, mutabakat
kontrollerini çalıştır, batch id'lerini bulup elle onayla) — her ay
tekrarlanacak, hata payı yüksek bir süreç. Bu script üç ayrı batch
zincirini (ana EPDK akışı: fact_tuketim/abone/serbest_tuketici/uretim;
üretim kaynak/il kırılımı: fact_uretim_kaynak_geneli/il_geneli; tüketim
ülke-geneli: fact_tuketim_ulke_geneli) TEK çağrıda, sırayla ve ay-ay
ayrı ayrı aktive ederek işler — 2026-10-02'de tam da bu sıranın
bozulması (tüm ayları işleyip SONRA toplu aktive etmeye çalışmak)
Temmuz'un de-kümülatif hesabını kırıp 459 imkânsız negatif değer
üretmişti (bkz. `dokumanlar/06_canli_veri_operasyon_gunlugu.md`
2026-10-02 kaydı) — bu script o hata sınıfını YAPISAL olarak imkânsız
kılar (tek ay işler, üç zinciri de o ay için sırayla aktive eder,
"toplu işle sonra toplu aktive et" diye bir mod YOK).

**Yer tutucu YOK:** kaynak dosya EPDK Verileri klasöründe başlık
satırından bulunur (manifest/sabit yol gerekmez), parser_version
verilmezse önceki ayın ana-zincir batch'inden devralınır, batch id'leri
script'in kendi akışından gelir — Ahmet hiçbir kimlik elle girmez.

Kullanım:
    python -m worker.scripts.aylik_yukle --ay 202607
        (varsayılan: --dry-run — HİÇBİR ŞEY YAZILMAZ, ne yapılacağı
        tam sadakatle gösterilir: aynı transaction içinde GERÇEKTEN
        işlenir, sonunda ROLLBACK edilir)
    python -m worker.scripts.aylik_yukle --ay 202607 --uygula \\
        --negatif-red-esigi 2
        (disposable'da ölçülmüş beklenen değer — bkz. kapanış raporu)
    python -m worker.scripts.aylik_yukle --ay 202607 --uygula \\
        --negatif-red-esigi 2 --elle-onay "bilinen T7 çok-sütunlu boşluk"
        (otomatik_onaya_uygun()/periyot_aktivasyona_uygun_mu() False
        dönerse gerekçeli elle onayla aktive et)

Durma kuralları (her biri `DurdurmaHatasi` fırlatır, exit code 1):
- Kaynak dosya 0 veya 1'den fazla eşleşiyorsa (tahmin edilmez).
- Yedek 24 saatten eskiyse/doğrulanamıyorsa (`--yedek-atla "<gerekçe>"`
  ile bilinçli geçilir — gerekçesiz geçiş YOK).
- Herhangi bir zincirde toplam red satırı `--negatif-red-esigi`'yi
  aşarsa (varsayılan 0) — batch `onay_bekliyor`a düşer, sonraki
  zincire/aya GEÇİLMEZ.
- `otomatik_onaya_uygun()`/`periyot_aktivasyona_uygun_mu()` False
  dönüp `--elle-onay "<gerekçe>"` verilmemişse.
- İşlem sonunda hedef ay DIŞINDA herhangi bir ayda satır sayısı
  değiştiyse (beklenmez, ama sessizce geçilmez — bkz. `--uygula`
  sonrası özet).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import openpyxl
import psycopg
import requests

from worker import ingest, pipeline
from worker.db import get_database_url
from worker.scripts import mutabakat_uretim

_REPO = "ahmet-damar/epp-elektrik-piyasasi"
_YEDEK_WORKFLOW = "scheduled-backup.yml"
_VARSAYILAN_YEDEK_MAX_YAS_SAAT = 24
_API_ZAMAN_ASIMI_SN = 15
_URETIM_PARSER_VERSION = "excel-uretim-geneli-v1"
_ULKE_GENELI_PARSER_VERSION = "excel-ulke-geneli-v1"

_FACT_TABLOLARI = [
    "fact_tuketim",
    "fact_abone",
    "fact_serbest_tuketici",
    "fact_uretim",
    "fact_tuketim_ulke_geneli",
    "fact_uretim_kaynak_geneli",
    "fact_uretim_il_geneli",
]


class DurdurmaHatasi(RuntimeError):
    """Script'in KASITLI olarak durması gerektiğinde fırlatılır — bir
    güvenlik/kalite kararının sonucu, beklenmeyen bir programlama hatası
    DEĞİL. main() bunu yakalayıp exit code 1 ile net bir mesaj basar."""


def _ay_bilgisi(tarih_id: int) -> tuple[int, int, str, str]:
    yil, ay = divmod(tarih_id, 100)
    if not (1 <= ay <= 12):
        raise DurdurmaHatasi(
            f"--ay geçersiz: {tarih_id} (YYYYMM bekleniyor, örn. 202607)"
        )
    ay_adi = ingest.AY_ADLARI[ay]
    source_period = f"{yil}-{ay:02d}"
    return yil, ay, ay_adi, source_period


def _onceki_tarih_id(tarih_id: int) -> int:
    yil, ay = divmod(tarih_id, 100)
    return (yil - 1) * 100 + 12 if ay == 1 else yil * 100 + (ay - 1)


def _turkce_buyuk_harf(metin: str) -> str:
    """Python'ın yerleşik `str.upper()`'ı Türkçe-bilmez: küçük 'i'yi ASCII
    'I' (noktasız) yapar, gerçek Türkçe büyük hâli 'İ' (noktalı) olması
    gerekirken — klasik "Turkish I problem". `kaynak_dosya_bul()`'da bu
    yüzden NİSAN/EKİM gibi 'i' içeren ay adları GERÇEK dosyadaki (doğru
    Türkçe büyük harfli) başlıkla hiç eşleşmiyordu (gerçek dosyaya karşı
    ÖLÇÜLEREK bulundu, 2026-10-03) — küçük 'i'/'ı' çevrimi `upper()`'dan
    ÖNCE elle yapılır."""
    return metin.replace("i", "İ").replace("ı", "I").upper()


def kaynak_dosya_bul(dizin: Path, yil: int, ay_adi: str) -> Path:
    """EPDK Verileri klasöründeki TÜM `.xlsx` dosyalarını açar, ilk
    sayfanın başlık satırında `'{AY_ADI} {YIL}'` geçen TEK dosyayı
    bulur — gerçek dosya adları rastgele portal-üretimi hash'ler
    taşıdığından (bkz. `worker/scripts/backfill.py` modül notu) isim
    eşleştirmesi YAPILAMAZ, içerik okunur. Sıfır veya birden fazla
    eşleşme KASITLI OLARAK tahmin edilmez — ikisi de `DurdurmaHatasi`."""
    hedef = f"{_turkce_buyuk_harf(ay_adi)} {yil}"
    eslesenler: list[Path] = []
    for yol in sorted(dizin.glob("*.xlsx")):
        try:
            wb = openpyxl.load_workbook(yol, data_only=True, read_only=True)
        except Exception:  # noqa: BLE001, S112 - bozuk/kilitli dosya atlanır, çökmez
            continue
        baslik = None
        try:
            ws = wb[wb.sheetnames[0]]
            for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
                for deger in row:
                    if deger:
                        baslik = str(deger)
                        break
                if baslik:
                    break
        finally:
            wb.close()
        if baslik and hedef in _turkce_buyuk_harf(baslik):
            eslesenler.append(yol)
    if not eslesenler:
        raise DurdurmaHatasi(
            f"'{hedef}' başlığını içeren hiçbir .xlsx bulunamadı ({dizin})"
        )
    if len(eslesenler) > 1:
        raise DurdurmaHatasi(
            f"'{hedef}' başlığıyla BİRDEN FAZLA dosya eşleşti (tahmin "
            f"edilmedi, elle seç gerekiyor): {[str(p) for p in eslesenler]}"
        )
    return eslesenler[0]


def son_basarili_yedek_yasi() -> timedelta | None:
    """GitHub Actions REST API'sinden (repo PUBLIC, token gerekmez — bkz.
    `gh repo view --json visibility`) son BAŞARILI `scheduled-backup.yml`
    koşusunun ne kadar önce bittiğini döner. API'ye ulaşılamazsa veya hiç
    başarılı koşu yoksa `None` döner — çağıran bunu 'doğrulanamadı' sayıp
    ESKİ gibi davranmalı (fail-closed, 2026-09/10 oturumlarının "ölçülmeden
    varsayma" hatalarıyla aynı sınıfa düşmemek için)."""
    url = (
        f"https://api.github.com/repos/{_REPO}/actions/workflows/{_YEDEK_WORKFLOW}/runs"
    )
    try:
        yanit = requests.get(
            url,
            params={"status": "success", "per_page": "1"},
            headers={"Accept": "application/vnd.github+json"},
            timeout=_API_ZAMAN_ASIMI_SN,
        )
        yanit.raise_for_status()
        kosular = yanit.json().get("workflow_runs", [])
        if not kosular:
            return None
        bitis_metni = kosular[0].get("updated_at") or kosular[0].get("created_at")
        bitis = datetime.fromisoformat(bitis_metni.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - bitis
    except Exception:  # noqa: BLE001 - ağ/API hatası "doğrulanamadı" sayılır
        return None


def durum_fotografi(conn: psycopg.Connection) -> dict[str, Any]:
    """Fact tabloları (toplam/aktif), ay bazlı aktif sayımlar,
    `ingestion_batch` durum dağılımı, `audit_log` sayısı — önce/sonra
    karşılaştırması için. Yalnız `select`, hiçbir satırı değiştirmez."""
    foto: dict[str, Any] = {"tablolar": {}, "ay_bazli": {}, "batch_durumlari": {}}
    with conn.cursor() as cur:
        for tablo in _FACT_TABLOLARI:
            sorgu = f"select count(*), count(*) filter (where is_active) from {tablo}"  # nosec B608 - tablo adı _FACT_TABLOLARI sabit listesinden
            cur.execute(sorgu)
            satir = cur.fetchone()
            assert satir is not None
            foto["tablolar"][tablo] = {"toplam": satir[0], "aktif": satir[1]}
            cur.execute(
                f"select tarih_id, count(*) from {tablo} where is_active group by tarih_id"  # nosec B608
            )
            foto["ay_bazli"][tablo] = dict(cur.fetchall())
        cur.execute("select status, count(*) from ingestion_batch group by status")
        foto["batch_durumlari"] = dict(cur.fetchall())
        cur.execute("select count(*) from audit_log")
        satir = cur.fetchone()
        assert satir is not None
        foto["audit_log_sayisi"] = satir[0]
    return foto


def fotograf_farkini_dogrula(
    once: dict[str, Any], sonra: dict[str, Any], hedef_tarih_id: int
) -> list[str]:
    """Hedef ay DIŞINDA herhangi bir ayda satır sayısı değiştiyse bunu
    listeler — boş liste "0 fark" demektir. Dry-run'da (rollback) bu
    HER ZAMAN boş olmalı; `--uygula`'da yalnız hedef ay değişmeli."""
    sorunlar: list[str] = []
    for tablo in _FACT_TABLOLARI:
        once_ay = once["ay_bazli"].get(tablo, {})
        sonra_ay = sonra["ay_bazli"].get(tablo, {})
        for ay in set(once_ay) | set(sonra_ay):
            if ay == hedef_tarih_id:
                continue
            if once_ay.get(ay, 0) != sonra_ay.get(ay, 0):
                sorunlar.append(
                    f"{tablo} tarih_id={ay}: {once_ay.get(ay, 0)} -> "
                    f"{sonra_ay.get(ay, 0)} (BEKLENMİYORDU)"
                )
    return sorunlar


def onceki_ay_parser_version(conn: psycopg.Connection, tarih_id: int) -> str | None:
    """Ana zincirin (fact_tuketim'e yazan) önceki ay batch'inin
    parser_version'ını döner — `fact_tuketim`'e yazmış olmak, AYRI
    zincirlerin (`excel-ulke-geneli-v1`/`excel-uretim-geneli-v1`, kendi
    sabit version string'leri var) bu sorguya YANLIŞLIKLA karışmasını
    engeller. Önceki ay hiç işlenmemişse `None` (çağıran varsayılana
    döner)."""
    onceki = _onceki_tarih_id(tarih_id)
    onceki_period = f"{onceki // 100}-{onceki % 100:02d}"
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ib.parser_version
            FROM ingestion_batch ib
            JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
            WHERE sa.source_type = 'epdk_aylik' AND sa.source_period = %s
              AND EXISTS (
                  SELECT 1 FROM fact_tuketim ft WHERE ft.ingestion_batch_id = ib.batch_id
              )
            ORDER BY ib.batch_id DESC LIMIT 1
            """,
            (onceki_period,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _toplam_red(sonuc: pipeline.IslemSonucu) -> int:
    return sum(t.red for t in sonuc.tablolar.values())


def _batch_durumu_getir(conn: psycopg.Connection, batch_id: int) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM ingestion_batch WHERE batch_id = %s", (batch_id,)
        )
        row = cur.fetchone()
    return row[0] if row else "bulunamadı"


def _mevcut_batch_id_bul(
    conn: psycopg.Connection, source_period: str, parser_version: str
) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ib.batch_id FROM ingestion_batch ib
            JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
            WHERE sa.source_type = 'epdk_aylik' AND sa.source_period = %s
              AND ib.parser_version = %s
            ORDER BY ib.batch_id DESC LIMIT 1
            """,
            (source_period, parser_version),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _zaten_var_sonucu(
    conn: psycopg.Connection, *, zincir: str, batch_id: int | None
) -> dict[str, Any]:
    """`sahiplenildi=False`/`sonuc is None` — bu ay için bu zincir DAHA ÖNCE
    denenmiş. `succeeded` ise gerçekten bitmiş (sorun yok, devam edilir);
    BAŞKA bir durumdaysa (örn. `onay_bekliyor` — önceki bir koşu eşik/onay
    gerektirmişti ama hiç çözülmemiş) bunu SESSİZCE 'zaten işlenmiş' SAYMAK
    YANLIŞ olurdu — DURDU olarak işaretlenir, elle incelenmesi istenir."""
    if batch_id is None:
        return {
            "zincir": zincir,
            "durum": "DURDU_onceki_deneme_bulunamadi",
            "sebep": "sahiplenilmiş ama batch_id bulunamadı",
        }
    durum = _batch_durumu_getir(conn, batch_id)
    if durum == "succeeded":
        return {"zincir": zincir, "durum": "zaten_islenmis", "batch_id": batch_id}
    return {
        "zincir": zincir,
        "durum": "DURDU_onceki_deneme_cozulmemis",
        "batch_id": batch_id,
        "sebep": f"batch_id={batch_id} zaten var ama durumu '{durum}' (succeeded DEĞİL) — elle incele",
    }


def _esik_asimi_isle(
    conn: psycopg.Connection, *, batch_id: int, toplam_red: int, esik: int, actor: str
) -> str:
    sebep = f"negatif red eşiği aşıldı: beklenen<={esik}, gerçek={toplam_red}"
    ingest.batch_durumu_guncelle(conn, batch_id, "onay_bekliyor", error_summary=sebep)
    ingest.audit_log_yaz(
        conn,
        table_name="ingestion_batch",
        record_id=batch_id,
        action_type="UPDATE",
        actor_name=actor,
        payload={
            "olay": "onay_bekliyor",
            "sebep": sebep,
            "kontrol": "aylik_yukle.negatif_red_esigi",
        },
    )
    return sebep


def _onay_bekliyor_isle(
    conn: psycopg.Connection, *, batch_id: int, sebep: str, actor: str
) -> None:
    ingest.batch_durumu_guncelle(conn, batch_id, "onay_bekliyor", error_summary=sebep)
    ingest.audit_log_yaz(
        conn,
        table_name="ingestion_batch",
        record_id=batch_id,
        action_type="UPDATE",
        actor_name=actor,
        payload={
            "olay": "onay_bekliyor",
            "sebep": sebep,
            "kontrol": "pipeline.otomatik_onaya_uygun",
        },
    )


def _elle_onay_isle(
    conn: psycopg.Connection, *, batch_id: int, sebep: str, gerekce: str, actor: str
) -> None:
    pipeline.batch_onayla(conn, batch_id, actor_name=actor)
    ingest.audit_log_yaz(
        conn,
        table_name="ingestion_batch",
        record_id=batch_id,
        action_type="UPDATE",
        actor_name=actor,
        payload={
            "olay": "elle_onay",
            "sebep": sebep,
            "gerekce": gerekce,
            "kontrol": "aylik_yukle.--elle-onay",
        },
    )


def ana_zincir_isle(
    conn: psycopg.Connection,
    *,
    dosya_adi: str,
    icerik: bytes,
    tarih_id: int,
    source_period: str,
    parser_version: str,
    negatif_red_esigi: int,
    elle_onay: str | None,
    actor: str,
) -> dict[str, Any]:
    """fact_tuketim/fact_abone/fact_serbest_tuketici/fact_uretim (T1/T4/
    T10/T11/T13) — Faz 0 SENKRON yolu (`epdk_aylik_isle`) kullanılır,
    Faz 1'in job_status kuyruğu BİLEREK atlanır (bu script senkron
    çalışır, ayrı bir worker süreci beklemeye gerek yok). `uploaded_by`
    BİLEREK verilmiyor (`db/schema.sql`'de UUID tipi — `--actor` özgür
    metin, bir kullanıcı UUID'si DEĞİL); bu adımın kendi `audit_log`
    kaydı bu yüzden sabit "system:epdk_aylik_isle" etiketiyle düşer,
    `--actor` yalnız BU fonksiyonun SONRAKİ (onay/durma) adımlarında
    kullanılır."""
    sonuc = pipeline.epdk_aylik_isle(
        conn,
        dosya_adi=dosya_adi,
        icerik=icerik,
        tarih_id=tarih_id,
        source_period=source_period,
        parser_version=parser_version,
        schema_version="1",
    )
    if not sonuc.sahiplenildi:
        return _zaten_var_sonucu(conn, zincir="ana", batch_id=sonuc.batch_id)
    if sonuc.eksik_tablolar:
        raise DurdurmaHatasi(f"ana zincir: eksik tablo(lar): {sonuc.eksik_tablolar}")

    toplam_red = _toplam_red(sonuc)
    if toplam_red > negatif_red_esigi:
        sebep = _esik_asimi_isle(
            conn,
            batch_id=sonuc.batch_id,
            toplam_red=toplam_red,
            esik=negatif_red_esigi,
            actor=actor,
        )
        return {
            "zincir": "ana",
            "durum": "DURDU_esik_asimi",
            "batch_id": sonuc.batch_id,
            "sebep": sebep,
            "toplam_red": toplam_red,
        }

    uygun, sebep = pipeline.otomatik_onaya_uygun(sonuc)
    if uygun:
        pipeline.batch_onayla(conn, sonuc.batch_id, actor_name=actor)
        return {
            "zincir": "ana",
            "durum": "aktive_edildi",
            "batch_id": sonuc.batch_id,
            "toplam_red": toplam_red,
        }
    if elle_onay:
        _elle_onay_isle(
            conn, batch_id=sonuc.batch_id, sebep=sebep, gerekce=elle_onay, actor=actor
        )
        return {
            "zincir": "ana",
            "durum": "aktive_edildi_elle_onay",
            "batch_id": sonuc.batch_id,
            "sebep": sebep,
            "toplam_red": toplam_red,
        }
    _onay_bekliyor_isle(conn, batch_id=sonuc.batch_id, sebep=sebep, actor=actor)
    return {
        "zincir": "ana",
        "durum": "DURDU_elle_onay_gerekli",
        "batch_id": sonuc.batch_id,
        "sebep": sebep,
        "toplam_red": toplam_red,
    }


def uretim_zincir_isle(
    conn: psycopg.Connection,
    *,
    wb: openpyxl.Workbook,
    tarih_id: int,
    dosya_adi: str,
    icerik: bytes,
    source_period: str,
    negatif_red_esigi: int,
    elle_onay: str | None,
    actor: str,
) -> dict[str, Any]:
    """fact_uretim_kaynak_geneli + fact_uretim_il_geneli (T2/T3/T5/T6) —
    aktivasyon kapısı `otomatik_onaya_uygun()` DEĞİL, `mutabakat_uretim.
    periyot_aktivasyona_uygun_mu()` (kaynak↔il çapraz toplamı) — bkz.
    `worker/pipeline.py:isle_ay_uretim_excel()` modül notu."""
    sonuc = pipeline.isle_ay_uretim_excel(
        conn,
        wb=wb,
        tarih_id=tarih_id,
        dosya_adi=dosya_adi,
        icerik=icerik,
        source_period=source_period,
        actor_name=actor,
        parser_version=_URETIM_PARSER_VERSION,
    )
    if sonuc is None:
        batch_id = _mevcut_batch_id_bul(conn, source_period, _URETIM_PARSER_VERSION)
        return _zaten_var_sonucu(conn, zincir="uretim_geneli", batch_id=batch_id)

    toplam_red = _toplam_red(sonuc)
    if toplam_red > negatif_red_esigi:
        sebep = _esik_asimi_isle(
            conn,
            batch_id=sonuc.batch_id,
            toplam_red=toplam_red,
            esik=negatif_red_esigi,
            actor=actor,
        )
        return {
            "zincir": "uretim_geneli",
            "durum": "DURDU_esik_asimi",
            "batch_id": sonuc.batch_id,
            "sebep": sebep,
            "toplam_red": toplam_red,
        }

    uygun, sebep = mutabakat_uretim.periyot_aktivasyona_uygun_mu(conn, tarih_id)
    if uygun:
        pipeline.batch_onayla(conn, sonuc.batch_id, actor_name=actor)
        return {
            "zincir": "uretim_geneli",
            "durum": "aktive_edildi",
            "batch_id": sonuc.batch_id,
            "toplam_red": toplam_red,
        }
    if elle_onay:
        _elle_onay_isle(
            conn, batch_id=sonuc.batch_id, sebep=sebep, gerekce=elle_onay, actor=actor
        )
        return {
            "zincir": "uretim_geneli",
            "durum": "aktive_edildi_elle_onay",
            "batch_id": sonuc.batch_id,
            "sebep": sebep,
            "toplam_red": toplam_red,
        }
    mutabakat_uretim.mutabakat_reddini_kaydet(
        conn, batch_id=sonuc.batch_id, tarih_id=tarih_id, sebep=sebep, actor_name=actor
    )
    return {
        "zincir": "uretim_geneli",
        "durum": "DURDU_mutabakat_reddi",
        "batch_id": sonuc.batch_id,
        "sebep": sebep,
        "toplam_red": toplam_red,
    }


def ulke_geneli_zincir_isle(
    conn: psycopg.Connection,
    *,
    wb: openpyxl.Workbook,
    tarih_id: int,
    dosya_adi: str,
    icerik: bytes,
    source_period: str,
    negatif_red_esigi: int,
    elle_onay: str | None,
    actor: str,
) -> dict[str, Any]:
    """fact_tuketim_ulke_geneli (T11'in Genel Toplam satırı, de-kümülatif)
    — `isle_ay_ulke_geneli_excel()` HİÇBİR ZAMAN kendi aktive ETMEZ (bkz.
    fonksiyonun kendi modül notu), aktivasyon kararı burada verilir."""
    sonuc = pipeline.isle_ay_ulke_geneli_excel(
        conn,
        wb=wb,
        tarih_id=tarih_id,
        dosya_adi=dosya_adi,
        icerik=icerik,
        source_period=source_period,
        actor_name=actor,
        parser_version=_ULKE_GENELI_PARSER_VERSION,
    )
    if sonuc is None:
        batch_id = _mevcut_batch_id_bul(
            conn, source_period, _ULKE_GENELI_PARSER_VERSION
        )
        return _zaten_var_sonucu(conn, zincir="ulke_geneli", batch_id=batch_id)

    toplam_red = _toplam_red(sonuc)
    if toplam_red > negatif_red_esigi:
        sebep = _esik_asimi_isle(
            conn,
            batch_id=sonuc.batch_id,
            toplam_red=toplam_red,
            esik=negatif_red_esigi,
            actor=actor,
        )
        return {
            "zincir": "ulke_geneli",
            "durum": "DURDU_esik_asimi",
            "batch_id": sonuc.batch_id,
            "sebep": sebep,
            "toplam_red": toplam_red,
        }

    uygun, sebep = pipeline.otomatik_onaya_uygun(sonuc)
    if uygun:
        pipeline.batch_onayla(conn, sonuc.batch_id, actor_name=actor)
        return {
            "zincir": "ulke_geneli",
            "durum": "aktive_edildi",
            "batch_id": sonuc.batch_id,
            "toplam_red": toplam_red,
        }
    if elle_onay:
        _elle_onay_isle(
            conn, batch_id=sonuc.batch_id, sebep=sebep, gerekce=elle_onay, actor=actor
        )
        return {
            "zincir": "ulke_geneli",
            "durum": "aktive_edildi_elle_onay",
            "batch_id": sonuc.batch_id,
            "sebep": sebep,
            "toplam_red": toplam_red,
        }
    _onay_bekliyor_isle(conn, batch_id=sonuc.batch_id, sebep=sebep, actor=actor)
    return {
        "zincir": "ulke_geneli",
        "durum": "DURDU_elle_onay_gerekli",
        "batch_id": sonuc.batch_id,
        "sebep": sebep,
        "toplam_red": toplam_red,
    }


def calistir(
    conn: psycopg.Connection,
    *,
    yol: Path,
    tarih_id: int,
    source_period: str,
    parser_version: str,
    uygula: bool,
    negatif_red_esigi: int,
    elle_onay: str | None,
    actor: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Üç zinciri SIRAYLA işler — biri DURursa (`durum` "DURDU" ile
    başlıyorsa) sonrakine HİÇ geçilmez (ama `calistir()` normal döner,
    fırlatmaz — "DURDU" da geçerli, incelenebilir bir sonuçtur; çağıran
    `main()` bunu `sonuclar`'dan okuyup exit code'a çevirir). `uygula=
    False` ise aynı transaction'da gerçekten işlenir ama sonunda
    ROLLBACK edilir (tam sadakatli dry-run — bkz. modül notu); `uygula=
    True` ise COMMIT edilir. Dönen ikinci eleman, hedef ay dışındaki
    farklardır (`uygula=False`'ta her zaman boş olmalı)."""
    icerik = yol.read_bytes()
    wb = openpyxl.load_workbook(yol, data_only=True)

    once = durum_fotografi(conn)
    sonuclar: list[dict[str, Any]] = []
    try:
        r1 = ana_zincir_isle(
            conn,
            dosya_adi=yol.name,
            icerik=icerik,
            tarih_id=tarih_id,
            source_period=source_period,
            parser_version=parser_version,
            negatif_red_esigi=negatif_red_esigi,
            elle_onay=elle_onay,
            actor=actor,
        )
        sonuclar.append(r1)

        if not r1["durum"].startswith("DURDU"):
            r2 = uretim_zincir_isle(
                conn,
                wb=wb,
                tarih_id=tarih_id,
                dosya_adi=yol.name,
                icerik=icerik,
                source_period=source_period,
                negatif_red_esigi=negatif_red_esigi,
                elle_onay=elle_onay,
                actor=actor,
            )
            sonuclar.append(r2)

            if not r2["durum"].startswith("DURDU"):
                r3 = ulke_geneli_zincir_isle(
                    conn,
                    wb=wb,
                    tarih_id=tarih_id,
                    dosya_adi=yol.name,
                    icerik=icerik,
                    source_period=source_period,
                    negatif_red_esigi=negatif_red_esigi,
                    elle_onay=elle_onay,
                    actor=actor,
                )
                sonuclar.append(r3)
    finally:
        if uygula:
            conn.commit()
        else:
            conn.rollback()

    sonra = durum_fotografi(conn)
    farklar = fotograf_farkini_dogrula(once, sonra, tarih_id)
    return sonuclar, farklar


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--ay", type=int, required=True, help="tarih_id, örn. 202607")
    ap.add_argument(
        "--uygula",
        action="store_true",
        help="gerçekten yaz (varsayılan: dry-run, HİÇBİR ŞEY YAZILMAZ)",
    )
    ap.add_argument(
        "--kaynak-dizin",
        type=Path,
        default=Path("/epdk-verileri"),
        help="EPDK Verileri klasörü",
    )
    ap.add_argument(
        "--parser-version",
        default=None,
        help="verilmezse önceki ayın ana-zincir batch'inden devralınır",
    )
    ap.add_argument(
        "--negatif-red-esigi",
        type=int,
        default=0,
        help="varsayılan 0 — her ay için elle ölçülüp geçilmeli",
    )
    ap.add_argument("--elle-onay", default=None, metavar="GEREKÇE")
    ap.add_argument("--yedek-atla", default=None, metavar="GEREKÇE")
    ap.add_argument(
        "--yedek-max-yas-saat", type=int, default=_VARSAYILAN_YEDEK_MAX_YAS_SAAT
    )
    ap.add_argument("--actor", default="manual-cli:aylik-yukle")
    args = ap.parse_args()

    if args.elle_onay is not None and not args.elle_onay.strip():
        print("HATA: --elle-onay gerekçeli verilmeli (boş olamaz).")
        return 1
    if args.yedek_atla is not None and not args.yedek_atla.strip():
        print("HATA: --yedek-atla gerekçeli verilmeli (boş olamaz).")
        return 1

    try:
        yil, _ay, ay_adi, source_period = _ay_bilgisi(args.ay)
        yol = kaynak_dosya_bul(args.kaynak_dizin, yil, ay_adi)
        print(
            f"[BULUNDU] {yol.name} -> {_turkce_buyuk_harf(ay_adi)} {yil} (tarih_id={args.ay})"
        )

        if args.yedek_atla:
            print(f"[YEDEK] kontrolü ATLANDI — gerekçe: {args.yedek_atla}")
        else:
            yas = son_basarili_yedek_yasi()
            if yas is None:
                raise DurdurmaHatasi(
                    "yedek tazeliği DOĞRULANAMADI (GitHub API'ye ulaşılamadı veya hiç "
                    'başarılı koşu yok) — --yedek-atla "<gerekçe>" ile bilinçli geç'
                )
            if yas.total_seconds() > args.yedek_max_yas_saat * 3600:
                raise DurdurmaHatasi(
                    f"son başarılı yedek {yas} önce — {args.yedek_max_yas_saat} saatten ESKİ. "
                    '--yedek-atla "<gerekçe>" ile bilinçli geç'
                )
            print(f"[YEDEK] tazelik doğrulandı: {yas} önce")

        database_url = get_database_url()
        if not database_url:
            raise DurdurmaHatasi("DATABASE_URL tanımlı değil")

        # prepare_threshold=None: bkz. worker/db.py:get_db_connection() — pooler uyumu.
        with psycopg.connect(database_url, prepare_threshold=None) as conn:
            if args.parser_version:
                parser_version = args.parser_version
                print(f"[PARSER_VERSION] elle verildi: {parser_version}")
            else:
                onceki = onceki_ay_parser_version(conn, args.ay)
                parser_version = onceki or "0.1"
                if onceki:
                    print(f"[PARSER_VERSION] önceki aydan devralındı: {parser_version}")
                else:
                    print(
                        f"[PARSER_VERSION] önceki ay bulunamadı, varsayılan: {parser_version}"
                    )

            if not args.uygula:
                print(
                    "\n=== DRY-RUN — gerçek transaction'da işlenip sonunda ROLLBACK edilecek ==="
                )

            sonuclar, farklar = calistir(
                conn,
                yol=yol,
                tarih_id=args.ay,
                source_period=source_period,
                parser_version=parser_version,
                uygula=args.uygula,
                negatif_red_esigi=args.negatif_red_esigi,
                elle_onay=args.elle_onay,
                actor=args.actor,
            )

        print(
            f"\n=== {'UYGULANDI' if args.uygula else 'DRY-RUN SONUCU (hiçbir şey yazılmadı)'} ==="
        )
        for r in sonuclar:
            print(f"  {r}")

        if farklar:
            print("\n[HATA] HEDEF AY DIŞINDA FARK BULUNDU:")
            for f in farklar:
                print(f"  {f}")
            return 1
        print("\n[OK] Diğer aylarda 0 fark.")

        if any(r["durum"].startswith("DURDU") for r in sonuclar):
            return 1
        return 0

    except DurdurmaHatasi as e:
        print(f"\n[DURDU] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
