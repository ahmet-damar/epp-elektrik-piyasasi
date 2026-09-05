"""EPP — worker/auth.py birim testleri (DATABASE_URL/canlı Supabase Auth
BAĞIMSIZ — bkz. worker/tests/test_auth_integration.py gerçek Supabase Auth'a
karşı olan kısım için, README Ek D kuralına tabi).
"""

from __future__ import annotations

import base64
import json

import pytest

import worker.auth as auth_modul
from worker.auth import (
    GECERLI_ROLLER,
    GirisKilitli,
    _basarili_giriste_sifirla,
    _basarisiz_deneme_kaydet,
    _jwt_payload_coz,
    _rate_limit_kontrol_et,
    giris_yap,
    rol_baglantisi_ac,
)


@pytest.fixture(autouse=True)
def _rate_limit_sayacini_temizle():
    """Aşama 2 rate-limiting SÜREÇ-İÇİ (modül seviyesi, global) bir sözlük
    kullanıyor — testler arası sızmayı önlemek için her testten önce/sonra
    temizlenir."""
    auth_modul._basarisiz_denemeler.clear()
    yield
    auth_modul._basarisiz_denemeler.clear()


def _sahte_jwt(payload: dict) -> str:
    """Gerçek bir imza taşımayan, yalnız payload çözme testleri için
    sentetik bir JWT üretir (header.payload.signature şekli)."""

    def _b64url(veri: bytes) -> str:
        return base64.urlsafe_b64encode(veri).rstrip(b"=").decode()

    header = _b64url(json.dumps({"alg": "HS256"}).encode())
    govde = _b64url(json.dumps(payload).encode())
    return f"{header}.{govde}.imza-onemli-degil"


def test_jwt_payload_coz_dogru_govdeyi_dondurur() -> None:
    token = _sahte_jwt({"app_metadata": {"role": "viewer"}, "sub": "abc-123"})
    assert _jwt_payload_coz(token) == {
        "app_metadata": {"role": "viewer"},
        "sub": "abc-123",
    }


def test_gecerli_roller_beklenen_uclu() -> None:
    assert GECERLI_ROLLER == {"viewer", "data_operator", "admin"}


def test_rol_baglantisi_ac_whitelist_disi_rol_set_role_e_hic_ulasmadan_hata_verir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kritik güvenlik testi: whitelist dışı bir rol verilirse `ValueError`
    fırlatılmalı VE `psycopg.connect()`'e (dolayısıyla SET ROLE'e) HİÇ
    ulaşılmamalı — SQL injection/keyfi rol geçişine karşı savunmanın
    gerçekten ilk adımda durduğunu kanıtlar."""
    baglanti_denendi = False

    def _sahte_connect(*args: object, **kwargs: object) -> None:
        nonlocal baglanti_denendi
        baglanti_denendi = True
        raise AssertionError("psycopg.connect() ÇAĞRILMAMALIYDI")

    monkeypatch.setattr("worker.auth.psycopg.connect", _sahte_connect)

    with pytest.raises(ValueError, match="Whitelist dışı rol"):
        rol_baglantisi_ac('{"app_metadata": {"role": "admin"}}', "postgres")

    assert not baglanti_denendi


@pytest.mark.parametrize(
    "kotu_rol",
    [
        "postgres",
        "service_role",
        "authenticated",
        "'; DROP TABLE fact_tuketim; --",
        "viewer; SET ROLE admin",
        "",
    ],
)
def test_rol_baglantisi_ac_bilinen_enjeksiyon_denemelerini_reddeder(
    kotu_rol: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _sahte_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("psycopg.connect() ÇAĞRILMAMALIYDI")

    monkeypatch.setattr("worker.auth.psycopg.connect", _sahte_connect)

    with pytest.raises(ValueError, match="Whitelist dışı rol"):
        rol_baglantisi_ac('{"app_metadata": {"role": "admin"}}', kotu_rol)


# ---------------- Aşama 2 (2026-09-05) — login rate-limiting ----------------


def test_rate_limit_besinci_basarisiz_denemeden_sonra_kilitler() -> None:
    email = "test@example.com"
    for _ in range(5):
        _basarisiz_deneme_kaydet(email)
    with pytest.raises(GirisKilitli):
        _rate_limit_kontrol_et(email)


def test_rate_limit_dorduncu_denemede_henuz_kilitlemez() -> None:
    email = "test2@example.com"
    for _ in range(4):
        _basarisiz_deneme_kaydet(email)
    _rate_limit_kontrol_et(email)  # hata fırlatmamalı


def test_rate_limit_basarili_giriste_sifirlanir() -> None:
    email = "test3@example.com"
    for _ in range(4):
        _basarisiz_deneme_kaydet(email)
    _basarili_giriste_sifirla(email)
    _rate_limit_kontrol_et(email)  # sıfırlandığı için hata fırlatmamalı


def test_rate_limit_farkli_email_bagimsiz_sayilir() -> None:
    for _ in range(5):
        _basarisiz_deneme_kaydet("a@example.com")
    _rate_limit_kontrol_et("b@example.com")  # farklı e-posta etkilenmemeli
    with pytest.raises(GirisKilitli):
        _rate_limit_kontrol_et("a@example.com")


def test_giris_yap_kilitliyken_supabase_client_hic_cagrilmaz(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kilitliyken Supabase'e hiç istek atılmamalı — hem gereksiz dış çağrıyı
    önler hem Supabase'in kendi rate-limit'ini gereksiz tüketmez."""
    email = "locked@example.com"
    for _ in range(5):
        _basarisiz_deneme_kaydet(email)

    def _sahte_create_client() -> None:
        raise AssertionError("create_supabase_client() ÇAĞRILMAMALIYDI")

    monkeypatch.setattr(auth_modul, "create_supabase_client", _sahte_create_client)

    with pytest.raises(GirisKilitli):
        giris_yap(email, "herhangi-bir-sifre")


def test_giris_yap_email_normalize_edilerek_sayilir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Büyük/küçük harf veya baştaki/sondaki boşlukla sayaç bypass
    edilememeli — 'Test@Example.com' ve '  test@example.com  ' AYNI
    sayaca yazılmalı."""
    from supabase_auth.errors import AuthApiError

    class SahteAuth:
        def sign_in_with_password(self, _kimlik: dict) -> None:
            raise AuthApiError("bad credentials", 400, None)

    class SahteClient:
        auth = SahteAuth()

    monkeypatch.setattr(auth_modul, "create_supabase_client", lambda: SahteClient())

    for _ in range(5):
        assert giris_yap("Test@Example.com", "yanlis") is None

    with pytest.raises(GirisKilitli):
        giris_yap("  test@example.com  ", "yanlis")
