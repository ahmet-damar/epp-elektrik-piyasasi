"""Paket-genelinde koruma: pytest ASLA canlı Supabase'e karşı tam
çalıştırılamaz.

Neden: 2026-09-02'de tam pytest paketinin (argümansız `-v`) yanlışlıkla
canlı `DATABASE_URL`'e karşı çalıştırılması, `worker/job_worker.py`'nin
async polling yolunun KENDİ commit'lerini yapması (standart `conn`
fixture'ının rollback tabanlı izolasyonunu bypass etmesi) yüzünden 4 fact
tablosunda + `ingestion_batch` + `source_asset` + `dim_tarih`'te kalıcı
test verisi (`tarih_id=209912`, yıl 2099) bırakmıştı — üç turda tespit
edilip temizlendi (bkz. `dokumanlar/06_canli_veri_operasyon_gunlugu.md`,
2026-09-03 girdisi; kural README'de "Canlı Supabase'e Karşı Test
Çalıştırma Kuralı" olarak yazılıydı ama koruma yalnız dokümandaydı, KOD
SEVİYESİNDE yoktu — bu dosya o boşluğu kapatır, 2026-09-07 denetimi C2).

Kasıtlı istisna: `worker/tests/test_auth_integration.py` BİLEREK canlı
Supabase Auth'a karşı çalışır (`DATABASE_URL_DASHBOARD` tanımlıysa;
gerçek e-posta/şifre girişini/rol bağlantısını egzersiz eder — bkz. o
dosyanın docstring'i ve `dokumanlar/10_TEKNIK_MASTER_DOKUMAN.md` §9.4).
Bu bilinçli akışı kırmamak için `ALLOW_DESTRUCTIVE_TESTS=true` kaçış
kapısı bırakıldı — yalnız elle, açıkça set edildiğinde devre dışı kalır.

**2026-09-08'de bulunan boşluk (bu koruma varken bile canlıya sızma
yaşandı, tarih_id=209912'ye AYNI 2026-09-02 deseninde 85 satır + 3 batch +
3 source_asset + 1 dim_tarih — temizlendi, bkz. dokumanlar/06_canli_veri_
operasyon_gunlugu.md 2026-09-08 kaydı):** bu dosya `worker.db`'yi hiç
IMPORT ETMEDEN yalnız `os.environ`'a bakıyordu — eğer kabuk ortamında
`DATABASE_URL` set değilse (örn. elle `Remove-Item Env:DATABASE_URL`),
`pytest_configure` boş görüp GEÇİYORDU; sonra test toplama sırasında ilk
`worker.db` import'u kendi `load_dotenv()`'ini çalıştırıp `.env`'den canlı
`DATABASE_URL`'i SESSİZCE process ortamına yüklüyordu — koruma artık
etkisizdi. Düzeltme: bu dosya da `worker.db`'yi import ediyor (bu onun
`load_dotenv()`'ini TETİKLER, `override=False` olduğundan zaten set bir
kabuk değişkenini BOZMAZ) — kontrol artık test toplamasının göreceğiyle
AYNI, nihai `DATABASE_URL` değerine bakıyor.
"""

from __future__ import annotations

import os

import pytest

# .env'i BURADA, kontrolden ÖNCE yükle (worker.db'nin kendi load_dotenv()
# çağrısını tetikler) — aksi halde bu dosya boş os.environ görüp geçer,
# sonra bir test modülünün İLK worker.db import'u .env'deki canlı
# DATABASE_URL'i sessizce process'e yükler ve koruma atlanmış olur
# (2026-09-08'de gerçekten yaşandı, yukarıdaki modül notuna bkz.).
import worker.db  # noqa: F401

# Canlı Supabase projelerinin connection string'lerinde her zaman geçen
# host parçaları. CI'nin kendi disposable postgres:16 container'ı
# (`localhost`/`postgres` host'u) bunlardan hiçbirini içermez.
_PROD_ISARETLERI = ("supabase.co", "supabase.com", "pooler.supabase")

_KONTROL_EDILEN_DEGISKENLER = ("DATABASE_URL", "DATABASE_URL_DASHBOARD")

_KACIS_KAPISI_DEGISKENI = "ALLOW_DESTRUCTIVE_TESTS"


def _maskele(url: str) -> str:
    """Hata mesajında şifreyi göstermeden yalnız host'u ortaya koyar."""
    if "@" in url:
        return "***@" + url.rsplit("@", 1)[-1]
    return "(ayrıştırılamadı)"


def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get(_KACIS_KAPISI_DEGISKENI) == "true":
        return

    for degisken in _KONTROL_EDILEN_DEGISKENLER:
        url = os.environ.get(degisken, "")
        if url and any(isaret in url for isaret in _PROD_ISARETLERI):
            pytest.exit(
                f"{degisken} canlı Supabase'i gösteriyor gibi görünüyor "
                f"({_maskele(url)}). Test paketi canlı veritabanına karşı "
                "çalıştırılamaz (bkz. README 'Canlı Supabase'e Karşı Test "
                "Çalıştırma Kuralı'). Bilerek canlıya karşı çalıştırmak "
                f"istiyorsanız (örn. test_auth_integration.py) "
                f"{_KACIS_KAPISI_DEGISKENI}=true ortam değişkenini set edin.",
                returncode=3,
            )
