"""EPP — `supabase/migrations/` dosyalarını CANLIYA uygulayan, hangisinin
uygulandığını KAYDEDEN kalıcı operatör script'i (2026-10-04,
`Claude outputs/PROMPT_MIGRATION_CANLI_2026-10-04.md`).

**Neden gerekli:** `20260920_0001_toplama_katmani_views.sql` disposable'da
doğrulanıp canlıya HİÇ UYGULANMADI — üstüne UI (dashboard Zaman Serisi)
inşa edildi, canlıda `psycopg.errors.UndefinedTable` ile patladı. Kök
sebep bundan da temel: `.github/workflows/deploy.yml`'in `migrate` job'ı
`build-push`'a `needs` ile bağlı, o da `if: false` ile KALICI OLARAK
devre dışı (web/worker Dockerfile'ları henüz yok) — yani `migrate`
HİÇBİR push'ta hiç çalışmıyor, Faz 0'dan beri TÜM migration'lar ELLE
(psql ile) uygulanıyordu, hiçbiri kayıt altına alınmadan. `schema_
migrations` tablosu (bkz. `supabase/migrations/20261004_0001_schema_
migrations.sql`) + bu script bu sınıf hatanın TEKRARINI yapısal olarak
imkânsız kılar: `--dry-run` (varsayılan) her koşuda BEKLEYEN migration'ları
açıkça listeler, sessizce atlamaz.

Kullanım:
    python -m worker.scripts.migration_uygula
        (varsayılan: --dry-run — HİÇBİR ŞEY YAZILMAZ, bekleyen dosyalar
        gerçek bir transaction içinde işlenip sonunda ROLLBACK edilir)
    python -m worker.scripts.migration_uygula --uygula
        (bekleyen dosyaları sırayla, HER BİRİ KENDİ transaction'ında
        uygular ve `schema_migrations`'a kaydeder)
    python -m worker.scripts.migration_uygula --bootstrap --dry-run
        (tablo BOŞKEN bir kez: nesne-varlık kontrolüyle hangi dosyaların
        'zaten uygulanmış' işaretleneceğini GÖSTERİR, hiçbir şey yazmaz)
    python -m worker.scripts.migration_uygula --bootstrap --uygula
        (yukarıdakini GERÇEKTEN işaretler — tablo dolu değilse reddedilir,
        bu bayrak yalnız BİR KEZ kullanılabilir)

Durma kuralları (her biri `DurdurmaHatasi` fırlatır, exit code 1):
- Yedek 24 saatten eskiyse/doğrulanamıyorsa (`--yedek-atla "<gerekçe>"`
  ile bilinçli geçilir).
- Başka bir `migration_uygula` koşusu SÜRÜYORSA (advisory lock alınamaz).
- Kayıtlı bir `dosya_hash` diskteki dosyayla UYUŞMUYORSA (uygulanmış bir
  migration sonradan düzenlenmiş demektir — sessizce geçilmez).
- `--bootstrap` tablo BOŞ değilken çağrılırsa.
- Herhangi bir migration'ın uygulanması sırasında hata oluşursa — o dosya
  VE SONRASI işlenmez (toplu uygulama YOK, sıra korunur).
- İşlem sonunda fact tablolarında (toplam/aktif/ay-bazlı), `ingestion_
  batch` durum dağılımında fark bulunursa — bir view/index migration'ı
  VERİYE dokunmamalı.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg

from worker import ingest
from worker.db import get_database_url
from worker.scripts.aylik_yukle import (
    DurdurmaHatasi,
    baglan,
    durum_fotografi,
    son_basarili_yedek_yasi,
)

_VARSAYILAN_YEDEK_MAX_YAS_SAAT = 24
_ADVISORY_LOCK_KEY = 847302001  # sabit, keyfi - epp_migration_uygula için ayrılmış

MIGRATIONS_DIZIN_VARSAYILAN = (
    Path(__file__).resolve().parents[2] / "supabase" / "migrations"
)

_RE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\"?(\w+)\"?", re.IGNORECASE
)
_RE_VIEW = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+\"?(\w+)\"?", re.IGNORECASE)
_RE_INDEX = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?\"?(\w+)\"?"
    r"\s+ON\s+\"?(\w+)\"?",
    re.IGNORECASE,
)
_RE_FUNC = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+\"?(\w+)\"?\s*\(", re.IGNORECASE
)
_RE_POLICY = re.compile(
    r"CREATE\s+POLICY\s+\"?([\w ]+?)\"?\s+ON\s+\"?(\w+)\"?", re.IGNORECASE
)
_RE_DROP_COLUMN = re.compile(
    r"ALTER\s+TABLE\s+\"?(\w+)\"?\s+DROP\s+COLUMN", re.IGNORECASE
)


def dosya_hash(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def migration_listesi(dizin: Path) -> list[Path]:
    return sorted(dizin.glob("*.sql"))


def govde_metni(sql: str) -> str:
    """Dosyanın kendi `BEGIN;`/`COMMIT;` sarmalamasını söker — transaction'ı
    HER ZAMAN script kendisi yönetir (dry-run'da rollback edilebilsin,
    `--uygula`'da her dosya kendi transaction'ında commit edilsin)."""
    govde = sql.strip()
    govde = re.sub(r"^\s*BEGIN\s*;\s*", "", govde, count=1, flags=re.IGNORECASE)
    govde = re.sub(r"\s*COMMIT\s*;\s*$", "", govde, count=1, flags=re.IGNORECASE)
    return govde.strip()


def _objeleri_cikar(sql: str) -> list[tuple[str, str, str | None]]:
    """(tür, ad, tablo_veya_None) listesi döner — `--bootstrap`'ın
    nesne-varlık kontrolü için (bkz. GÖREV 1 kapanış raporu)."""
    sonuc: list[tuple[str, str, str | None]] = []
    for m in _RE_TABLE.finditer(sql):
        sonuc.append(("table", m.group(1), None))
    for m in _RE_VIEW.finditer(sql):
        sonuc.append(("view", m.group(1), None))
    for m in _RE_INDEX.finditer(sql):
        sonuc.append(("index", m.group(1), m.group(2)))
    for m in _RE_FUNC.finditer(sql):
        sonuc.append(("function", m.group(1), None))
    for m in _RE_POLICY.finditer(sql):
        sonuc.append(("policy", m.group(1).strip(), m.group(2)))
    return sonuc


def _obje_dogrudan_var_mi(
    cur: psycopg.Cursor, tur: str, ad: str, tablo: str | None
) -> bool:
    if tur == "table":
        cur.execute(
            "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relname=%s AND c.relkind IN ('r','p')",
            (ad,),
        )
    elif tur == "view":
        cur.execute(
            "SELECT 1 FROM pg_views WHERE schemaname='public' AND viewname=%s", (ad,)
        )
    elif tur == "index":
        cur.execute(
            "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=%s",
            (ad,),
        )
    elif tur == "function":
        cur.execute(
            "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname='public' AND p.proname=%s",
            (ad,),
        )
    elif tur == "policy":
        cur.execute(
            "SELECT 1 FROM pg_policies WHERE schemaname='public' "
            "AND tablename=%s AND policyname=%s",
            (tablo, ad),
        )
    else:  # pragma: no cover - _objeleri_cikar yalnız yukarıdaki türleri üretir
        raise AssertionError(f"bilinmeyen obje türü: {tur}")
    return cur.fetchone() is not None


def _obje_sonradan_dusuruldu_mu(
    tur: str, ad: str, tablo: str | None, sonraki_metin: str
) -> bool:
    """Bir obje canlıda YOK diye bu migration'ın UYGULANMADIĞI anlamına
    gelmez — DAHA SONRAKİ bir migration onu kasıtlı olarak kaldırmış
    olabilir (örn. `20260819_0019` birçok politikayı `DROP POLICY` ile
    kaldırdı; `20260819_0009` `is_active` kolonunu düşürüp buna bağlı
    partial unique index'i KASKADLA düşürdü, bkz. kapanış raporu). İki
    genel (dosya adına özel OLMAYAN) kural: (1) aynı ad+tablo'yu açıkça
    DROP eden bir migration var mı, (2) index/constraint için, aynı
    tabloda bir `DROP COLUMN` var mı (kolonun TAM eşleşmesi aranmaz —
    index'in hangi koloma bağlı olduğunu genel biçimde çıkarmak bir SQL
    ayrıştırıcısı gerektirir; bu script'in bootstrap çıktısı ZATEN elle
    gözden geçiriliyor, bkz. GÖREV 3 adım 2)."""
    if (
        tur == "policy"
        and tablo
        and re.search(
            rf"DROP\s+POLICY\s+(?:IF\s+EXISTS\s+)?\"?{re.escape(ad)}\"?\s+ON\s+\"?{re.escape(tablo)}\"?",
            sonraki_metin,
            re.IGNORECASE,
        )
    ):
        return True
    if tur in ("table", "view", "function"):
        tur_sql = {"table": "TABLE", "view": "VIEW", "function": "FUNCTION"}[tur]
        if re.search(
            rf"DROP\s+{tur_sql}\s+(?:IF\s+EXISTS\s+)?\"?{re.escape(ad)}\"?",
            sonraki_metin,
            re.IGNORECASE,
        ):
            return True
    return bool(
        tur == "index"
        and tablo
        and any(m.group(1) == tablo for m in _RE_DROP_COLUMN.finditer(sonraki_metin))
    )


def bootstrap_adaylarini_belirle(cur: psycopg.Cursor, dizin: Path) -> list[Path]:
    """Dosyaları sırayla tarar, nesne-varlık kontrolüyle 'zaten uygulanmış'
    olanları toplar. İLK GERÇEKTEN eksik dosyada DURUR — o dosya VE
    SONRASI bootstrap'lanmaz, normal `--dry-run`/`--uygula` akışına
    bırakılır (bkz. modül notu: tek eksik varsayılmaz, hepsi taranır)."""
    dosyalar = migration_listesi(dizin)
    isaretlenecekler: list[Path] = []
    for i, yol in enumerate(dosyalar):
        sql = yol.read_text(encoding="utf-8")
        objeler = _objeleri_cikar(sql)
        sonraki_metin = "\n".join(
            d.read_text(encoding="utf-8") for d in dosyalar[i + 1 :]
        )
        eksikler = [
            (tur, ad)
            for tur, ad, tablo in objeler
            if not _obje_dogrudan_var_mi(cur, tur, ad, tablo)
            and not _obje_sonradan_dusuruldu_mu(tur, ad, tablo, sonraki_metin)
        ]
        if eksikler:
            break
        isaretlenecekler.append(yol)
    return isaretlenecekler


def _bare_tablo_olustur(conn: psycopg.Connection) -> None:
    """`schema_migrations`'ın BOŞ KABUĞUNU (RLS'siz, salt sütun tanımları)
    her modda (dry-run DAHİL) var olduğundan emin olur — bu saf ALTYAPI,
    migration İÇERİĞİ değil; script'in "bekleyen ne var" sorgusu yapabilmesi
    için GEREKLİ (gerçek araçların — Flyway/golang-migrate — hepsi aynı
    desenle çalışır). RLS + politika + grant ise NORMAL migration dosyası
    (`20261004_0001_schema_migrations.sql`) üzerinden, `--uygula`'da
    GERÇEKTEN kalıcı olur, dry-run'da rollback edilir — burada TEKRAR
    oluşturulmaz (`CREATE POLICY`'nin `IF NOT EXISTS`'i YOK, iki kez
    çalıştırılırsa hata verir)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              dosya_adi TEXT PRIMARY KEY,
              dosya_hash TEXT NOT NULL,
              uygulandi_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              uygulayan TEXT NOT NULL,
              sure_ms BIGINT NOT NULL
            )
            """
        )
    conn.commit()


def uygulanmis_migrationlari_oku(conn: psycopg.Connection) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute("SELECT dosya_adi, dosya_hash FROM schema_migrations")
        return dict(cur.fetchall())


def hash_tutarliligini_dogrula(kayitli: dict[str, str], dizin: Path) -> None:
    for dosya_adi, kayitli_hash in kayitli.items():
        yol = dizin / dosya_adi
        if not yol.exists():
            raise DurdurmaHatasi(
                f"{dosya_adi} schema_migrations'da KAYITLI ama diskte YOK"
            )
        gercek_hash = dosya_hash(yol)
        if gercek_hash != kayitli_hash:
            raise DurdurmaHatasi(
                f"{dosya_adi}: KAYITLI hash ({kayitli_hash[:12]}...) diskteki "
                f"dosyayla UYUŞMUYOR ({gercek_hash[:12]}...) — uygulanmış bir "
                "migration SONRADAN DÜZENLENMİŞ. Sessizce geçilmez, elle incele."
            )


def kilidi_dene(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (_ADVISORY_LOCK_KEY,))
        row = cur.fetchone()
    conn.commit()
    return bool(row and row[0])


def kilidi_birak(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s)", (_ADVISORY_LOCK_KEY,))
    conn.commit()


def _veri_farkini_dogrula(once: dict[str, Any], sonra: dict[str, Any]) -> list[str]:
    """Migration'lar (view/index/RLS) VERİ satırına dokunmamalı — herhangi
    bir fark (hedef ay istisnası YOK, `aylik_yukle.py`'nin tersine) hata."""
    sorunlar: list[str] = []
    for tablo, veri in once["tablolar"].items():
        if sonra["tablolar"].get(tablo) != veri:
            sorunlar.append(f"{tablo}: {veri} -> {sonra['tablolar'].get(tablo)}")
    for tablo, ay_veri in once["ay_bazli"].items():
        if ay_veri != sonra["ay_bazli"].get(tablo):
            sorunlar.append(f"{tablo}: ay bazlı sayımlar DEĞİŞTİ")
    if once["batch_durumlari"] != sonra["batch_durumlari"]:
        sorunlar.append(
            f"ingestion_batch durum dağılımı DEĞİŞTİ: "
            f"{once['batch_durumlari']} -> {sonra['batch_durumlari']}"
        )
    if sonra["audit_log_sayisi"] < once["audit_log_sayisi"]:
        sorunlar.append("audit_log sayısı AZALDI (append-only olması gerekirdi)")
    return sorunlar


def _bootstrap_isle(
    database_url: str, kilit_conn: psycopg.Connection, args: argparse.Namespace
) -> int:
    kayitli = uygulanmis_migrationlari_oku(kilit_conn)
    if kayitli:
        raise DurdurmaHatasi(
            f"--bootstrap yalnız BOŞ bir schema_migrations'da çalışır — şu an "
            f"{len(kayitli)} kayıt var. Bu bayrak yalnız BİR KEZ kullanılabilir."
        )
    with kilit_conn.cursor() as cur:
        adaylar = bootstrap_adaylarini_belirle(cur, args.dizin)
    tum_dosyalar = migration_listesi(args.dizin)
    aday_adlari = {y.name for y in adaylar}
    kalanlar = [y.name for y in tum_dosyalar if y.name not in aday_adlari]

    print(f"[BOOTSTRAP] {len(adaylar)} dosya 'uygulanmış' olarak işaretlenecek:")
    for yol in adaylar:
        print(f"  - {yol.name}")
    if kalanlar:
        print(
            f"[BOOTSTRAP] İŞARETLENMEYECEK (normal --dry-run/--uygula akışına "
            f"bırakılıyor): {kalanlar}"
        )

    if not args.uygula:
        print("\n=== BOOTSTRAP DRY-RUN — hiçbir satır yazılmadı ===")
        return 0

    with baglan(database_url) as conn:
        with conn.cursor() as cur:
            for yol in adaylar:
                cur.execute(
                    "INSERT INTO schema_migrations "
                    "(dosya_adi, dosya_hash, uygulayan, sure_ms) "
                    "VALUES (%s, %s, %s, 0)",
                    (yol.name, dosya_hash(yol), args.actor),
                )
        ingest.audit_log_yaz(
            conn,
            table_name="schema_migrations",
            record_id=None,
            action_type="INSERT",
            actor_name=args.actor,
            payload={
                "olay": "bootstrap_isaretleme",
                "dosyalar": [y.name for y in adaylar],
            },
        )
        conn.commit()
    print(f"\n=== BOOTSTRAP TAMAMLANDI — {len(adaylar)} dosya işaretlendi ===")
    return 0


def _tek_dosya_isle(
    conn: psycopg.Connection, yol: Path, uygula: bool, actor: str
) -> int:
    t0 = time.monotonic()
    govde = govde_metni(yol.read_text(encoding="utf-8"))
    with conn.cursor() as cur:
        cur.execute(govde)
    sure_ms = int((time.monotonic() - t0) * 1000)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO schema_migrations "
            "(dosya_adi, dosya_hash, uygulayan, sure_ms) VALUES (%s, %s, %s, %s)",
            (yol.name, dosya_hash(yol), actor, sure_ms),
        )
    ingest.audit_log_yaz(
        conn,
        table_name="schema_migrations",
        record_id=None,
        action_type="INSERT",
        actor_name=actor,
        payload={
            "olay": "migration_uygulandi" if uygula else "migration_dry_run",
            "dosya": yol.name,
            "sure_ms": sure_ms,
        },
    )
    return sure_ms


def _normal_akis_isle(
    database_url: str, kilit_conn: psycopg.Connection, args: argparse.Namespace
) -> int:
    kayitli = uygulanmis_migrationlari_oku(kilit_conn)
    hash_tutarliligini_dogrula(kayitli, args.dizin)

    bekleyenler = [y for y in migration_listesi(args.dizin) if y.name not in kayitli]
    if not bekleyenler:
        print("[OK] Bekleyen migration yok — canlı güncel.")
        return 0

    print(
        "\n=== UYGULANACAK ==="
        if args.uygula
        else "\n=== DRY-RUN — aşağıdakiler GERÇEK transaction içinde işlenip "
        "ROLLBACK edilecek ==="
    )
    for y in bekleyenler:
        print(f"  - {y.name}")

    once = durum_fotografi(kilit_conn)
    uygulanan: list[str] = []

    if args.uygula:
        # Her dosya KENDİ bağlantısında/transaction'ında commit edilir —
        # biri patlarsa ÖNCEKİLER kalıcı kalır, sonrakine GEÇİLMEZ.
        for yol in bekleyenler:
            try:
                with baglan(database_url) as conn:
                    sure_ms = _tek_dosya_isle(conn, yol, args.uygula, args.actor)
                    conn.commit()
            except DurdurmaHatasi:
                raise
            except Exception as e:  # noqa: BLE001 - kasıtlı: her hata DURDU'ya çevrilir
                kalan = [
                    y.name for y in bekleyenler if y.name not in uygulanan and y != yol
                ]
                print(f"  [DURDU] {yol.name}: {e}")
                print(f"  (sıradaki dosyalar İŞLENMEDİ: {kalan})")
                return 1
            print(f"  [OK] {yol.name} ({sure_ms}ms)")
            uygulanan.append(yol.name)
    else:
        # Dry-run: TÜM bekleyenler AYNI transaction'da (aylik_yukle.py'nin
        # "tam sadakatli dry-run" deseniyle TUTARLI) — aksi halde 2. dosya
        # 1. dosyanın (rollback edilmeden önce GEÇİCİ olarak var olan)
        # etkisini GÖREMEZ (örn. bir ALTER TABLE, dry-run'da henüz hiç
        # COMMIT olmamış bir CREATE TABLE'ı referans alamaz) — gerçek bir
        # testle BULUNDU (2 dosyalı sentetik set, 2. dosya 1.'in tablosuna
        # kolon eklemeye çalışıyordu).
        try:
            with baglan(database_url) as conn:
                for yol in bekleyenler:
                    sure_ms = _tek_dosya_isle(conn, yol, args.uygula, args.actor)
                    print(f"  [OK] {yol.name} ({sure_ms}ms)")
                    uygulanan.append(yol.name)
                # Context manager'ın __exit__'i BAŞARIYLA biterse COMMIT eder
                # (psycopg varsayılanı) — dry-run'ın "hiçbir şey yazılmaz"
                # sözünü BAŞARI yolunda da tutmak için burada AÇIKÇA rollback.
                conn.rollback()
        except DurdurmaHatasi:
            raise
        except Exception as e:  # noqa: BLE001 - kasıtlı: her hata DURDU'ya çevrilir
            kalan = [y.name for y in bekleyenler if y.name not in uygulanan]
            print(f"  [DURDU] {kalan[0] if kalan else '?'}: {e}")
            return 1

    sonra = durum_fotografi(kilit_conn)
    farklar = _veri_farkini_dogrula(once, sonra)
    if farklar:
        print("\n[HATA] VERİ SATIRLARINDA FARK BULUNDU (beklenmiyordu):")
        for f in farklar:
            print(f"  {f}")
        return 1

    print(
        f"\n=== {'UYGULANDI' if args.uygula else 'DRY-RUN TAMAMLANDI (hiçbir şey yazılmadı)'}"
        f" — {len(uygulanan)} dosya ==="
    )
    print("[OK] Veri satırlarında fark yok.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--uygula",
        action="store_true",
        help="gerçekten yaz (varsayılan: dry-run, HİÇBİR ŞEY YAZILMAZ)",
    )
    ap.add_argument(
        "--bootstrap",
        action="store_true",
        help="nesne-varlık kontrolüyle mevcut migration'ları işaretle (yalnız BİR KEZ, tablo boşken)",
    )
    ap.add_argument("--dizin", type=Path, default=MIGRATIONS_DIZIN_VARSAYILAN)
    ap.add_argument("--yedek-atla", default=None, metavar="GEREKÇE")
    ap.add_argument(
        "--yedek-max-yas-saat", type=int, default=_VARSAYILAN_YEDEK_MAX_YAS_SAAT
    )
    ap.add_argument("--actor", default="manual-cli:migration-uygula")
    args = ap.parse_args()

    if args.yedek_atla is not None and not args.yedek_atla.strip():
        print("HATA: --yedek-atla gerekçeli verilmeli (boş olamaz).")
        return 1

    try:
        if args.yedek_atla:
            print(f"[YEDEK] kontrolü ATLANDI — gerekçe: {args.yedek_atla}")
        else:
            yas = son_basarili_yedek_yasi()
            if yas is None:
                raise DurdurmaHatasi(
                    "yedek tazeliği DOĞRULANAMADI (GitHub API'ye ulaşılamadı veya "
                    'hiç başarılı koşu yok) — --yedek-atla "<gerekçe>" ile bilinçli geç'
                )
            if yas.total_seconds() > args.yedek_max_yas_saat * 3600:
                raise DurdurmaHatasi(
                    f"son başarılı yedek {yas} önce — {args.yedek_max_yas_saat} "
                    'saatten ESKİ. --yedek-atla "<gerekçe>" ile bilinçli geç'
                )
            print(f"[YEDEK] tazelik doğrulandı: {yas} önce")

        database_url = get_database_url()
        if not database_url:
            raise DurdurmaHatasi("DATABASE_URL tanımlı değil")

        with baglan(database_url) as kilit_conn:
            if not kilidi_dene(kilit_conn):
                raise DurdurmaHatasi(
                    "başka bir migration_uygula koşusu SÜRÜYOR (advisory lock "
                    "alınamadı) — eşzamanlı iki koşu aynı migration'ı uygulamasın"
                )
            try:
                _bare_tablo_olustur(kilit_conn)
                if args.bootstrap:
                    return _bootstrap_isle(database_url, kilit_conn, args)
                return _normal_akis_isle(database_url, kilit_conn, args)
            finally:
                kilidi_birak(kilit_conn)

    except DurdurmaHatasi as e:
        print(f"\n[DURDU] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
