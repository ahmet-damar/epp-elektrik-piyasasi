"""EPP — canlı Supabase'in `public` şemasındaki VERİYİ (DDL değil) yedekler.

Neden yalnız veri (--data-only), şema değil: `public` şemasının DDL'i
(tablolar/RLS/policy/fonksiyon) zaten `supabase/migrations/`'da tam olarak
version-control altında — sıfırdan bir Supabase projesine migration'ları
sırayla uygulayarak birebir yeniden üretilebilir (`ci.yml`'in `integration`
job'ı bunu her koşuda zaten kanıtlıyor). Gerçekten TEK KOPYASI olan ve
kazayla kaybı saatlerce/tekrar üretilemez maliyete yol açacak şey VERİDİR:
120 ay elle transkribe edilmiş EPDK Word/Excel verisi ve Open-Meteo'nun
dokümante edilmemiş saatlik kotası yüzünden ~3 saat süren bir hava
backfill'i (bkz. dokumanlar/10_TEKNIK_MASTER_DOKUMAN.md §10, §11).

Bu yüzden: DDL'i migration'lardan yeniden kur, VERİYİ bu script'in ürettiği
dump'tan `pg_restore` ile geri yükle. Tarifi (adım adım, GERÇEKTEN denenmiş
restore dahil): dokumanlar/11_yedekleme_runbook.md.

Kullanım (pg_dump PATH'te olmalı — bu makinede yoksa WSL/Docker içinde
çalıştır, bkz. runbook §"Ortam notu"):
    py worker/scripts/backup.py
    py worker/scripts/backup.py --out-dir /path/to/yedekler

Çıktı: `epp_data_<UTC-zaman-damgası>.dump` (pg_dump custom format, -Fc —
sıkıştırılmış, pg_restore ile TABLO BAZINDA seçici geri yükleme de mümkün).

**Hariç tutulan 6 tablo (2026-09-07, gerçek restore denemesiyle
bulundu):** `dim_il`/`dim_kaynak`/`dim_lisans`/`dim_tuketici_grubu`/
`kpi_esik`/`sistem_parametre` — bunlar `supabase/migrations/`'daki seed
migration'ları (20260819_0004, 20260905_0001) tarafından ZATEN
oluşturulur; data-only dump'a dahil edilirlerse restore sırasında
"duplicate key" hatası verirler (zararsız ama gürültülü — pg_restore
bunları "ignored" sayıp devam eder). `dim_tarih` DAHİL tutulur — o statik
bir seed DEĞİL, ingestion pipeline'ı her ay işledikçe büyür.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # .env'den oku (worker/db.py'nin geri kalanı da böyle davranıyor değil
    # ama backup script'i CI'da hiç çalışmadığı için burada basit tutuldu)
    env_dosya = Path(__file__).resolve().parents[2] / ".env"
    if env_dosya.exists():
        for satir in env_dosya.read_text(encoding="utf-8").splitlines():
            if satir.startswith("DATABASE_URL="):
                return satir.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL ne ortam değişkeni olarak ne de .env'de bulundu.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[2] / "yedekler"),
        help="Dump dosyasının yazılacağı klasör (varsayılan: repo_kökü/yedekler, git'e girmez)",
    )
    args = ap.parse_args()

    database_url = _database_url()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    zaman_damgasi = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    hedef = out_dir / f"epp_data_{zaman_damgasi}.dump"

    # supabase/migrations/'daki seed migration'ları (20260819_0004,
    # 20260905_0001) tarafından zaten oluşturulan statik referans/config
    # tabloları — data-only dump'a dahil edilirlerse restore'da zararsız
    # ama gürültülü "duplicate key" hatası verirler (bkz. modül docstring'i).
    _SEED_TABLOLARI = (
        "dim_il",
        "dim_kaynak",
        "dim_lisans",
        "dim_tuketici_grubu",
        "kpi_esik",
        "sistem_parametre",
    )

    komut = [
        "pg_dump",
        database_url,
        "--schema=public",
        "--data-only",
        "--no-owner",
        "--disable-triggers",
        "--format=custom",
        f"--file={hedef}",
        "--verbose",
    ]
    for tablo in _SEED_TABLOLARI:
        komut.append(f"--exclude-table=public.{tablo}")

    print(
        f">> {' '.join(komut[:2])} ... (URL maskelendi) --schema=public --data-only ..."
    )
    sonuc = subprocess.run(komut, capture_output=True, text=True, check=False)
    if sonuc.returncode != 0:
        print(sonuc.stderr, file=sys.stderr)
        return sonuc.returncode

    boyut_mb = hedef.stat().st_size / (1024 * 1024)
    print(f"OK: {hedef} ({boyut_mb:.2f} MB)")
    print(f'İçerik listesi için: pg_restore --list "{hedef}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
