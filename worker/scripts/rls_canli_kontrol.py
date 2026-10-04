"""EPP — canlı RLS kontrolü (gerçek DB'ye karşı, salt okuma, 2026-10-04,
`Claude outputs/PROMPT_MIGRATION_KAPAT_2026-10-04.md`).

**Neden gerekli:** `worker/validate_rls_static.py` migration DOSYALARINI
okur — bir script'in (migration DEĞİL) canlıya bir tablo yaratıp RLS'siz/
politikasız bırakmasını GÖREMEZ. `migration_uygula.py`'nin kendi önceki
yazımındaki `_bare_tablo_olustur()` tam da bunu yapmıştı: canlıda RLS
Supabase'in KENDİ `ensure_rls` event trigger'ı sayesinde otomatik AÇILDI
(ölçülerek bulundu) ama 0 politikayla — yani şans eseri "açık" değildi
ama BOŞ (fail-closed, ama hâlâ eksik), kod kendisi hiçbir şey garanti
etmiyordu. RLS turunda kapatılan körlüğün (statik kontrol, güncel
migration listesini görmüyordu) tam aynısı, bu kez TERS yönden: tabloyu
bir migration değil bir SCRIPT oluşturdu, statik kontrol onu hiç görmedi.

Bu script `pg_class`/`pg_policies` üzerinden canlıdaki TÜM `public`
tablolarını tarar, RLS'i KAPALI VEYA hiç politikası OLMAYANLARI AYRI
listeler. Bulursa exit 1. `migration_uygula.py`'nin başarılı bir
`--uygula` (veya `--bootstrap --uygula`/`--tam --uygula`) koşusunun
SONUNDA OTOMATİK çağrılır — migration uygulayan araç, arkasında
korumasız tablo bırakıp bırakmadığını KENDİSİ söylemek zorunda.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from worker.db import get_database_url


def kontrol_et(conn: psycopg.Connection) -> tuple[list[str], list[str]]:
    """(rls_kapali, politikasiz) — public şemasındaki her sıradan tablo
    (`relkind='r'`, view/sequence/vb. hariç) için iki ayrı liste döner."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT c.relname, c.relrowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY 1"
        )
        tablolar = cur.fetchall()
        cur.execute(
            "SELECT DISTINCT tablename FROM pg_policies WHERE schemaname = 'public'"
        )
        politikali = {r[0] for r in cur.fetchall()}
    rls_kapali = [ad for ad, acik in tablolar if not acik]
    politikasiz = [ad for ad, _ in tablolar if ad not in politikali]
    return rls_kapali, politikasiz


def main() -> int:
    database_url = get_database_url() or os.environ.get("DATABASE_URL")
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    with psycopg.connect(database_url, connect_timeout=15) as conn:
        conn.read_only = True
        rls_kapali, politikasiz = kontrol_et(conn)
        conn.rollback()

    if not rls_kapali and not politikasiz:
        print(
            "[OK] Canlıdaki tüm public tablolar RLS açık VE en az 1 politikaya sahip."
        )
        return 0

    if rls_kapali:
        print(f"[HATA] RLS KAPALI ({len(rls_kapali)} tablo): {rls_kapali}")
    if politikasiz:
        print(f"[HATA] HİÇ POLİTİKASI YOK ({len(politikasiz)} tablo): {politikasiz}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
