"""EPP — `app/dashboard.py`'nin "onay bekleyen batch" uyarısının
entegrasyon testi. (`Claude outputs/PROMPT_KONTROL_DENETIMI_2026-09-20.md`
Görev D, 2026-09-20)

**Neden önceden yazılmamıştı:** batch durum makinesi turu (`Claude
outputs/kapanis_2026-09-19_batch_durum.md`, Görev 3) bu uyarıyı
"Streamlit test altyapısı yok" gerekçesiyle atlamıştı. Bu gerekçe artık
GEÇERSİZ — `streamlit.testing.v1.AppTest` (Streamlit'in KENDİ resmi
headless test aracı) `Claude outputs/kapanis_2026-09-20_ui_zaman_serisi.md`
turunda uçtan uca çalıştığı KANITLANDI (2 gerçek bug bile bulundu).

**2026-09-20 (`Claude outputs/PROMPT_TEST_IZOLASYON_2026-09-20.md`) —
KÖK NEDEN teşhisi:** bu test İLK yazıldığında yalnız bir `ingestion_
batch` satırı oluşturuyordu, hiç `fact_tuketim` satırı EKLEMİYORDU.
`app/dashboard.py:701-708` şu sırayı izliyor: `donemler_getir()`
(`fact_tuketim`'de EN AZ bir aktif satırı olan dönemleri arar) boş
dönerse `st.error()` + `st.stop()` ile script HEMEN durur — "onay
bekliyor" uyarısı kodunun çok öncesinde. FRESH disposable'da (bu turun
Görev 1 rebuild'i sonrası) `fact_tuketim` HİÇ satır içermediğinden bu
her seferinde `st.stop()`'a çarpıyordu (kanıt: `at.title`/`at.subheader`
BOŞ, yalnız `st.stop()`'tan ÖNCEKİ tek `st.info()` görünüyordu — hiçbir
exception YOKTU, çünkü `st.stop()` Streamlit'in normal script-sonlandırma
sinyali, hata değil). Önceki (yanlış) hipotez — `st.cache_data`'nın
process-geneli kalıcılığı — `st.cache_data.clear()` ile test edilip
ÇÜRÜTÜLDÜ (fark yaratmadı). Gerçek düzeltme: fixture artık bir `fact_
tuketim` satırı da ekliyor, `donemler_getir()`'in boş dönmesini önlüyor.

`AppTest`, `app/dashboard.py`'yi GERÇEKTEN çalıştırır — kendi `os.environ`
tabanlı `DATABASE_URL` bağlantısını açar, standart `conn` fixture'ının
rollback izolasyonunu KULLANAMAZ. Test verisi bu yüzden KOMMİT edilir ve
`finally`'de elle temizlenir — established sentinel-tarih_id deseni
(`worker/tests/test_job_worker_integration.py`'nin `_TEST_TARIH_ID`
notuyla AYNI ilke: gerçek veriyle ASLA çakışmayan, uzak-gelecek bir
`tarih_id`)."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from worker import ingest

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tanımlı değil (yalnız CI 'integration' job'ında çalışır)",
)

_TEST_TARIH_ID = (
    999801  # yıl 9998 — established sentinel deseni, gerçek veriyle çakışmaz
)
_DASHBOARD_PATH = str(Path(__file__).resolve().parents[2] / "app" / "dashboard.py")


def test_onay_bekleyen_batch_uyarisi_gorunur(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Bir batch `status='onay_bekliyor'`a geçirilirse, dashboard'un
    "Sistem Durumu" bölümünde doğru batch_id'yi içeren bir `st.warning()`
    görünmeli — `running_batch_kontrolu.onay_bekleyen_batchleri_bul()`'un
    (zaten test edilmiş) UI'ye doğru bağlandığının kanıtı."""
    # AppTest 'DATABASE_URL_DASHBOARD' tanımlıysa giriş ekranını (kimlik
    # doğrulama) gösterir — established UI smoke-test deseniyle AYNI,
    # kaçış: girişsiz eski DATABASE_URL yolunu zorla.
    monkeypatch.delenv("DATABASE_URL_DASHBOARD", raising=False)
    from streamlit.testing.v1 import AppTest

    assert (
        DATABASE_URL is not None
    )  # pytestmark zaten garanti ediyor, mypy için daraltma
    conn = psycopg.connect(DATABASE_URL)
    ingest.dim_tarih_getir_veya_olustur(conn, _TEST_TARIH_ID)
    source_asset_id = ingest.kaynak_asset_olustur(
        conn,
        source_type="epdk_aylik",
        dosya_adi="test_onay_bekliyor.xlsx",
        icerik=b"test-onay-bekliyor",
        donem_tipi="aylik",
        source_period="9998-01",
    )
    batch_id = ingest.batch_olustur(conn, source_asset_id, "test-onay-bekliyor", "s1")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ingestion_batch SET status='onay_bekliyor', error_summary=%s WHERE batch_id=%s",
            ("test: mutabakat uyuşmadı (dashboard testi)", batch_id),
        )
        # `app/dashboard.py`'nin `donemler_getir()`'i (fact_tuketim'de EN AZ
        # bir aktif satırı olan dönemleri arar) boş dönerse script `st.stop()`
        # ile HEMEN durur, onay-bekliyor uyarısına hiç ulaşmaz — bu satır
        # olmadan test FRESH disposable'da HER ZAMAN yanlış nedenle
        # başarısız olurdu (bkz. modül notu).
        cur.execute("SELECT grup_id FROM dim_tuketici_grubu WHERE grup_adi = 'Mesken'")
        grup_id_satir = cur.fetchone()
        assert grup_id_satir is not None
        grup_id = grup_id_satir[0]
        cur.execute(
            """
            INSERT INTO fact_tuketim
                (il_kodu, tarih_id, grup_id, baglanti, tuketim_mwh, ingestion_batch_id, is_active)
            VALUES (6, %s, %s, 'dagitim', 1.0, %s, true)
            """,
            (_TEST_TARIH_ID, grup_id, batch_id),
        )
    conn.commit()

    try:
        at = AppTest.from_file(_DASHBOARD_PATH, default_timeout=60)
        at.run()

        assert len(at.exception) == 0, [
            e.value if hasattr(e, "value") else e for e in at.exception
        ]
        uyarilar = [w.value for w in at.warning]
        eslesen = [u for u in uyarilar if "onay bekliyor" in u and str(batch_id) in u]
        assert eslesen, (
            f"batch_id={batch_id} için 'onay bekliyor' uyarısı bulunamadı. "
            f"Görülen uyarılar: {uyarilar}"
        )
    finally:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM fact_tuketim WHERE ingestion_batch_id = %s", (batch_id,)
            )
            cur.execute("DELETE FROM ingestion_batch WHERE batch_id = %s", (batch_id,))
            cur.execute(
                "DELETE FROM source_asset WHERE source_asset_id = %s",
                (source_asset_id,),
            )
            cur.execute("DELETE FROM dim_tarih WHERE tarih_id = %s", (_TEST_TARIH_ID,))
        conn.commit()
        conn.close()
