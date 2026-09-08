"""EPP — `worker/tests/conftest.py`'nin canlı-DB koruması için regresyon
testi (2026-09-09, gece çalışması MADDE 0).

**Neden bu test yok muydu, neden şimdi ekleniyor:** koruma iki kez
sessizce delindi — 2026-09-02'de (koruma o zaman hiç yoktu) ve
2026-09-08'de (koruma VARDI ama `.env`'in kontrolden SONRA yüklenmesi
yüzünden atlandı, bkz. `conftest.py`'nin 2026-09-08 modül notu ve
`dokumanlar/06_canli_veri_operasyon_gunlugu.md` 2026-09-08 (devam)
kaydı). İkisi de elle canlıda reprodüksiyonla doğrulandı ama kod
seviyesinde KİLİTLENMEMİŞTİ — bu dosya o boşluğu kapatır.

**Yöntem:** `worker/tests/conftest.py`'nin GÜNCEL kaynağı, izole bir
geçici "sahte proje" içine (kendi `worker/db.py` test-double'ı + kendi
`.env`'i ile) kopyalanıp `python -m pytest` subprocess olarak orada
çalıştırılır — gerçek pytest oturumumuzu ASLA bozmaz, gerçek `.env`'e
HİÇ DOKUNMAZ (yalnız sahte projenin İÇİNDE, kendi ayrı bir `.env`
dosyası var). Sahte `worker/db.py`, gerçek `worker/db.py` ile AYNI
`load_dotenv()` deseni taşır ki test_b senaryosu (yalnız `.env`
sağlıyor) gerçek 2026-09-08 bug'ını doğru şekilde reprodükte etsin.

Üç senaryo:
1. `test_dogrudan_env_degiskeni_ile_engellenir` — `DATABASE_URL` doğrudan
   subprocess ortamında sahte-canlı bir URL'e (pooler.supabase.com
   içeren) set edilir → exit code 3 beklenir.
2. `test_env_dosyasi_kontrolden_sonra_yuklenince_bile_engellenir` — asıl
   2026-09-08 hatasının reprodüksiyonu: `DATABASE_URL` subprocess
   ortamında HİÇ set DEĞİL, yalnız sahte projenin `.env` dosyasında var
   — koruma yine de yakalamalı (eski/buggy sürümde bu senaryo SESSİZCE
   geçerdi).
3. `test_allow_destructive_tests_kacis_kapisi_calisir` — aynı sahte-canlı
   URL + `ALLOW_DESTRUCTIVE_TESTS=true` → koruma devre dışı kalmalı,
   toplama devam etmeli (bunu, BİLEREK başarısız olan bir sahte testin
   gerçekten ÇALIŞTIĞINI — yani `pytest.exit`'in hiç tetiklenmediğini —
   görerek kanıtlıyoruz, yalnız "exit code != 3" yetmez çünkü pytest'in
   kendi toplama hatası da 3'ten farklı bir kod verebilir).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_GERCEK_CONFTEST = Path(__file__).parent / "conftest.py"

_SAHTE_CANLI_URL = (
    "postgresql://fake_user:fake_pass@aws-0-eu-central-1.pooler.supabase.com:"
    "6543/postgres"
)


def _sahte_proje_kur(tmp_path: Path, *, env_dosyasi_icerigi: str | None) -> Path:
    """Gerçek `worker/tests/conftest.py`'nin GÜNCEL içeriğini, kendi
    `worker/db.py` test-double'ı olan izole bir sahte proje köküne
    kopyalar. `env_dosyasi_icerigi` verilirse sahte projenin KENDİ
    `.env`'i olarak yazılır (gerçek proje `.env`'ine ASLA dokunulmaz)."""
    proje = tmp_path / "sahte_proje"
    worker_dir = proje / "worker"
    tests_dir = worker_dir / "tests"
    tests_dir.mkdir(parents=True)

    (worker_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    # Gerçek worker/db.py ile AYNI desen: load_dotenv() modül seviyesinde,
    # override=False (varsayılan) — test_b'nin ".env kontrolden SONRA
    # yüklenirse bile yakalanmalı" senaryosu bunu gerektiriyor.
    (worker_dir / "db.py").write_text(
        "from dotenv import load_dotenv\n\nload_dotenv()\n",
        encoding="utf-8",
    )

    # Gerçek koruma dosyasının GÜNCEL kaynağını birebir kopyala — bu test
    # bir KOPYAYI değil, ŞU ANKİ gerçek dosyayı sınıyor.
    (tests_dir / "conftest.py").write_text(
        _GERCEK_CONFTEST.read_text(encoding="utf-8"), encoding="utf-8"
    )

    (tests_dir / "test_sahte.py").write_text(
        "def test_korumadan_gecerse_buraya_ulasilmamali():\n"
        "    assert False, (\n"
        "        'Guard tetiklenmedi, sahte test calisti — bu YALNIZ '\n"
        "        'ALLOW_DESTRUCTIVE_TESTS=true senaryosunda beklenir.'\n"
        "    )\n",
        encoding="utf-8",
    )

    if env_dosyasi_icerigi is not None:
        (proje / ".env").write_text(env_dosyasi_icerigi, encoding="utf-8")

    return proje


def _pytest_calistir(
    proje: Path, *, ekstra_env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Sahte projede `python -m pytest worker/tests -q` subprocess'ini,
    gerçek `DATABASE_URL`/`DATABASE_URL_DASHBOARD`/`ALLOW_DESTRUCTIVE_
    TESTS` kalıntılarından TAMAMEN arındırılmış bir ortamda çalıştırır —
    bu üç değişken yalnız `ekstra_env`'den gelir (varsayılan: hiçbiri set
    değil)."""
    import os

    env = dict(os.environ)
    for degisken in (
        "DATABASE_URL",
        "DATABASE_URL_DASHBOARD",
        "ALLOW_DESTRUCTIVE_TESTS",
    ):
        env.pop(degisken, None)
    # alt süreç Türkçe karakterleri (guard mesajındaki "canlı" gibi) UTF-8
    # yazsın — Windows'ta yerel kod sayfası varsayılanı bozuyor.
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(ekstra_env)

    return subprocess.run(
        [sys.executable, "-m", "pytest", "worker/tests", "-q"],
        cwd=proje,
        env=env,
        capture_output=True,
        encoding="utf-8",  # text=True Windows'ta yerel kod sayfasını (cp1254
        # vb.) kullanır — Türkçe karakterleri bozar; UTF-8 açıkça istenmeli.
        timeout=60,
        check=False,  # exit code'u BİZ yorumluyoruz (3 mü, 1 mi) — raise etmesin
    )


def test_dogrudan_env_degiskeni_ile_engellenir(tmp_path: Path) -> None:
    proje = _sahte_proje_kur(tmp_path, env_dosyasi_icerigi=None)
    sonuc = _pytest_calistir(proje, ekstra_env={"DATABASE_URL": _SAHTE_CANLI_URL})

    assert sonuc.returncode == 3, (
        f"Beklenen exit code 3 (guard engeli), gelen: {sonuc.returncode}\n"
        f"stdout:\n{sonuc.stdout}\nstderr:\n{sonuc.stderr}"
    )
    assert "canlı Supabase" in sonuc.stdout + sonuc.stderr
    assert "test_korumadan_gecerse_buraya_ulasilmamali" not in sonuc.stdout


def test_env_dosyasi_kontrolden_sonra_yuklenince_bile_engellenir(
    tmp_path: Path,
) -> None:
    """2026-09-08 bug'ının BİREBİR reprodüksiyonu: `DATABASE_URL` kabuk
    ortamında YOK, yalnız `.env`'de var. Eski (buggy) `conftest.py` bunu
    KAÇIRIRDI (os.environ'a `worker.db` import edilmeden BAKARDI);
    düzeltilmiş sürüm `worker.db`'yi kontrolden ÖNCE import ettiği için
    (bu da `load_dotenv()`'i tetikler) yakalamalı."""
    proje = _sahte_proje_kur(
        tmp_path, env_dosyasi_icerigi=f"DATABASE_URL={_SAHTE_CANLI_URL}\n"
    )
    sonuc = _pytest_calistir(proje, ekstra_env={})

    assert sonuc.returncode == 3, (
        f"Beklenen exit code 3 (guard engeli — .env'den yüklenen değer "
        f"bile yakalanmalı), gelen: {sonuc.returncode}\n"
        f"stdout:\n{sonuc.stdout}\nstderr:\n{sonuc.stderr}"
    )
    assert "canlı Supabase" in sonuc.stdout + sonuc.stderr
    assert "test_korumadan_gecerse_buraya_ulasilmamali" not in sonuc.stdout


def test_allow_destructive_tests_kacis_kapisi_calisir(tmp_path: Path) -> None:
    """Kaçış kapısı hâlâ çalışıyor mu: aynı sahte-canlı URL +
    `ALLOW_DESTRUCTIVE_TESTS=true` → guard devre dışı kalmalı, toplama
    DEVAM etmeli. Bunu, bilerek başarısız olan sahte testin GERÇEKTEN
    çalıştığını (yani guard'ın hiç tetiklenmediğini) görerek kanıtlıyoruz
    — yalnız "returncode != 3" yetersiz olurdu (pytest'in kendi hata
    kodları da 3'ten farklı olabilir)."""
    proje = _sahte_proje_kur(tmp_path, env_dosyasi_icerigi=None)
    sonuc = _pytest_calistir(
        proje,
        ekstra_env={
            "DATABASE_URL": _SAHTE_CANLI_URL,
            "ALLOW_DESTRUCTIVE_TESTS": "true",
        },
    )

    assert sonuc.returncode != 3, (
        f"Kaçış kapısı çalışmıyor gibi görünüyor — guard yine devreye "
        f"girmiş (returncode=3).\nstdout:\n{sonuc.stdout}\nstderr:\n{sonuc.stderr}"
    )
    # Guard'ın atlandığının ASIL kanıtı: sahte test'in KENDİSİ çalışıp
    # KENDİ (kasıtlı) assertion'ıyla düşmüş olması.
    assert "test_korumadan_gecerse_buraya_ulasilmamali" in sonuc.stdout
    assert "1 failed" in sonuc.stdout
