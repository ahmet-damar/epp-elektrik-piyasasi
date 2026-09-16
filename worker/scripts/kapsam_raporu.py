"""EPP — canlı veritabanındaki GERÇEK veri kapsamını tek bir otoriter
rapora döken KALICI script (2026-09-17, kullanıcı talebi: "dashboard'a
eklenecek 'Veri Kalitesi ve Kapsam' sayfasının da veri kaynağı olacak").

**MUTLAK KISIT — SALT OKUMA:** bu modül hiçbir INSERT/UPDATE/DELETE/DDL
içermez, yalnız SELECT çalıştırır. `main()` bağlantıyı `read_only=True`
ile açar (psycopg3, sunucu tarafında `SET TRANSACTION READ ONLY` — bir
yazma denemesi KOD HATASI olsa bile veritabanı seviyesinde reddedilir,
yalnız disiplin/konvansiyona güvenilmez). Script çalıştıktan sonra
veritabanında TEK SATIR değişmez.

**Sahte değer üretilmez:** bir şey ölçülemiyorsa (örn. bir tabloda hiç
aktif satır yoksa) ilgili alan `None` kalır, rapor "hesaplanamaz" yazar —
asla `0` ile karıştırılmaz.

**Yorum yok, yalnız ölçüm:** "neden eksik" yorumu bu script'ten ÇIKMAZ —
yalnız `veri_kapsam_disi`'nde KAYITLI gerekçe (sebep/karar_referansi)
olduğu gibi raporlanır. Bunun dışındaki eksiklikler yalnız "eksik" olarak
işaretlenir, nedeni tahmin edilmez.

Kapsanan 8 fact tablosu (`TABLOLAR`): `fact_tuketim`, `fact_uretim`,
`fact_abone`, `fact_serbest_tuketici`, `fact_tuketim_ulke_geneli`,
`fact_uretim_kaynak_geneli`, `fact_uretim_il_geneli`, `fact_hava_aylik`
(bu SONUNCUSU `is_active` kolonu OLMAYAN TEK tablo — UPSERT + log modeli,
bkz. `db/schema.sql` notu — "aktif" burada "satır var" anlamına gelir)."""

from __future__ import annotations

import csv
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg
from psycopg import Connection

from worker.db import get_database_url

PROJE_KOKU = Path(__file__).resolve().parents[2]
RAPOR_DIZINI = PROJE_KOKU / "dokumanlar"
CSV_DIZINI = PROJE_KOKU / "worker" / "out"


# ---------------------------------------------------------------------------
# Tablo tanımları — TEK whitelist, f-string SQL'lerin TEK kaynağı (SQL
# enjeksiyonuna kapalı, worker/scripts/mutabakat_uretim.py ile AYNI desen).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TabloTanimi:
    ad: str
    kirilim_kolonlari: tuple[str, ...]
    is_active_var_mi: bool = True


TABLOLAR: tuple[TabloTanimi, ...] = (
    TabloTanimi("fact_tuketim", ("il_kodu", "grup_id")),
    TabloTanimi("fact_uretim", ("il_kodu", "kaynak_id", "lisans_id")),
    TabloTanimi("fact_abone", ("il_kodu", "grup_id")),
    TabloTanimi("fact_serbest_tuketici", ("il_kodu", "grup_id")),
    TabloTanimi("fact_tuketim_ulke_geneli", ("grup_id",)),
    TabloTanimi("fact_uretim_kaynak_geneli", ("kaynak_id", "lisans_id")),
    TabloTanimi("fact_uretim_il_geneli", ("il_kodu", "lisans_id")),
    TabloTanimi("fact_hava_aylik", ("il_kodu",), is_active_var_mi=False),
)

_TABLO_ADLARI = {t.ad for t in TABLOLAR}

# Bulgu J (dokumanlar/12_word_uretim_envanteri.md) — 202402'nin T2'si
# (kaynak bazında, fact_uretim_kaynak_geneli) "sağlam" ölçülüp YÜKLENDİ
# ama PASİF (aktive edilmemiş) bırakıldı — bu ilk çalıştırmada (2026-09-17)
# BULUNDU (batch_id=732, 11 satır, durum='running'). T3'ü (il bazında,
# fact_uretim_il_geneli) İSE EPDK kaynak belge hatası yüzünden HİÇ
# YÜKLENMEDİ — o tarafta bir "kapsam dışı" kaydı var (`veri_kapsam_disi`,
# bkz. §1), pasif bir fact satırı YOK. Yalnız bir kontrol sabiti; script
# bunun DIŞINDA hiçbir "neden" yorumu üretmez.
_BULGU_J_TARIH_ID = 202402
_BULGU_J_TABLO = "fact_uretim_kaynak_geneli"


def _tablo_adini_dogrula(tablo_adi: str) -> None:
    if tablo_adi not in _TABLO_ADLARI:
        raise ValueError(f"Beklenmeyen tablo adı: {tablo_adi!r}")


# ---------------------------------------------------------------------------
# SAF (DB gerektirmeyen) takvim/kardinalite fonksiyonları — testlerin çoğu
# bunlara karşı yazılır.
# ---------------------------------------------------------------------------


def ay_ekle(tarih_id: int, delta: int) -> int:
    """`tarih_id` (YYYYMM) üzerinde `delta` ay ileri/geri kaydırır — yıl
    devrini doğru işler (örn. 202412 + 1 -> 202501). Yalnız AYLIK
    (ay 1-12) tarih_id'ler için tanımlıdır."""
    yil, ay = divmod(tarih_id, 100)
    toplam_ay_indeksi = yil * 12 + (ay - 1) + delta
    yeni_yil, yeni_ay_indeksi = divmod(toplam_ay_indeksi, 12)
    return yeni_yil * 100 + (yeni_ay_indeksi + 1)


def beklenen_aylik_takvim(min_tarih_id: int, max_tarih_id: int) -> list[int]:
    """`min_tarih_id`..`max_tarih_id` (DAHİL) arasındaki HER ayın
    tarih_id'sini üretir. `min_tarih_id > max_tarih_id` ise boş liste
    (tablo hiç veri içermiyor demektir, çağıran bunu ayrıca ele alır)."""
    if min_tarih_id > max_tarih_id:
        return []
    takvim = [min_tarih_id]
    while takvim[-1] < max_tarih_id:
        takvim.append(ay_ekle(takvim[-1], 1))
    return takvim


def eksik_aylari_bul(
    mevcut_tarih_idler: Iterable[int], min_tarih_id: int, max_tarih_id: int
) -> list[int]:
    """Beklenen takvimde olup `mevcut_tarih_idler`'de OLMAYAN ayları
    döner — sıralı, tekrarsız."""
    mevcut_kume = set(mevcut_tarih_idler)
    return [
        t
        for t in beklenen_aylik_takvim(min_tarih_id, max_tarih_id)
        if t not in mevcut_kume
    ]


def modal_kardinalite_bul(
    ay_kardinalite: dict[int, dict[str, int]], kolonlar: Sequence[str]
) -> dict[str, int | None]:
    """Her kırılım kolonu için AYLAR ÜZERİNDE en sık görülen (modal)
    kardinalite değerini döner. Hiç gözlem yoksa `None` (hesaplanamaz —
    sahte bir sayı ÜRETİLMEZ)."""
    modal: dict[str, int | None] = {}
    for kolon in kolonlar:
        degerler = [
            ay_verisi[kolon]
            for ay_verisi in ay_kardinalite.values()
            if kolon in ay_verisi
        ]
        if not degerler:
            modal[kolon] = None
            continue
        sayac = Counter(degerler)
        modal[kolon] = sayac.most_common(1)[0][0]
    return modal


def kismi_aylari_bul(
    ay_kardinalite: dict[int, dict[str, int]], modal: Mapping[str, int | None]
) -> dict[int, dict[str, tuple[int, int]]]:
    """Modal kardinaliteden SAPAN ayları döner:
    `{tarih_id: {kolon: (mevcut_deger, modal_deger)}}`. Tam eksik AYLAR
    (hiç satırı olmayan) burada YOK — bkz. `eksik_aylari_bul()`; bu yalnız
    "var ama içi delik" ayları yakalar."""
    kismi: dict[int, dict[str, tuple[int, int]]] = {}
    for tarih_id, kolonlar in sorted(ay_kardinalite.items()):
        sapmalar: dict[str, tuple[int, int]] = {}
        for kolon, deger in kolonlar.items():
            beklenen = modal.get(kolon)
            if beklenen is not None and deger != beklenen:
                sapmalar[kolon] = (deger, beklenen)
        if sapmalar:
            kismi[tarih_id] = sapmalar
    return kismi


def yil_basina_beklenen_ay(yil: int, bugun: date) -> int:
    """Geçmiş bir yıl için 12, gelecek bir yıl için 0, İÇİNDE
    BULUNULAN yıl için `bugun`e kadar geçen ay sayısı (kullanıcı talimatı:
    "2026 için bugüne kadar")."""
    if yil < bugun.year:
        return 12
    if yil > bugun.year:
        return 0
    return bugun.month


def yillik_tamlik_hesapla(
    tablo_adi: str, aktif_tarih_idler: Iterable[int], bugun: date
) -> list[dict[str, Any]]:
    """Her yıl için `{tablo, yil, beklenen_ay, mevcut_aktif_ay, tam_mi}`
    satırı üretir — `aktif_tarih_idler`'in kapsadığı EN KÜÇÜK ve EN BÜYÜK
    yıl arasındaki HER yıl için (aradaki bir yıl hiç veri içermese bile
    `mevcut_aktif_ay=0` ile satırı üretilir — sessizce atlanmaz). Yıllık
    (ay=0) kayıtlar bu aylık-tamlık hesabının DIŞINDA tutulur."""
    yillar_aylar: dict[int, set[int]] = {}
    for tarih_id in aktif_tarih_idler:
        yil, ay = divmod(tarih_id, 100)
        if ay == 0:
            continue
        yillar_aylar.setdefault(yil, set()).add(ay)

    if not yillar_aylar:
        return []

    sonuc: list[dict[str, Any]] = []
    for yil in range(min(yillar_aylar), max(yillar_aylar) + 1):
        mevcut_ay = len(yillar_aylar.get(yil, set()))
        beklenen = yil_basina_beklenen_ay(yil, bugun)
        sonuc.append(
            {
                "tablo": tablo_adi,
                "yil": yil,
                "beklenen_ay": beklenen,
                "mevcut_aktif_ay": mevcut_ay,
                "tam_mi": mevcut_ay == beklenen,
            }
        )
    return sonuc


def tarih_id_okunabilir(tarih_id: int) -> str:
    yil, ay = divmod(tarih_id, 100)
    return f"{yil} (yıllık)" if ay == 0 else f"{yil}-{ay:02d}"


# ---------------------------------------------------------------------------
# DB sorgu katmanı — YALNIZ SELECT.
# ---------------------------------------------------------------------------


def veri_kapsam_disi_getir(conn: Connection) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tarih_id, fact_tablosu, nitelik, sebep, karar_referansi, created_at
            FROM veri_kapsam_disi
            ORDER BY fact_tablosu, tarih_id, nitelik
            """
        )
        rows = cur.fetchall()
    return [
        {
            "tarih_id": r[0],
            "fact_tablosu": r[1],
            "nitelik": r[2],
            "sebep": r[3],
            "karar_referansi": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]


def tablo_min_max_aktif_getir(
    conn: Connection, tanim: TabloTanimi
) -> tuple[int, int] | None:
    """`is_active`'i olan tablolarda yalnız aktif satırların, olmayanlarda
    (fact_hava_aylik) TÜM satırların min/max `tarih_id`'sini döner. Tablo
    hiç satır içermiyorsa `None` ("hesaplanamaz")."""
    _tablo_adini_dogrula(tanim.ad)
    kosul = "WHERE is_active" if tanim.is_active_var_mi else ""
    sorgu = f"SELECT min(tarih_id), max(tarih_id) FROM {tanim.ad} {kosul}"  # nosec B608 — tanim.ad TABLOLAR sabitinden, _tablo_adini_dogrula() ile teyit edildi
    with conn.cursor() as cur:
        cur.execute(sorgu)
        row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    return int(row[0]), int(row[1])


def tablo_ay_kardinalite_getir(
    conn: Connection, tanim: TabloTanimi, min_tarih_id: int, max_tarih_id: int
) -> dict[int, dict[str, int]]:
    """[min_tarih_id, max_tarih_id] aralığındaki (dahil) her `tarih_id`
    için, tanımın kırılım kolonlarının HER BİRİNİN distinct sayımını
    döner. Yalnız EN AZ bir aktif satırı olan aylar anahtardır — eksik
    aylar burada hiç GÖRÜNMEZ (bkz. `eksik_aylari_bul()`)."""
    _tablo_adini_dogrula(tanim.ad)
    kosul = "is_active AND " if tanim.is_active_var_mi else ""
    kolon_secimleri = ", ".join(
        f"count(DISTINCT {kolon}) AS {kolon}" for kolon in tanim.kirilim_kolonlari
    )
    sorgu = f"""
        SELECT tarih_id, {kolon_secimleri}
        FROM {tanim.ad}
        WHERE {kosul}tarih_id BETWEEN %s AND %s
        GROUP BY tarih_id
        ORDER BY tarih_id
    """  # nosec B608 — tanim.ad/kirilim_kolonlari TABLOLAR sabitinden, kullanıcı girdisi değil
    with conn.cursor() as cur:
        cur.execute(sorgu, (min_tarih_id, max_tarih_id))
        rows = cur.fetchall()
    sonuc: dict[int, dict[str, int]] = {}
    for row in rows:
        tarih_id = int(row[0])
        sonuc[tarih_id] = dict(
            zip(tanim.kirilim_kolonlari, (int(v) for v in row[1:]), strict=True)
        )
    return sonuc


def tablo_pasif_kayitlari_getir(
    conn: Connection, tanim: TabloTanimi
) -> list[dict[str, Any]]:
    """`is_active=false` olan (tarih_id, ingestion_batch_id) çiftlerini,
    ait oldukları batch'in durumu/oluşturulma tarihiyle birlikte döner.
    `is_active` kolonu olmayan tablolarda (fact_hava_aylik) boş liste —
    bu tablonun sürümleme modelinde "pasif" kavramı yok."""
    if not tanim.is_active_var_mi:
        return []
    _tablo_adini_dogrula(tanim.ad)
    sorgu = f"""
        SELECT f.tarih_id, f.ingestion_batch_id, count(*) AS satir_sayisi,
               b.status, b.created_at
        FROM {tanim.ad} f
        JOIN ingestion_batch b ON b.batch_id = f.ingestion_batch_id
        WHERE f.is_active = false
        GROUP BY f.tarih_id, f.ingestion_batch_id, b.status, b.created_at
        ORDER BY f.tarih_id, f.ingestion_batch_id
    """  # nosec B608 — tanim.ad TABLOLAR sabitinden, _tablo_adini_dogrula() ile teyit edildi
    with conn.cursor() as cur:
        cur.execute(sorgu)
        rows = cur.fetchall()
    return [
        {
            "tablo": tanim.ad,
            "tarih_id": int(r[0]),
            "ingestion_batch_id": int(r[1]),
            "satir_sayisi": int(r[2]),
            "batch_status": r[3],
            "batch_created_at": r[4],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Orkestrasyon
# ---------------------------------------------------------------------------


@dataclass
class TabloRaporu:
    tanim: TabloTanimi
    min_tarih_id: int | None
    max_tarih_id: int | None
    ay_kardinalite: dict[int, dict[str, int]] = field(default_factory=dict)
    eksik_aylar: list[int] = field(default_factory=list)
    modal_kardinalite: dict[str, int | None] = field(default_factory=dict)
    kismi_aylar: dict[int, dict[str, tuple[int, int]]] = field(default_factory=dict)
    pasif_kayitlar: list[dict[str, Any]] = field(default_factory=list)
    yillik_tamlik: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class KapsamRaporu:
    olusturulma_zamani_iso: str
    veri_kapsam_disi: list[dict[str, Any]]
    tablolar: list[TabloRaporu]
    bulgu_j_kontrolu: dict[str, Any]


def _bulgu_j_kontrol_et(tablo_raporlari: list[TabloRaporu]) -> dict[str, Any]:
    for tr in tablo_raporlari:
        if tr.tanim.ad != _BULGU_J_TABLO:
            continue
        bulundu = any(p["tarih_id"] == _BULGU_J_TARIH_ID for p in tr.pasif_kayitlar)
        return {
            "tablo": _BULGU_J_TABLO,
            "tarih_id": _BULGU_J_TARIH_ID,
            "bulundu": bulundu,
        }
    return {"tablo": _BULGU_J_TABLO, "tarih_id": _BULGU_J_TARIH_ID, "bulundu": False}


def rapor_olustur(conn: Connection, *, bugun: date | None = None) -> KapsamRaporu:
    """Rapor'un TEK giriş noktası — yalnız SELECT çalıştırır. `bugun`
    testlerde sabitlenebilir (varsayılan `date.today()`)."""
    if bugun is None:
        bugun = datetime.now(tz=UTC).date()

    kapsam_disi = veri_kapsam_disi_getir(conn)

    tablo_raporlari: list[TabloRaporu] = []
    for tanim in TABLOLAR:
        min_max = tablo_min_max_aktif_getir(conn, tanim)
        pasif = tablo_pasif_kayitlari_getir(conn, tanim)
        if min_max is None:
            tablo_raporlari.append(TabloRaporu(tanim, None, None, pasif_kayitlar=pasif))
            continue
        min_t, max_t = min_max
        ay_kardinalite = tablo_ay_kardinalite_getir(conn, tanim, min_t, max_t)
        eksik = eksik_aylari_bul(ay_kardinalite.keys(), min_t, max_t)
        modal = modal_kardinalite_bul(ay_kardinalite, tanim.kirilim_kolonlari)
        kismi = kismi_aylari_bul(ay_kardinalite, modal)
        yillik = yillik_tamlik_hesapla(tanim.ad, ay_kardinalite.keys(), bugun)
        tablo_raporlari.append(
            TabloRaporu(
                tanim,
                min_t,
                max_t,
                ay_kardinalite=ay_kardinalite,
                eksik_aylar=eksik,
                modal_kardinalite=modal,
                kismi_aylar=kismi,
                pasif_kayitlar=pasif,
                yillik_tamlik=yillik,
            )
        )

    return KapsamRaporu(
        olusturulma_zamani_iso=datetime.now(tz=UTC).isoformat(timespec="seconds"),
        veri_kapsam_disi=kapsam_disi,
        tablolar=tablo_raporlari,
        bulgu_j_kontrolu=_bulgu_j_kontrol_et(tablo_raporlari),
    )


# ---------------------------------------------------------------------------
# Render — Markdown (insan okuması) + CSV (makine okuması). SAF fonksiyonlar
# (yalnız `KapsamRaporu`'nu okur, DB'ye dokunmaz).
# ---------------------------------------------------------------------------


def csv_satirlari_olustur(rapor: KapsamRaporu) -> list[dict[str, Any]]:
    satirlar: list[dict[str, Any]] = []
    for tr in rapor.tablolar:
        satirlar.extend(tr.yillik_tamlik)
    return satirlar


def csv_yaz(satirlar: list[dict[str, Any]], dosya_yolu: Path) -> None:
    dosya_yolu.parent.mkdir(parents=True, exist_ok=True)
    alan_adlari = ["tablo", "yil", "beklenen_ay", "mevcut_aktif_ay", "tam_mi"]
    with dosya_yolu.open("w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=alan_adlari)
        yazici.writeheader()
        for satir in satirlar:
            yazici.writerow(satir)


def _md_kapsam_disi_bolumu(rapor: KapsamRaporu) -> list[str]:
    satirlar = [
        "## 1) `veri_kapsam_disi` — tamamı",
        "",
        (
            f"Toplam {len(rapor.veri_kapsam_disi)} kayıt "
            f"({rapor.olusturulma_zamani_iso} itibarıyla, canlı veritabanından)."
        ),
        "",
    ]
    if not rapor.veri_kapsam_disi:
        satirlar.append("(hiç kayıt yok)")
        satirlar.append("")
        return satirlar

    satirlar += [
        "| tarih_id | dönem | fact_tablosu | nitelik | sebep | karar_referansi | created_at |",
        "|---|---|---|---|---|---|---|",
    ]
    for k in rapor.veri_kapsam_disi:
        satirlar.append(
            f"| {k['tarih_id']} | {tarih_id_okunabilir(k['tarih_id'])} "
            f"| {k['fact_tablosu']} | {k['nitelik']} | {k['sebep']} "
            f"| {k['karar_referansi']} | {k['created_at']} |"
        )
    satirlar.append("")

    satirlar.append("**Okunabilir özet (tablo/yıl aralığı/satır sayısı):**")
    satirlar.append("")
    ozet: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for k in rapor.veri_kapsam_disi:
        anahtar = (k["fact_tablosu"], k["nitelik"])
        ozet.setdefault(anahtar, []).append(k)
    for (tablo, nitelik), kayitlar in sorted(ozet.items()):
        donemler = sorted(k["tarih_id"] for k in kayitlar)
        satirlar.append(
            f"- `{tablo}` / `{nitelik}`: {len(kayitlar)} kayıt, "
            f"{tarih_id_okunabilir(donemler[0])} .. {tarih_id_okunabilir(donemler[-1])} "
            f"— gerekçe: {kayitlar[0]['sebep']} ({kayitlar[0]['karar_referansi']})"
        )
    satirlar.append("")
    return satirlar


def _md_tablo_bolumu(tr: TabloRaporu) -> list[str]:
    ad = tr.tanim.ad
    satirlar = [f"### `{ad}`", ""]
    if tr.min_tarih_id is None:
        satirlar.append("Hiç aktif satır bulunamadı — **hesaplanamaz**.")
        satirlar.append("")
        return satirlar
    # min/max_tarih_id her zaman BİRLİKTE set edilir (bkz. rapor_olustur) —
    # min None değilse max de değildir.
    assert tr.max_tarih_id is not None

    satirlar.append(
        f"Aralık: **{tarih_id_okunabilir(tr.min_tarih_id)} .. "
        f"{tarih_id_okunabilir(tr.max_tarih_id)}** "
        f"(tarih_id {tr.min_tarih_id}..{tr.max_tarih_id})."
    )
    satirlar.append("")

    satirlar.append(f"**Eksik ay sayısı: {len(tr.eksik_aylar)}**")
    if tr.eksik_aylar:
        satirlar.append(", ".join(tarih_id_okunabilir(t) for t in tr.eksik_aylar))
    satirlar.append("")

    modal_metin = ", ".join(
        f"{kolon}={deger if deger is not None else 'hesaplanamaz'}"
        for kolon, deger in tr.modal_kardinalite.items()
    )
    satirlar.append(f"**Modal kardinalite:** {modal_metin}")
    satirlar.append("")

    satirlar.append(f"**Kısmi ay sayısı (modalden sapan): {len(tr.kismi_aylar)}**")
    if tr.kismi_aylar:
        satirlar.append("")
        satirlar.append("| dönem | sapan kolon(lar) (mevcut / modal) |")
        satirlar.append("|---|---|")
        for tarih_id, sapmalar in sorted(tr.kismi_aylar.items()):
            sapma_metni = ", ".join(
                f"{kolon}: {mevcut}/{modal}"
                for kolon, (mevcut, modal) in sapmalar.items()
            )
            satirlar.append(f"| {tarih_id_okunabilir(tarih_id)} | {sapma_metni} |")
    satirlar.append("")

    kolon_basliklari = " | ".join(tr.tanim.kirilim_kolonlari)
    satirlar.append(f"**Ay bazlı kardinalite** (dönem | {kolon_basliklari}):")
    satirlar.append("")
    satirlar.append(f"| dönem | {kolon_basliklari} |")
    satirlar.append("|" + "---|" * (len(tr.tanim.kirilim_kolonlari) + 1))
    for tarih_id in sorted(tr.ay_kardinalite):
        degerler = " | ".join(
            str(tr.ay_kardinalite[tarih_id][k]) for k in tr.tanim.kirilim_kolonlari
        )
        satirlar.append(f"| {tarih_id_okunabilir(tarih_id)} | {degerler} |")
    satirlar.append("")

    if tr.tanim.is_active_var_mi:
        satirlar.append(
            f"**Yüklü ama PASİF (is_active=false) kayıt sayısı:** {len(tr.pasif_kayitlar)}"
        )
        if tr.pasif_kayitlar:
            satirlar.append("")
            satirlar.append(
                "| dönem | ingestion_batch_id | satır sayısı | batch durumu | batch created_at |"
            )
            satirlar.append("|---|---|---|---|---|")
            for p in tr.pasif_kayitlar:
                satirlar.append(
                    f"| {tarih_id_okunabilir(p['tarih_id'])} | {p['ingestion_batch_id']} "
                    f"| {p['satir_sayisi']} | {p['batch_status']} | {p['batch_created_at']} |"
                )
    else:
        satirlar.append(
            "**Pasif kayıt kavramı yok** — bu tablo `is_active` sürümlemesi "
            "kullanmıyor (UPSERT + `fact_hava_aylik_log`, bkz. `db/schema.sql`)."
        )
    satirlar.append("")

    if tr.yillik_tamlik:
        satirlar.append("**Yıllık tamlık:**")
        satirlar.append("")
        satirlar.append("| yıl | beklenen_ay | mevcut_aktif_ay | tam_mı |")
        satirlar.append("|---|---|---|---|")
        for y in tr.yillik_tamlik:
            satirlar.append(
                f"| {y['yil']} | {y['beklenen_ay']} | {y['mevcut_aktif_ay']} "
                f"| {'✅' if y['tam_mi'] else '❌'} |"
            )
        satirlar.append("")

    return satirlar


def markdown_olustur(rapor: KapsamRaporu, tarih_str: str) -> str:
    satirlar = [
        f"# EPP — Veri Kapsamı Raporu ({tarih_str})",
        "",
        f"**Oluşturulma zamanı (UTC, tarih çapası):** {rapor.olusturulma_zamani_iso}",
        "",
        (
            "Bu rapor `worker/scripts/kapsam_raporu.py` ile YALNIZ SELECT "
            "sorgularıyla üretildi — üretim sırasında veritabanında hiçbir "
            "satır değişmedi. Bir değer ölçülemiyorsa 'hesaplanamaz' yazar, "
            "asla sahte bir sıfır ÜRETMEZ. 'Neden eksik' yorumu YALNIZ "
            "`veri_kapsam_disi`'nde KAYITLI gerekçelerden gelir — script "
            "kendi başına neden tahmini YAPMAZ."
        ),
        "",
        "---",
        "",
    ]

    satirlar += _md_kapsam_disi_bolumu(rapor)
    satirlar.append("---")
    satirlar.append("")

    satirlar.append("## 2) Fact tabloları — takvim, eksik/kısmi aylar, kardinalite")
    satirlar.append("")
    for tr in rapor.tablolar:
        satirlar += _md_tablo_bolumu(tr)
    satirlar.append("---")
    satirlar.append("")

    satirlar.append("## 3) Yüklü ama pasif kayıtlar — Bulgu J kontrolü")
    satirlar.append("")
    bj = rapor.bulgu_j_kontrolu
    if bj["bulundu"]:
        satirlar.append(
            f"✅ Beklenen kayıt bulundu: `{bj['tablo']}` / "
            f"{tarih_id_okunabilir(bj['tarih_id'])} pasif olarak mevcut (Bulgu J)."
        )
    else:
        satirlar.append(
            f"⚠️ **BEKLENEN KAYIT BULUNAMADI:** `{bj['tablo']}` / "
            f"{tarih_id_okunabilir(bj['tarih_id'])} (Bulgu J) pasif kayıtlar "
            "arasında YOK. Bu sessizce geçilmedi, açıkça işaretleniyor — "
            "beklenen durumla canlı durum arasında bir fark var, araştırılmalı."
        )
    satirlar.append("")
    satirlar.append(
        "(Tam pasif kayıt listeleri her tablonun yukarıdaki §2 alt "
        "bölümünde — bu madde yalnız Bulgu J'nin özel kontrolüdür.)"
    )
    satirlar.append("")
    satirlar.append("---")
    satirlar.append("")

    satirlar.append("## 4) Yıllık tamlık tablosu (tüm tablolar, özet)")
    satirlar.append("")
    satirlar.append(
        f"Ayrıca makine-okunur CSV: `worker/out/kapsam_yillik_tamlik_{tarih_str}.csv` "
        "— yıllık grafiklerdeki 'eksik dönem' bayrağı buradan beslenir."
    )
    satirlar.append("")
    satirlar.append("| tablo | yıl | beklenen_ay | mevcut_aktif_ay | tam_mı |")
    satirlar.append("|---|---|---|---|---|")
    for tr in rapor.tablolar:
        for y in tr.yillik_tamlik:
            satirlar.append(
                f"| {y['tablo']} | {y['yil']} | {y['beklenen_ay']} "
                f"| {y['mevcut_aktif_ay']} | {'✅' if y['tam_mi'] else '❌'} |"
            )
    satirlar.append("")

    return "\n".join(satirlar)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _konsol_ozeti_yazdir(rapor: KapsamRaporu) -> None:
    print(f"Oluşturulma zamanı (UTC): {rapor.olusturulma_zamani_iso}")
    print(f"veri_kapsam_disi: {len(rapor.veri_kapsam_disi)} kayıt")
    bj = rapor.bulgu_j_kontrolu
    print(
        f"Bulgu J kontrolü ({bj['tablo']}/{tarih_id_okunabilir(bj['tarih_id'])}): "
        + ("bulundu" if bj["bulundu"] else "BULUNAMADI — beklenen kayıt yok!")
    )
    for tr in rapor.tablolar:
        if tr.min_tarih_id is None:
            print(f"- {tr.tanim.ad}: hiç aktif satır yok (hesaplanamaz)")
            continue
        assert tr.max_tarih_id is not None
        print(
            f"- {tr.tanim.ad}: {tarih_id_okunabilir(tr.min_tarih_id)}.."
            f"{tarih_id_okunabilir(tr.max_tarih_id)}, "
            f"eksik ay={len(tr.eksik_aylar)}, kısmi ay={len(tr.kismi_aylar)}, "
            f"pasif kayıt={len(tr.pasif_kayitlar)}"
        )
        if tr.eksik_aylar:
            print(
                "    eksik: "
                + ", ".join(tarih_id_okunabilir(t) for t in tr.eksik_aylar)
            )
        if tr.kismi_aylar:
            print(
                "    kısmi: "
                + ", ".join(tarih_id_okunabilir(t) for t in sorted(tr.kismi_aylar))
            )


def main() -> int:
    database_url = get_database_url()
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    bugun = datetime.now(tz=UTC).date()
    tarih_str = bugun.isoformat()

    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        # SALT OKUMA garantisi — sunucu tarafında zorlanır (bkz. modül notu).
        conn.read_only = True
        rapor = rapor_olustur(conn, bugun=bugun)
        conn.rollback()

    md_metni = markdown_olustur(rapor, tarih_str)
    md_yolu = RAPOR_DIZINI / f"kapsam_raporu_{tarih_str}.md"
    md_yolu.write_text(md_metni, encoding="utf-8")

    csv_satirlari = csv_satirlari_olustur(rapor)
    csv_yolu = CSV_DIZINI / f"kapsam_yillik_tamlik_{tarih_str}.csv"
    csv_yaz(csv_satirlari, csv_yolu)

    print(f"Rapor yazıldı: {md_yolu}")
    print(f"CSV yazıldı: {csv_yolu}")
    print()
    _konsol_ozeti_yazdir(rapor)
    return 0


if __name__ == "__main__":
    sys.exit(main())
