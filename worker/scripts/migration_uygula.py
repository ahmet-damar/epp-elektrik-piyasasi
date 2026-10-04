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
from worker.scripts import rls_canli_kontrol
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


_SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  dosya_adi TEXT PRIMARY KEY,
  dosya_hash TEXT NOT NULL,
  uygulandi_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  uygulayan TEXT NOT NULL,
  sure_ms BIGINT NOT NULL
);
ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS admin_schema_migrations_select ON schema_migrations;
CREATE POLICY admin_schema_migrations_select ON schema_migrations
  FOR SELECT TO admin
  USING (public.current_app_role() = 'admin');
DROP POLICY IF EXISTS admin_schema_migrations_insert ON schema_migrations;
CREATE POLICY admin_schema_migrations_insert ON schema_migrations
  FOR INSERT TO admin
  WITH CHECK (public.current_app_role() = 'admin');
GRANT SELECT, INSERT ON TABLE schema_migrations TO admin;
"""


def _tam_korumali_tablo_olustur(conn: psycopg.Connection) -> bool:
    """`schema_migrations`'ı tablo+RLS+politika+grant TEK transaction'da,
    idempotent olarak kurar — **korumasız bir ARA an hiç oluşmaz** (önce
    tablo, SONRA RLS diye iki ayrı commit YOK). 2026-10-04 (`Claude
    outputs/PROMPT_MIGRATION_KAPAT_2026-10-04.md`) — önceki yazım yalnız
    boş kabuğu (RLS'siz) oluşturup commit ediyordu; canlıda Supabase'in
    KENDİ `ensure_rls` event trigger'ı RLS'i otomatik açtı (ÖLÇÜLEREK
    bulundu — `relrowsecurity=true` ama 0 politika), ama bu platforma
    özel bir şans, kodun kendisi GARANTİ etmiyordu (düz `postgres:16`'da
    — CI/disposable — bu event trigger YOK, gerçekten korumasız bir
    tablo oluşurdu). `DROP POLICY IF EXISTS` + `CREATE POLICY` ile
    idempotent (`CREATE POLICY`'nin kendi `IF NOT EXISTS`'i yok) — ikinci
    çalıştırmada da patlamaz, politikaları TAZELER.

    Döndürdüğü `bool`, tablonun bu çağrıdan ÖNCE canlıda hiç OLMADIĞINI
    (yani şimdi YENİ oluşturulduğunu) söyler — çağıran bunu `[ALTYAPI]`
    satırıyla AÇIKÇA bildirmek için kullanır (dry-run'ın "hiçbir şey
    yazılmadı" derken sessizce DDL commit'lemesi, bu turun bulduğu
    gerçek yanlış-raporlama hatasıydı)."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_class WHERE relname = 'schema_migrations'")
        zaten_var = cur.fetchone() is not None
        cur.execute(_SCHEMA_MIGRATIONS_DDL)
    conn.commit()
    return not zaten_var


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


def _bootstrap_core(
    database_url: str, kilit_conn: psycopg.Connection, args: argparse.Namespace
) -> int:
    """Asıl bootstrap mantığı — tablo BOŞ mu kontrolü HARİÇ (çağıran
    sorumlu). Hem `--bootstrap` hem `--tam` tarafından kullanılır."""
    with kilit_conn.cursor() as cur:
        adaylar = bootstrap_adaylarini_belirle(cur, args.dizin)
    kilit_conn.rollback()  # bkz. _normal_akis_isle'daki kilit notu
    tum_dosyalar = migration_listesi(args.dizin)
    aday_adlari = {y.name for y in adaylar}
    kalanlar = [y.name for y in tum_dosyalar if y.name not in aday_adlari]

    print(
        f"[BOOTSTRAP] {len(adaylar)}/{len(tum_dosyalar)} dosya 'uygulanmış' "
        "olarak işaretlenecek:"
    )
    for yol in adaylar:
        print(f"  - {yol.name}")
    if kalanlar:
        print(
            f"[BOOTSTRAP] İŞARETLENMEYECEK ({len(kalanlar)}/{len(tum_dosyalar)} — "
            f"normal --dry-run/--uygula akışına bırakılıyor): {kalanlar}"
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


def _bootstrap_isle(
    database_url: str, kilit_conn: psycopg.Connection, args: argparse.Namespace
) -> int:
    kayitli = uygulanmis_migrationlari_oku(kilit_conn)
    if kayitli:
        raise DurdurmaHatasi(
            f"--bootstrap yalnız BOŞ bir schema_migrations'da çalışır — şu an "
            f"{len(kayitli)} kayıt var. Bu bayrak yalnız BİR KEZ kullanılabilir."
        )
    return _bootstrap_core(database_url, kilit_conn, args)


def _tam_isle(
    database_url: str, kilit_conn: psycopg.Connection, args: argparse.Namespace
) -> int:
    """`--tam`: tablo boşsa bootstrap'ı yapar, ardından AYNI koşuda
    bekleyen migration'ları uygular — Ahmet'in canlıda çalıştırması
    gereken komutu ikiden bire indirir (2026-10-04, `Claude outputs/
    PROMPT_MIGRATION_KAPAT_2026-10-04.md`). Bootstrap adımı patlarsa
    (bir exception fırlatırsa veya 0'dan farklı dönerse) uygulama
    adımına HİÇ GEÇİLMEZ. Tablo zaten doluysa bootstrap adımı sessizce
    ATLANIR (hata YOK — `--tam` tekrar tekrar çalıştırılabilir olmalı)."""
    kayitli = uygulanmis_migrationlari_oku(kilit_conn)
    if kayitli:
        print(
            f"[TAM] schema_migrations zaten dolu ({len(kayitli)} kayıt) — "
            "bootstrap adımı ATLANDI."
        )
        return _normal_akis_isle(database_url, kilit_conn, args)

    if not args.uygula:
        print("[TAM] schema_migrations BOŞ — bootstrap önizlemesi (dry-run):")
        with kilit_conn.cursor() as cur:
            adaylar = bootstrap_adaylarini_belirle(cur, args.dizin)
        tum_dosyalar = migration_listesi(args.dizin)
        print(
            f"[BOOTSTRAP-ÖNİZLEME] {len(adaylar)}/{len(tum_dosyalar)} dosya "
            "işaretlenecekti:"
        )
        for yol in adaylar:
            print(f"  - {yol.name}")
        print("[TAM] ardından (bootstrap'lanmış SAYILARAK) bekleyenler:")
        return _normal_akis_isle(
            database_url,
            kilit_conn,
            args,
            ek_uygulanmis_adlar=frozenset(y.name for y in adaylar),
        )

    print("[TAM] schema_migrations BOŞ — bootstrap adımı uygulanıyor...")
    try:
        kod = _bootstrap_core(database_url, kilit_conn, args)
    except DurdurmaHatasi as e:
        print(f"[DURDU] bootstrap adımı patladı: {e}")
        print("[TAM] uygulama adımına GEÇİLMEDİ.")
        return 1
    except Exception as e:  # noqa: BLE001 - kasıtlı: bootstrap'ın her hatası DURDU'ya çevrilir
        print(f"[DURDU] bootstrap adımı patladı: {e}")
        print("[TAM] uygulama adımına GEÇİLMEDİ.")
        return 1
    if kod != 0:
        print("[DURDU] bootstrap adımı başarısız döndü — uygulama adımına GEÇİLMEDİ.")
        return 1
    print("[TAM] bootstrap adımı tamamlandı — uygulama adımına geçiliyor.")
    return _normal_akis_isle(database_url, kilit_conn, args)


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
    database_url: str,
    kilit_conn: psycopg.Connection,
    args: argparse.Namespace,
    *,
    ek_uygulanmis_adlar: frozenset[str] = frozenset(),
) -> int:
    """`ek_uygulanmis_adlar`: `--tam`'ın dry-run önizlemesinde, henüz
    GERÇEKTEN yazılmamış (bootstrap dry-run'dan geçen) dosya adlarını
    "zaten uygulanmış SAYARAK" `bekleyenler` listesinden çıkarmak için —
    yoksa önizleme TÜM dosyaları bekleyen sayıp sıfırdan oynatmaya
    çalışırdı (bkz. modül notu: bu YANLIŞ TEMSİL, bootstrap olmadan
    migration geçmişini canlıya karşı tekrar oynatmak güvenli değil)."""
    kayitli = uygulanmis_migrationlari_oku(kilit_conn)
    hash_tutarliligini_dogrula(kayitli, args.dizin)
    # `kilit_conn`'un bu SELECT'i AÇIK bir transaction'da tutması (advisory
    # kilit SESSION-seviyeli, rollback'ten ETKİLENMEZ — bkz. kilidi_dene())
    # — bekleyenlerden biri `schema_migrations`'ın KENDİSİNE `ALTER TABLE`/
    # `CREATE POLICY` uygularsa (tam da `20261004_0001` dosyası), o DDL
    # kilit_conn'un AccessShareLock'unu SERBEST BIRAKANA kadar BEKLER —
    # `_normal_akis_isle` döngüsü bitene kadar kilit_conn hiç kapanmadığı
    # için bu, statement_timeout'a kadar GERÇEKTEN asılı kalır (gerçek bir
    # testle BULUNDU). Döngüden ÖNCE açıkça rollback.
    kilit_conn.rollback()

    bilinen_adlar = set(kayitli) | ek_uygulanmis_adlar
    bekleyenler = [
        y for y in migration_listesi(args.dizin) if y.name not in bilinen_adlar
    ]
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
    kilit_conn.rollback()  # aynı sebep — bkz. yukarıdaki not
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
    ap.add_argument(
        "--tam",
        action="store_true",
        help="tablo boşsa --bootstrap'ı yapar, AYNI koşuda bekleyenleri uygular "
        "(bootstrap patlarsa uygulamaya geçmez; tablo doluysa bootstrap'ı atlar)",
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
    if args.bootstrap and args.tam:
        print(
            "HATA: --bootstrap ve --tam birlikte verilemez (--tam zaten ikisini sırayla yapar)."
        )
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
                if _tam_korumali_tablo_olustur(kilit_conn):
                    print(
                        "[ALTYAPI] schema_migrations oluşturuldu (RLS + "
                        "politika + grant ile, TEK transaction'da)"
                    )
                if args.bootstrap:
                    sonuc = _bootstrap_isle(database_url, kilit_conn, args)
                elif args.tam:
                    sonuc = _tam_isle(database_url, kilit_conn, args)
                else:
                    sonuc = _normal_akis_isle(database_url, kilit_conn, args)
            finally:
                kilidi_birak(kilit_conn)

        if args.uygula and sonuc == 0:
            # Migration uygulayan araç, arkasında korumasız (RLS'siz veya
            # politikasız) bir tablo bırakıp bırakmadığını KENDİSİ söylemek
            # zorunda (bkz. rls_canli_kontrol.py modül notu — bu kontrolün
            # eklenme sebebi tam olarak bu script'in KENDİ önceki bir hatası).
            print("\n[RLS-KONTROL] canlı RLS durumu doğrulanıyor...")
            rls_sonuc = rls_canli_kontrol.main()
            if rls_sonuc != 0:
                print(
                    "[DURDU] migration'lar uygulandı AMA canlıda RLS/politika "
                    "eksiği bulundu — yukarıya bak."
                )
                return rls_sonuc
        return sonuc

    except DurdurmaHatasi as e:
        print(f"\n[DURDU] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
