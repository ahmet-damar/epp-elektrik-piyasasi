"""EPP — 2023 Word (.docx) EPDK aylık raporları: TEK SEFERLİK tarihsel
aktarım tarifi. Bkz. dokumanlar/07_word_parser_kapsam.md ("Mimari Kapsam
Netliği", Karar 1, Karar 2) ve worker/scripts/word_2024.py (aynı desenin
2024'e özel hali — bu dosya onun BİREBİR yapısal kopyası, kod paylaşımı
yerine YIL BAZLI AYRI TARİF ilkesi bilinçli olarak tercih edildi).

Kapsam (bu turda): T11-karşılığı → fact_tuketim (Sanayi HARİÇ, Karar 2),
T10-karşılığı → fact_abone (Sanayi DAHİL). T13/T1/T4-karşılığı BU TURDA YOK
(Karar 1, T1/T4 henüz incelenmedi).

**2023'e özgü bulgu (2024'ten farklı):** 2023 içinde EN AZ İKİ etiket-
varyantı var — Ocak/Şubat "Kamu ve Özel Hiz. Sek. ile Diğer" /
"Kamu/Özel Hiz. Sek./Diğer" gibi kısaltmalar kullanırken, Eylül 2024'ün
Mart ayıyla BİREBİR AYNI tam-uzun etiketleri/tablo numaralandırmasını
kullanıyor ("Tablo 5.2" T10, "Kamu/Özel/Diğer" T10 tür etiketi). Bu, 2023
içinde bir şablon geçişine işaret ediyor (ne zaman geçtiği belirsiz) —
_GRUP_TAKMA_ADLAR bu yüzden 2024'ten daha kalabalık; yeni bir ay yeni bir
varyant getirirse grup_esle_zorunlu() yine SESSİZCE DÜŞÜRMEZ, ValueError
fırlatır.

Dosya→ay eşlemesi (MANIFEST_2023): word_2024.py'nin zipfile+regex
taramasıyla AYNI yöntemle bulundu — bu kez dosyanın kendi başlık sayfasında
doğrudan "{AY}2023" (örn. "OCAK2023") deseni arandı (2024 dosyalarından
farklı olarak 2023 dosyaları başlık sayfasında kendi dönemini DOĞRUDAN
yazıyor). Her giriş yine isle_ay() içinde kendi T11-karşılığı başlığından
(_ay_yil_dogrula) BİR DAHA doğrulanır.

Kullanım:
    python -m worker.scripts.word_2023 --ay 9                  # tek ay, gerçek yükleme
    python -m worker.scripts.word_2023                          # 2023'ün TÜMÜ
    python -m worker.scripts.word_2023 --dry-run                # yalnız parse, DB'ye YAZMA
"""

from __future__ import annotations

import argparse
import re
import sys
from io import BytesIO
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from docx import Document

from worker import ingest, kpi, pipeline
from worker.db import get_database_url  # import yan etkisi: .env yüklenir
from worker.parser import grup_esle as _excel_grup_esle
from worker.parser import il_kodu_bul, parse_sayi
from worker.scripts.word_ortak import (
    basliklari_topla,
    hedef_donem_kolonu_bul,
    tek_aday_bul,
)

KLASOR_VARSAYILAN = Path(r"C:\Users\adama\Downloads\EPDK Verileri")

# ay(int) -> dosya adı. Bkz. modül notu — her giriş isle_ay() içinde kendi
# başlığından yeniden doğrulanır.
MANIFEST_2023: dict[int, str] = {
    1: "_PortalAdmin_Uploads_Content_FastAccess_e2cde10c50359.docx",
    2: "_PortalAdmin_Uploads_Content_FastAccess_40fd93b367429.docx",
    3: "_PortalAdmin_Uploads_Content_FastAccess_ea4bdbe288373.docx",
    4: "_PortalAdmin_Uploads_Content_FastAccess_db2b7c9e28185.docx",
    5: "_PortalAdmin_Uploads_Content_FastAccess_ab5f528241673.docx",
    6: "_PortalAdmin_Uploads_Content_FastAccess_1e16f2f785735.docx",
    7: "_PortalAdmin_Uploads_Content_FastAccess_c9d49f7336385.docx",
    8: "_PortalAdmin_Uploads_Content_FastAccess_205d90e755150.docx",
    9: "_PortalAdmin_Uploads_Content_FastAccess_d01b291581609.docx",
    10: "_PortalAdmin_Uploads_Content_FastAccess_71fd755766750.docx",
    11: "_PortalAdmin_Uploads_Content_FastAccess_2e27e2f775576.docx",
    12: "_PortalAdmin_Uploads_Content_FastAccess_c3ba04c814964.docx",
}

# 2023 içinde en az iki şablon-dönemi var (bkz. modül notu) — bu yüzden
# 2024'ten daha kalabalık bir takma-ad listesiyle başlıyoruz. worker/parser.py
# DEĞİŞTİRİLMEDİ (mimari karar). YENİ bir ay YENİ bir varyant getirirse
# grup_esle_zorunlu() ValueError fırlatır — buraya elle eklenmesi gerekir.
_GRUP_TAKMA_ADLAR = {
    "Kamu ve Özel Hiz. Sek. ile Diğer": "Kamu ve Özel Hizmetler",  # Ocak/Şubat 2023 T11
    "Kamu/Özel Hiz. Sek./Diğer": "Kamu ve Özel Hizmetler",  # Şubat 2023 T11 (Ocak'tan da farklı!)
    "Kamu/Özel/Diğer": "Kamu ve Özel Hizmetler",  # Eylül 2023 T10 (2024 Mart ile aynı)
    "Kamu/Özel/ Diğer": "Kamu ve Özel Hizmetler",  # Nisan 2023 T10 (araya boşluk sızmış)
}
# Toplam/özet satırları VE T11'in "Pay" yüzde-sütunu — grup DEĞİL, atlanması
# gereken hücreler (satır ya da kolon başlığı olarak görülebilir).
_ATLA_ETIKETLERI = {"Genel Toplam", "Toplam", "İl Toplam", "Türkiye", "TÜRKİYE", "Pay"}


def grup_esle_zorunlu(metin: str) -> str | None:
    """None → bilinen bir 'atla' etiketi (toplam/özet satırı, veri değil).
    Aksi halde eşleşme bulunamazsa ValueError — sürpriz sessizce geçilmez."""
    temiz = metin.strip()
    if temiz in _ATLA_ETIKETLERI:
        return None
    if temiz in _GRUP_TAKMA_ADLAR:
        return _GRUP_TAKMA_ADLAR[temiz]
    grup = _excel_grup_esle(temiz)
    if grup is None:
        raise ValueError(
            f"Tanınmayan tüketici grubu etiketi: {temiz!r} — "
            "worker/scripts/word_2023.py: _GRUP_TAKMA_ADLAR'a eklenmeli mi "
            "kontrol et (yeni bir ay yeni bir kısaltma getirmiş olabilir)."
        )
    return grup


_SIRKUMFLEKS_DUZELT = str.maketrans("ÂâÎîÛû", "AaİiUu")


def _il_adi_temizle(il_adi_ham: str) -> str:
    """2023 kaynağında bazı il adları dipnot yıldızı taşıyor (örn.
    'ADIYAMAN*' — Ocak 2023, muhtemelen 2023 depremiyle ilgili bir EPDK
    notu) ve bazıları eski yazımda inceltme işareti (^) kullanıyor (örn.
    'HAKKÂRİ' — Ağustos 2023, standart yazım 'HAKKARİ'). worker/parser.py'nin
    normalize_label()'ı ikisini de STRIPLEMİYOR/DÖNÜŞTÜRMÜYOR (Excel'de hiç
    görülmedi) — worker/parser.py DEĞİŞTİRİLMEDİ (mimari karar), yalnız
    burada, bu tarife özel temizlik."""
    return il_adi_ham.rstrip("* ").strip().translate(_SIRKUMFLEKS_DUZELT)


def _ay_yil_dogrula(
    baslik: str, beklenen_ay_adi: str, beklenen_yil: int, etiket: str
) -> None:
    """T11-karşılığı başlığından ("... {Ay} {Yıl} Döneminde ...") ay/yıl'ı
    çıkarır, MANIFEST_2023'teki beklenenle karşılaştırır. Uyuşmazlıkta
    ValueError — dosya→ay eşlemesi YANLIŞSA yanlış tarih_id'ye veri
    yazmak yerine işlemi DURDURUR."""
    m = re.search(r"(\w+)\s+(20\d\d)\s+Döneminde", baslik)
    if not m:
        raise ValueError(f"{etiket}: başlıktan ay/yıl çıkarılamadı: {baslik!r}")
    bulunan_ay, bulunan_yil = m.group(1), int(m.group(2))
    if bulunan_ay != beklenen_ay_adi or bulunan_yil != beklenen_yil:
        raise ValueError(
            f"{etiket}: MANIFEST_2023 uyuşmazlığı! beklenen={beklenen_ay_adi} "
            f"{beklenen_yil}, dosyanın kendi başlığı={bulunan_ay} {bulunan_yil} "
            f"(başlık: {baslik!r})"
        )


def t11_oku(tbl, tarih_id: int) -> pd.DataFrame:
    """T11-karşılığı: wide format, satır0=['İller', grup1..grupN, 'Genel
    Toplam','Pay']. Karar 2: Sanayi HARİÇ (baglanti/P0-2 kaynakta yok)."""
    baslik_satir = [c.text.strip() for c in tbl.rows[0].cells]
    grup_kolonlari: list[tuple[int, str]] = []
    for idx, hucre in enumerate(baslik_satir):
        if idx == 0:
            continue
        grup = grup_esle_zorunlu(hucre)
        if grup is None or grup == "Sanayi":
            continue
        grup_kolonlari.append((idx, grup))
    if not grup_kolonlari:
        raise ValueError(f"T11: hiç grup kolonu bulunamadı, başlık={baslik_satir}")

    satirlar = []
    for row in tbl.rows[1:]:
        hucreler = [c.text.strip() for c in row.cells]
        il_adi_ham = _il_adi_temizle(hucreler[0])
        if not il_adi_ham or il_adi_ham.upper() in ("GENEL TOPLAM", "TOPLAM"):
            continue
        il_kodu = il_kodu_bul(il_adi_ham)
        if il_kodu is None:
            raise ValueError(f"T11: il_kodu bulunamadı: {il_adi_ham!r}")
        for kolon_idx, grup in grup_kolonlari:
            satirlar.append(
                {
                    "il_kodu": il_kodu,
                    "tarih_id": tarih_id,
                    "grup": grup,
                    "baglanti": "dagitim",  # Karar 2: Sanayi hariç herkes 'dagitim'
                    "tuketim_mwh": parse_sayi(hucreler[kolon_idx]),
                }
            )
    df = pd.DataFrame(
        satirlar, columns=["il_kodu", "tarih_id", "grup", "baglanti", "tuketim_mwh"]
    )
    beklenen = 81 * len(grup_kolonlari)
    if len(df) != beklenen:
        raise ValueError(
            f"T11: beklenen satır {beklenen} (81 il × {len(grup_kolonlari)} grup), "
            f"gerçek {len(df)} — il sayısı 81 değil mi kontrol et"
        )
    return df


def t10_oku(tbl, tarih_id: int, hedef_ay_yil: str) -> pd.DataFrame:
    """T10-karşılığı: uzun format, dönemler-arası-karşılaştırma. Sanayi
    DAHİL (fact_abone'de baglanti yok)."""
    donem_satiri = [c.text.strip() for c in tbl.rows[0].cells]
    baslik_satiri = [c.text.strip() for c in tbl.rows[1].cells]
    hedef_kolon = hedef_donem_kolonu_bul(
        donem_satiri, baslik_satiri, hedef_ay_yil, "Sayı"
    )

    satirlar = []
    for row in tbl.rows[2:]:
        hucreler = [c.text.strip() for c in row.cells]
        il_adi_ham, tur_ham = _il_adi_temizle(hucreler[0]), hucreler[1]
        if not il_adi_ham or not tur_ham:
            continue
        grup = grup_esle_zorunlu(tur_ham)
        if grup is None:
            continue
        if il_adi_ham.upper() in ("TÜRKİYE",):
            continue
        il_kodu = il_kodu_bul(il_adi_ham)
        if il_kodu is None:
            raise ValueError(f"T10: il_kodu bulunamadı: {il_adi_ham!r}")
        satirlar.append(
            {
                "il_kodu": il_kodu,
                "tarih_id": tarih_id,
                "grup": grup,
                "abone_sayisi": parse_sayi(hucreler[hedef_kolon]),
            }
        )
    df = pd.DataFrame(satirlar, columns=["il_kodu", "tarih_id", "grup", "abone_sayisi"])
    beklenen = 81 * 5  # Aydınlatma, Kamu ve Özel Hizmetler, Mesken, Sanayi, Tarımsal
    if len(df) != beklenen:
        raise ValueError(f"T10: beklenen satır {beklenen}, gerçek {len(df)}")
    return df


def isle_ay(
    conn,
    *,
    klasor: Path,
    ay: int,
    actor_name: str,
    dry_run: bool = False,
) -> pipeline.IslemSonucu | None:
    """Bir ayı uçtan uca işler — worker/scripts/word_2024.py:isle_ay() ile
    BİREBİR AYNI akış (kaynak_asset_olustur → batch_olustur → batch_sahiplen
    → parse+doğrula → fact_tuketim_yukle/fact_abone_yukle →
    batch_durumu_guncelle + audit_log_yaz). Adım 5 (aktivasyon) BURADA
    YAPILMAZ — pipeline.batch_onayla() ayrı çağrılır.

    dry_run=True: hiçbir DB yazımı yapmaz (kaynak_asset/batch dahil), yalnız
    parse edip sonuçları terminale basar."""
    dosya_adi = MANIFEST_2023[ay]
    yol = klasor / dosya_adi
    yil = 2023
    tarih_id = yil * 100 + ay
    ay_adi = ingest.AY_ADLARI[ay]
    ay_yil = f"{ay_adi} {yil}"
    source_period = f"{yil}-{ay:02d}"

    print(f"\n=== {ay_yil} — {dosya_adi} ===")

    if not dry_run:
        # İDEMPOTENCY: bkz. word_2024.py:isle_ay() aynı bölüm — 2024'te
        # Mart'ın iki kez işlenmesinden çıkan derse dayanan kalıcı koruma.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ib.batch_id, ib.status FROM ingestion_batch ib
                JOIN source_asset sa ON sa.source_asset_id = ib.source_asset_id
                WHERE sa.source_type = 'epdk_aylik_word' AND sa.source_period = %s
                  AND ib.status != 'failed'
                ORDER BY ib.batch_id
                """,
                (source_period,),
            )
            mevcut = cur.fetchall()
        if mevcut:
            print(
                f"  [ATLA] {source_period} zaten işlenmiş: {mevcut} (yeniden işlemek için önce eski batch'i temizleyin)"
            )
            return None

    icerik = yol.read_bytes()
    doc = Document(BytesIO(icerik))
    basliklar = basliklari_topla(doc)

    t11_tbl, t11_baslik = tek_aday_bul(
        basliklar,
        icerir=[
            "Faturalanan Elektrik Tüketiminin İl ve Tüketici Türü Bazında Dağılımı"
        ],
        icermez=["Karşılaştırılması", "Karşılaştırılmasının"],
        regex_disla=r"\b\w+-\w+\s+20\d\d\b",
        etiket="T11",
    )
    _ay_yil_dogrula(t11_baslik, ay_adi, yil, "T11")
    print(f"  T11 başlık: {t11_baslik!r} (ay/yıl doğrulandı)")

    t10_tbl, t10_baslik = tek_aday_bul(
        basliklar,
        icerir=[
            "Tüketici Sayısının İl ve Tüketici Türü Bazında Dağılımının",
            "Karşılaştırılması",
        ],
        etiket="T10",
    )
    print(f"  T10 başlık: {t10_baslik!r}")

    tuketim_ham = t11_oku(t11_tbl, tarih_id)
    abone_ham = t10_oku(t10_tbl, tarih_id, ay_yil)
    print(
        f"  T11: {len(tuketim_ham)} satır, grup={sorted(tuketim_ham['grup'].unique())}, "
        f"toplam={tuketim_ham['tuketim_mwh'].sum():,.2f} MWh"
    )
    print(
        f"  T10: {len(abone_ham)} satır, grup={sorted(abone_ham['grup'].unique())}, "
        f"toplam={abone_ham['abone_sayisi'].sum():,.0f} abone"
    )

    if dry_run:
        print("  [DRY-RUN] DB'ye yazılmadı.")
        return None

    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik_word",
        dosya_adi=dosya_adi,
        icerik=icerik,
        donem_tipi="aylik",
        source_period=source_period,
        uploaded_by=None,  # bkz. word_2024.py:isle_ay() aynı yorum — UUID FK
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, "word-2023-v1", "1")
    if not ingest.batch_sahiplen(conn, batch_id):
        print(f"  [ATLA] batch_id={batch_id} zaten sahiplenilmiş/işlenmiş.")
        return None

    ingest.dim_tarih_getir_veya_olustur(conn, tarih_id)

    sonuc = pipeline.IslemSonucu(batch_id=batch_id)
    audit_tablolar: dict[str, dict[str, object]] = {}

    dogrulanan_t = kpi.dogrula_tuketim(tuketim_ham)
    yuklenen_t, atlanan_t = ingest.fact_tuketim_yukle(
        conn, dogrulanan_t.kabul, batch_id
    )
    sonuc.tablolar["fact_tuketim"] = pipeline.TabloSonucu(
        toplam=len(tuketim_ham),
        red=len(dogrulanan_t.red),
        karantina=len(dogrulanan_t.karantina),
        yuklenen=yuklenen_t,
        atlanan=atlanan_t,
    )
    audit_tablolar["fact_tuketim"] = {
        "toplam": len(tuketim_ham),
        "red": len(dogrulanan_t.red),
        "karantina": len(dogrulanan_t.karantina),
        "yuklenen": yuklenen_t,
        "atlanan": atlanan_t,
        "red_satirlari": dogrulanan_t.red.to_dict("records"),
    }

    dogrulanan_a = kpi.dogrula_abone(abone_ham)
    yuklenen_a, atlanan_a = ingest.fact_abone_yukle(conn, dogrulanan_a.kabul, batch_id)
    sonuc.tablolar["fact_abone"] = pipeline.TabloSonucu(
        toplam=len(abone_ham),
        red=len(dogrulanan_a.red),
        karantina=len(dogrulanan_a.karantina),
        yuklenen=yuklenen_a,
        atlanan=atlanan_a,
    )
    audit_tablolar["fact_abone"] = {
        "toplam": len(abone_ham),
        "red": len(dogrulanan_a.red),
        "karantina": len(dogrulanan_a.karantina),
        "yuklenen": yuklenen_a,
        "atlanan": atlanan_a,
        "red_satirlari": dogrulanan_a.red.to_dict("records"),
    }

    if dogrulanan_t.red.shape[0] or dogrulanan_t.karantina.shape[0]:
        print(
            f"  [DİKKAT] fact_tuketim: red={len(dogrulanan_t.red)} karantina={len(dogrulanan_t.karantina)}"
        )
    if dogrulanan_a.red.shape[0] or dogrulanan_a.karantina.shape[0]:
        print(
            f"  [DİKKAT] fact_abone: red={len(dogrulanan_a.red)} karantina={len(dogrulanan_a.karantina)}"
        )

    toplam_satir = len(tuketim_ham) + len(abone_ham)
    toplam_yuklenen = yuklenen_t + yuklenen_a
    toplam_atlanan = toplam_satir - toplam_yuklenen

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
            "kaynak": "word_2023",
            "tablolar": audit_tablolar,
            "not": "T13/T1/T4-karşılığı bu turda YOK (Karar 1, dokumanlar/07_word_parser_kapsam.md)",
        },
    )

    uygun, sebep = pipeline.otomatik_onaya_uygun(sonuc)
    print(f"  otomatik_onaya_uygun() = {uygun}" + (f" ({sebep})" if sebep else ""))
    return sonuc


def main() -> int:
    ap = argparse.ArgumentParser(
        description="EPP: 2023 Word raporlarını yükle (tek seferlik)"
    )
    ap.add_argument(
        "--ay",
        type=int,
        choices=range(1, 13),
        help="Yalnız bu ayı işle (verilmezse 2023'ün tümü)",
    )
    ap.add_argument("--klasor", type=Path, default=KLASOR_VARSAYILAN)
    ap.add_argument("--actor", default="manual-cli:word-2023")
    ap.add_argument(
        "--onayla",
        action="store_true",
        help="otomatik_onaya_uygun() ise batch_onayla() de çağır",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="Yalnız parse et, DB'ye YAZMA"
    )
    args = ap.parse_args()

    aylar = [args.ay] if args.ay else sorted(MANIFEST_2023)

    if args.dry_run:
        for ay in aylar:
            isle_ay(
                None, klasor=args.klasor, ay=ay, actor_name=args.actor, dry_run=True
            )
        return 0

    import psycopg

    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    # prepare_threshold=None: bkz. worker/db.py:get_db_connection().
    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        for ay in aylar:
            try:
                sonuc = isle_ay(conn, klasor=args.klasor, ay=ay, actor_name=args.actor)
            except Exception:
                conn.rollback()
                print(
                    f"  [HATA] {ingest.AY_ADLARI[ay]} 2023 işlenirken istisna oluştu, bu ay atlandı, ROLLBACK yapıldı:"
                )
                raise
            conn.commit()
            if sonuc is None:
                continue
            if args.onayla:
                uygun, _ = pipeline.otomatik_onaya_uygun(sonuc)
                if uygun:
                    aktive = pipeline.batch_onayla(
                        conn, sonuc.batch_id, actor_name=args.actor
                    )
                    conn.commit()
                    print(f"  [AKTİVE EDİLDİ] {aktive}")
                else:
                    print(
                        f"  [BEKLEMEDE] otomatik onay eşiğini geçmedi, elle onay gerekir (worker/scripts/onayla.py --batch-id {sonuc.batch_id})"
                    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
