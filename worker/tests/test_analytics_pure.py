"""EPP — worker/analytics.py SAF (DB gerektirmeyen) fonksiyon testleri.

test_analytics_integration.py'den FARKLI olarak DATABASE_URL şartı YOK —
CI'nin "worker" (unit) job'ında da çalışır. `worker/analytics.py`'deki
çoğu fonksiyon DB sorgusu içerdiğinden orada kalıyor; bu dosya yalnız
pandas/tarih hesaplaması yapan, DB'ye dokunmayan fonksiyonlar içindir.
"""

from __future__ import annotations

import pandas as pd

from worker import analytics


def _job_satiri(job_id: int, status: str, next_retry_at: pd.Timestamp | None) -> dict:
    return {
        "job_id": job_id,
        "correlation_id": str(job_id * 10),
        "status": status,
        "attempt_count": 1,
        "next_retry_at": next_retry_at,
        "updated_at": pd.Timestamp("2026-09-01", tz="UTC"),
    }


def test_gecmis_kalan_isleri_bul_bos_dataframe_bos_doner() -> None:
    bos = pd.DataFrame(
        columns=[
            "job_id",
            "correlation_id",
            "status",
            "attempt_count",
            "next_retry_at",
            "updated_at",
        ]
    )
    assert analytics.gecmis_kalan_isleri_bul(bos).empty


def test_gecmis_kalan_isleri_bul_gercek_canli_ornekle() -> None:
    """2026-09-16'da canlıda bulunan GERÇEK örneğin regresyon pini —
    job_id=11, next_retry_at 8 gün geçmiş, status='retrying'."""
    simdi = pd.Timestamp("2026-09-16", tz="UTC")
    joblar = pd.DataFrame(
        [
            _job_satiri(11, "retrying", pd.Timestamp("2026-09-08 12:00", tz="UTC")),
        ]
    )

    gecmis = analytics.gecmis_kalan_isleri_bul(joblar, simdi=simdi)

    assert len(gecmis) == 1
    assert gecmis["job_id"].iloc[0] == 11


def test_gecmis_kalan_isleri_bul_gelecekteki_next_retry_at_dahil_edilmez() -> None:
    """Established/beklenen durum — worker normal ÇALIŞIYORSA next_retry_at
    hep gelecekte olur, uyarı GEREKMEZ."""
    simdi = pd.Timestamp("2026-09-16", tz="UTC")
    joblar = pd.DataFrame(
        [
            _job_satiri(12, "retrying", pd.Timestamp("2026-09-20", tz="UTC")),
        ]
    )

    gecmis = analytics.gecmis_kalan_isleri_bul(joblar, simdi=simdi)

    assert gecmis.empty


def test_gecmis_kalan_isleri_bul_tamamlanmis_isler_dahil_edilmez() -> None:
    """'succeeded'/'failed'/'dead_letter' durumundaki işlerin next_retry_at'i
    geçmişte olsa BİLE (örn. eski bir başarılı iş) uyarıya GİRMEMELİ — yalnız
    GERÇEKTEN bekleyen ('retrying'/'queued') işler dahil edilir."""
    simdi = pd.Timestamp("2026-09-16", tz="UTC")
    joblar = pd.DataFrame(
        [
            _job_satiri(13, "succeeded", pd.Timestamp("2026-09-01", tz="UTC")),
            _job_satiri(14, "dead_letter", pd.Timestamp("2026-09-01", tz="UTC")),
            _job_satiri(15, "failed", pd.Timestamp("2026-09-01", tz="UTC")),
        ]
    )

    gecmis = analytics.gecmis_kalan_isleri_bul(joblar, simdi=simdi)

    assert gecmis.empty


def test_gecmis_kalan_isleri_bul_next_retry_at_bos_olan_queued_is_dahil_edilmez() -> (
    None
):
    """'queued' durumunda next_retry_at genelde NULL olur (henüz hiç
    denenmemiş, ilk sahiplenmeyi bekliyor) — bu durumda 'geçmiş' sayılamaz,
    None ile Timestamp karşılaştırması YAPILMAMALI (TypeError riski)."""
    simdi = pd.Timestamp("2026-09-16", tz="UTC")
    joblar = pd.DataFrame(
        [
            _job_satiri(16, "queued", None),
        ]
    )

    gecmis = analytics.gecmis_kalan_isleri_bul(joblar, simdi=simdi)

    assert gecmis.empty


def test_gecmis_kalan_isleri_bul_karisik_liste_yalniz_dogru_olani_secer() -> None:
    simdi = pd.Timestamp("2026-09-16", tz="UTC")
    joblar = pd.DataFrame(
        [
            _job_satiri(17, "succeeded", pd.Timestamp("2026-09-01", tz="UTC")),
            _job_satiri(18, "retrying", pd.Timestamp("2026-09-08", tz="UTC")),  # geçmiş
            _job_satiri(
                19, "retrying", pd.Timestamp("2026-09-20", tz="UTC")
            ),  # gelecek
            _job_satiri(20, "queued", None),
        ]
    )

    gecmis = analytics.gecmis_kalan_isleri_bul(joblar, simdi=simdi)

    assert list(gecmis["job_id"]) == [18]
