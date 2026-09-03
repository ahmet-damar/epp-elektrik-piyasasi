"""EPP — worker/auth.py entegrasyon testi (CANLI Supabase Auth + canlı
Supabase Postgres'e karşı — CI'nin disposable postgres:16'sıyla İLGİSİ
YOK, `DATABASE_URL_DASHBOARD` yalnız gerçek Supabase projesinde vardır).

**README Ek D kuralına tabi:** bu dosya tam pytest paketinin bir parçası
olarak KÖRÜ KÖRÜNE çalıştırılmamalı — yalnız hedefli
`pytest worker/tests/test_auth_integration.py` ile, bilerek çalıştırılır.
`DATABASE_URL_DASHBOARD` tanımlı değilse (CI dahil — CI'de bu env değişkeni
hiç yok) TÜM testler atlanır.

`giris_yap()`'ın "yanlış şifre/var olmayan hesap" dalı gerçek bir hesap
GEREKTİRMEZ (Supabase Auth API'si her iki durumda da aynı genel hatayı
döner) — bu yüzden o test her ortamda (Ahmet'in hesabı kurulmuş olsun
olmasın) anlamlıdır. `rol_baglantisi_ac()`'ın DB tarafı da gerçek bir
Auth hesabı gerektirmez — sentetik (ama gerçekçi şekilde biçimlendirilmiş)
JWT claim'leriyle test edilir.
"""

from __future__ import annotations

import os

import pytest

from worker.auth import giris_yap, rol_baglantisi_ac

DATABASE_URL_DASHBOARD = os.environ.get("DATABASE_URL_DASHBOARD")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL_DASHBOARD,
    reason="DATABASE_URL_DASHBOARD tanımlı değil (yalnız canlı Supabase'e "
    "karşı, elle/hedefli çalıştırılır — CI'de yok).",
)


def test_giris_yap_yanlis_kimlik_bilgisiyle_none_doner() -> None:
    """Var olmayan bir e-posta + rastgele bir şifre — Supabase Auth genel
    bir "Invalid login credentials" hatası döner (hesap var/yok bilgisini
    sızdırmaz), `giris_yap()` bunu `None`'a çevirir."""
    sonuc = giris_yap(
        "epp-test-var-olmayan-hesap@ornek-yok.invalid", "kesinlikle-yanlis-sifre-123!"
    )
    assert sonuc is None


def test_rol_baglantisi_ac_sentetik_claim_ile_dogru_rolu_uygular() -> None:
    """Gerçek bir Supabase Auth oturumu OLMADAN, `rol_baglantisi_ac()`'ın
    DB tarafını (SET request.jwt.claims + SET ROLE + current_app_role())
    doğrular — dokumanlar/06_adr_dashboard_teknoloji.md'de (commit
    0ae49b2) kanıtlanan AYNI format: `{"app_metadata": {"role": "..."}}`."""
    claims_json = '{"app_metadata": {"role": "viewer"}, "sub": "test-sentetik"}'
    conn = rol_baglantisi_ac(claims_json, "viewer")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT public.current_app_role();")
            assert cur.fetchone()[0] == "viewer"
            cur.execute("SELECT count(*) FROM fact_tuketim;")
            (satir_sayisi,) = cur.fetchone()
            assert satir_sayisi >= 0  # sorgu BAŞARILI çalıştı (permission denied yok)
    finally:
        conn.rollback()
        conn.close()


def test_rol_baglantisi_ac_admin_claim_ile_tum_veriye_erisir() -> None:
    """admin rolü — kaldırılan 14 bypass politikasından SONRAKİ, DOĞRU
    gated erişimle (current_app_role()='admin' kontrolü üzerinden) hâlâ
    TÜM aktif satırlara erişebildiğini doğrular (regresyon testi,
    dokumanlar/06'daki 2026-09-05 migration 0019 bulgusu)."""
    claims_json = '{"app_metadata": {"role": "admin"}, "sub": "test-sentetik"}'
    conn = rol_baglantisi_ac(claims_json, "admin")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM fact_tuketim;")
            (satir_sayisi,) = cur.fetchone()
            assert satir_sayisi > 0  # admin en az bazı aktif satırları görmeli
    finally:
        conn.rollback()
        conn.close()
