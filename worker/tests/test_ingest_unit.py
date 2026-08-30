"""EPP — worker/ingest.py saf fonksiyon testleri (DB gerektirmez)."""

from __future__ import annotations

import hashlib

import pytest

from worker import ingest


def test_dosya_hash() -> None:
    assert ingest.dosya_hash(b"") == hashlib.sha256(b"").hexdigest()
    assert ingest.dosya_hash(b"test") == hashlib.sha256(b"test").hexdigest()


def test_tarih_bilesenleri_aylik() -> None:
    b = ingest.tarih_bilesenleri(202601)
    assert b == {
        "yil": 2026,
        "ay": 1,
        "ceyrek": 1,
        "ay_adi": "Ocak",
        "yil_ay": "2026-01",
        "donem_tipi": "aylik",
    }


def test_tarih_bilesenleri_yillik() -> None:
    b = ingest.tarih_bilesenleri(202500)
    assert b == {
        "yil": 2025,
        "ay": 0,
        "ceyrek": 0,
        "ay_adi": None,
        "yil_ay": "2025",
        "donem_tipi": "yillik",
    }


def test_donem_saat_sayisi_aylik() -> None:
    assert ingest.donem_saat_sayisi(202601) == 31 * 24  # Ocak
    assert ingest.donem_saat_sayisi(202602) == 28 * 24  # Şubat, 2026 artık yıl değil
    assert ingest.donem_saat_sayisi(202404) == 30 * 24  # Nisan


def test_donem_saat_sayisi_yillik() -> None:
    assert ingest.donem_saat_sayisi(202500) == 365 * 24
    assert ingest.donem_saat_sayisi(202400) == 366 * 24  # 2024 artık yıl


@pytest.mark.parametrize(
    ("ay", "beklenen_ceyrek", "beklenen_ay_adi"),
    [
        (1, 1, "Ocak"),
        (3, 1, "Mart"),
        (4, 2, "Nisan"),
        (9, 3, "Eylül"),
        (12, 4, "Aralık"),
    ],
)
def test_tarih_bilesenleri_ceyrek(
    ay: int, beklenen_ceyrek: int, beklenen_ay_adi: str
) -> None:
    b = ingest.tarih_bilesenleri(2026 * 100 + ay)
    assert b["ceyrek"] == beklenen_ceyrek
    assert b["ay_adi"] == beklenen_ay_adi


@pytest.mark.parametrize(
    ("girdi", "beklenen"),
    [(None, None), (float("nan"), None), (5, 5.0), (5.5, 5.5), (0, 0.0)],
)
def test_sayisal_temiz(girdi: object, beklenen: float | None) -> None:
    sonuc = ingest._sayisal_temiz(girdi)
    if beklenen is None:
        assert sonuc is None
    else:
        assert sonuc == pytest.approx(beklenen)


def test_dim_lisans_kodu_eslemesi() -> None:
    assert ingest._LISANS_KODU["Lisanslı"] == "Lisansli"
    assert ingest._LISANS_KODU["Lisanssız"] == "Lisanssiz"
