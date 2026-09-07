"""EPP — Rol bazlı erişim doğrulaması (gerçek DB'ye karşı, GRANT+RLS
davranışını canlı test eder — worker/validate_rls_static.py'nin statik
metin taramasından FARKLI, gerçekten `SET ROLE` yapıp sorgu çalıştırır).

Bkz. supabase/ci-only/01_roles_bootstrap.sql — anon/authenticated/
service_role rolleri CI'da bu script'ten önce bootstrap edilir.

Test edilen 3 senaryo (hepsi `veri_kapsam_disi` üzerinde, tek bir
transaction içinde, SAVEPOINT'lerle izole, sonunda TAMAMEN rollback —
hangi DB'ye karşı çalıştırılırsa çalıştırılsın kalıcı iz bırakmaz):

1. **anon** — GRANT seviyesinde tamamen dışlanmış (migration 20260819_0013,
   `REVOKE ALL ... FROM anon`). Beklenen: "permission denied for TABLE
   veri_kapsam_disi" (bir SCHEMA-seviyesi red DEĞİL — o CI'a özgü bir
   bootstrap eksikliği olurdu; TABLE-seviyesi red gerçek Supabase'deki
   TASARIM gereği doğru davranıştır, anon hiçbir tabloya GRANT edilmemiş).
2. **viewer, JWT claim'siz** — `current_app_role()` NULL döner (auth.jwt()
   NULL), RLS politikası (`USING (current_app_role() = 'viewer')`) hiçbir
   satırı geçirmez. Beklenen: sorgu BAŞARILI çalışır, 0 satır döner (RLS
   filtreleme — GRANT seviyesinde izin VAR, satır seviyesinde YOK).
3. **viewer, doğru JWT claim ile** — `request.jwt.claims` GUC'u
   `{"app_metadata":{"role":"viewer"}}` olarak ayarlanır, `current_app_role()`
   'viewer' döner, RLS politikası test satırını geçirir. Beklenen: sorgu
   BAŞARILI çalışır, EN AZ 1 satır döner (script'in kendi eklediği test
   satırı dahil).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worker.db import get_database_url

_SENTINEL_TARIH_ID = 999912  # yıl 9999 - gerçek veriyle asla çakışmaz


def main() -> int:
    database_url = get_database_url() or os.environ.get("DATABASE_URL")
    if not database_url:
        print("HATA: DATABASE_URL tanımlı değil.")
        return 1

    with psycopg.connect(database_url) as conn:
        conn.autocommit = False
        try:
            _test_tum_tablolarda_rls_ve_policy_var(conn)
            _hazirla(conn)
            _test_anon_table_level_denied(conn)
            _test_viewer_claimsiz_sifir_satir(conn)
            _test_viewer_dogru_claim_ile_satir_doner(conn)
        finally:
            conn.rollback()  # hiçbir kalıcı iz bırakma - test verisi dahil

    print("\nRol bazlı erişim doğrulaması TAMAMEN geçti.")
    return 0


def _test_tum_tablolarda_rls_ve_policy_var(conn: psycopg.Connection) -> None:
    """C4 (2026-09-07): 'public' şemasındaki HER tabloda RLS AÇIK ve EN AZ
    1 policy VAR — istisnasız. worker/validate_rls_static.py'nin metin
    taraması (yalnız 3 sabit dosyaya bakar) bunu YAKALAYAMAZ; bu yüzden
    canlı DB'nin (ya da CI'nin disposable postgres:16'sının) gerçek
    `pg_class`/`pg_policies` durumuna karşı DİNAMİK olarak kontrol edilir
    — hangi migration'ın RLS'i açtığı/kapattığı önemsiz, yalnız SONUÇ
    durumu önemli. 2026-09-04'teki 8 tablolık "RLS açık ama policy'siz"
    kör noktasının (dim_*/sistem_parametre/kpi_esik/job_status) sebebi
    tam olarak böyle bir kontrolün hiç var olmamasıydı — bu fonksiyon o
    boşluğu kapatır. İleride eklenen HER yeni tablo bu kontrolden geçmek
    zorunda; istisna listesi YOK."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.relname,
                   c.relrowsecurity,
                   COUNT(p.polname)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_policy p ON p.polrelid = c.oid
            WHERE n.nspname = 'public' AND c.relkind = 'r'
            GROUP BY c.relname, c.relrowsecurity
            ORDER BY c.relname
        """)
        satirlar = cur.fetchall()
    if not satirlar:
        raise AssertionError(
            "public şemasında hiç tablo bulunamadı - beklenmeyen boş sonuç"
        )
    sorunlu = [
        (ad, rls_acik, policy_sayisi)
        for ad, rls_acik, policy_sayisi in satirlar
        if not rls_acik or policy_sayisi == 0
    ]
    if sorunlu:
        detay = "; ".join(
            f"{ad} (RLS={'açık' if rls else 'KAPALI'}, {n} policy)"
            for ad, rls, n in sorunlu
        )
        raise AssertionError(
            f"{len(sorunlu)} tabloda RLS kapalı ve/veya hiç policy yok "
            f"(istisna YOK - her public tablo RLS açık + ≥1 policy'e "
            f"sahip olmalı): {detay}"
        )
    print(
        f"[OK] public şemasındaki {len(satirlar)} tablonun TAMAMI RLS açık "
        "+ en az 1 policy'e sahip (istisna yok)"
    )


def _hazirla(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_tarih (tarih_id, yil, ay, ceyrek, ay_adi, yil_ay, donem_tipi)
            VALUES (%s, 9999, 12, 4, 'Aralık', '9999-12', 'aylik')
            ON CONFLICT (tarih_id) DO UPDATE SET tarih_id = EXCLUDED.tarih_id
            """,
            (_SENTINEL_TARIH_ID,),
        )
        cur.execute(
            """
            INSERT INTO veri_kapsam_disi (tarih_id, fact_tablosu, nitelik, sebep, karar_referansi)
            VALUES (%s, 'fact_uretim', 'validate_role_access_test', 'test satırı', 'test')
            ON CONFLICT (tarih_id, fact_tablosu, nitelik) DO UPDATE SET sebep = EXCLUDED.sebep
            """,
            (_SENTINEL_TARIH_ID,),
        )


def _test_anon_table_level_denied(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SAVEPOINT sp_anon")
        cur.execute("SET LOCAL ROLE anon")
        try:
            cur.execute("SELECT * FROM veri_kapsam_disi")
        except psycopg.errors.InsufficientPrivilege as e:
            mesaj = str(e)
            if "schema" in mesaj.lower():
                raise AssertionError(
                    f"anon SCHEMA seviyesinde reddedildi (YANLIŞ - bu CI'a özgü bir "
                    f"bootstrap eksikliği olurdu, gerçek Supabase'de görülmez): {mesaj}"
                ) from e
            if "veri_kapsam_disi" not in mesaj:
                raise AssertionError(
                    f"Beklenmeyen izin hatası (tablo adı geçmiyor): {mesaj}"
                ) from e
            print(
                f"[OK] anon: TABLE seviyesinde reddedildi (beklenen, tasarım gereği): {mesaj.strip()}"
            )
        else:
            raise AssertionError(
                "anon veri_kapsam_disi'ni SORGULAYABİLDİ - migration 20260819_0013'ün "
                "'REVOKE ALL ... FROM anon' satırı etkisiz kalmış olabilir"
            )
        finally:
            cur.execute("ROLLBACK TO SAVEPOINT sp_anon")


def _test_viewer_claimsiz_sifir_satir(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SAVEPOINT sp_viewer_claimsiz")
        cur.execute("SET LOCAL ROLE viewer")
        # request.jwt.claims BİLİNÇLİ OLARAK ayarlanmıyor - current_app_role()
        # NULL dönmeli, RLS hiçbir satırı geçirmemeli.
        cur.execute("SELECT * FROM veri_kapsam_disi")
        satirlar = cur.fetchall()
        cur.execute("ROLLBACK TO SAVEPOINT sp_viewer_claimsiz")
    if satirlar:
        raise AssertionError(
            f"viewer (JWT claim'siz) {len(satirlar)} satır gördü - RLS politikası "
            "(current_app_role() = 'viewer') NULL claim'i yanlışlıkla geçiriyor olabilir"
        )
    print(
        "[OK] viewer (JWT claim'siz): sorgu BAŞARILI çalıştı, 0 satır (RLS doğru filtreliyor)"
    )


def _test_viewer_dogru_claim_ile_satir_doner(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SAVEPOINT sp_viewer_claimli")
        cur.execute("SET LOCAL ROLE viewer")
        cur.execute(
            'SET LOCAL request.jwt.claims = \'{"app_metadata": {"role": "viewer"}}\''
        )
        cur.execute(
            "SELECT * FROM veri_kapsam_disi WHERE tarih_id = %s", (_SENTINEL_TARIH_ID,)
        )
        satirlar = cur.fetchall()
        cur.execute("ROLLBACK TO SAVEPOINT sp_viewer_claimli")
    if not satirlar:
        raise AssertionError(
            "viewer (doğru JWT claim ile) hiç satır göremedi - GRANT SELECT ON TABLE "
            "veri_kapsam_disi TO viewer eksik olabilir, ya da RLS politikası "
            "current_app_role()'ü doğru okumuyor olabilir"
        )
    print(
        f"[OK] viewer (app_metadata.role=viewer JWT claim'i ile): sorgu BAŞARILI, "
        f"{len(satirlar)} satır döndü (RLS + GRANT ikisi de doğru çalışıyor)"
    )


if __name__ == "__main__":
    sys.exit(main())
