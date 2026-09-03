"""EPP — worker/auth.py birim testleri (DATABASE_URL/canlı Supabase Auth
BAĞIMSIZ — bkz. worker/tests/test_auth_integration.py gerçek Supabase Auth'a
karşı olan kısım için, README Ek D kuralına tabi).
"""

from __future__ import annotations

import base64
import json

import pytest

from worker.auth import GECERLI_ROLLER, _jwt_payload_coz, rol_baglantisi_ac


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
