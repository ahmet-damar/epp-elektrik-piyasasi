# EPP Ek D — CI/CD ve pre-commit Yapılandırması (v1.0)

Bağlı belge: EPP_SRS_Teknik-Gereksinim_v1.5 (Bölüm 13)
Tüm araçlar ücretsiz ve açık kaynak. Geliştirme: VS Code + GitHub.

## Dosya Yerleşimi (repo köküne)
```
epp/
├─ .pre-commit-config.yaml     # commit-öncesi yerel kontroller
├─ .commitlintrc.yaml          # Conventional Commits
├─ .github/
│  ├─ CODEOWNERS               # zorunlu inceleme
│  ├─ dependabot.yml           # bağımlılık güncelleme
│  └─ workflows/
│     ├─ ci.yml                # test+lint+kalite kapıları (G-1..G-7)
│     ├─ security.yml          # gitleaks, audit, Trivy, lisans
│     ├─ deploy.yml            # imaj build + GHCR + self-host (SSH)
│     └─ scheduled-refresh.yml # Open-Meteo hava verisi (API)
├─ web/                        # Next.js/TS
├─ worker/                     # Python/FastAPI (parser, ml, jobs)
├─ db/schema.sql               # source_asset, ingestion_batch, fact_*
└─ migrations/                 # 0001_*.sql ...
```

## Yerel Kurulum
```bash
pipx install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit run --all-files
```

## Panel Nasıl Çalıştırılır + Giriş (Faz B, 2026-09-05)
```bash
streamlit run app/dashboard.py
```
`.env`'de `DATABASE_URL_DASHBOARD` yapılandırılmışsa (canlı Supabase
kurulumunda böyledir) panel **e-posta/şifre girişi ister** — Supabase
Auth hesabınla giriş yaparsın, rolün (`app_metadata.role` — `viewer`/
`data_operator`/`admin`) veriye erişimini otomatik belirler (bkz.
`dokumanlar/06_adr_dashboard_teknoloji.md`, "Faz B — TAMAMLANDI"
bölümü). `DATABASE_URL_DASHBOARD` HİÇ yapılandırılmamışsa (yerel/offline
geliştirme) giriş İSTENMEZ, panel yerel dosya verisiyle (ya da varsa
`DATABASE_URL`) çalışır.

**Yeni kullanıcı eklemek** bir kod değişikliği DEĞİL, Supabase Admin
API'sinden tek bir çağrı — adımlar `dokumanlar/06_adr_dashboard_
teknoloji.md`'de yazılı.

## GitHub Ayarları
- Branch protection (main): PR + "Quality Gate" required check + signed commits
- Code security: Secret scanning + Push protection, Dependabot, Trivy (fs+deps)
  (CodeQL/code-scanning devre dışı — GitHub Advanced Security Free plan private repo'da yok)

## Gerekli Secrets
| Secret | Kullanım |
|--------|----------|
| PROD_DATABASE_URL | migration + zamanlı işler |
| DEPLOY_HOST/USER/SSH_KEY | self-host SSH deploy |
| PROD_URL | smoke testi |
| COOLIFY_WEBHOOK_URL | (opsiyonel) Coolify deploy |

## CI'da Supabase Rol Bootstrap (2026-09-02)
Gerçek Supabase Postgres, `supabase start` (Supabase CLI) tarafından proje
migration'ları çalışmadan ÖNCE otomatik kurulan üç yönetilen rolle gelir:
`anon`, `authenticated`, `service_role`. CI'ın `postgres:16` servisi bunlara
sahip DEĞİL — bu üç role GRANT/REVOKE yapan migration'lar (0003, 0010,
0011, 0013) daha önce CI'ın apply listesinden "role does not exist"
gerekçesiyle çıkarılmıştı, yani hiç doğrulanmıyorlardı. `ci.yml`'in
`integration` job'ı artık migration'lardan ÖNCE
`supabase/ci-only/01_roles_bootstrap.sql`'i çalıştırıyor (roller +
`GRANT USAGE ON SCHEMA public` — `supabase start`'ın kendi başlangıç
durumunu taklit eder), ve TÜM migration'lar (0001-0013) sırayla uygulanıp
`worker/validate_rls_static.py` (statik metin taraması) + `worker/
validate_role_access.py` (gerçek `SET ROLE`+sorgu ile GRANT/RLS
davranışını canlı test eder — `anon` tablo seviyesinde reddedilmeli,
`viewer` JWT claim'siz 0 satır/claim'li satır görmeli) ile doğrulanıyor.
`supabase/ci-only/` klasörü BİLİNÇLİ OLARAK `supabase/migrations/` dışında
— `deploy.yml`'in migration glob'u bu dosyaları asla gerçek Supabase'e
uygulamaz (orada zaten var).

## ⚠️ Canlı Supabase'e Karşı Test Çalıştırma Kuralı (2026-09-03)
**Tam pytest paketi (`py -m pytest` argümansız/`-v` ile TÜMÜ) ASLA canlı
Supabase'e karşı çalıştırılmaz.** Yalnız CI'ın izole, her çalıştırmada
sıfırdan kurulan `postgres:16` konteynerinde (`integration` job) tam paket
çalıştırılır. Canlı `DATABASE_URL`'e karşı yerel doğrulama gerekiyorsa
YALNIZ hedefli bir alt küme: `py -m pytest -k <hedef>` (örn.
`-k "kpi_25 or kpi_27"`). Sebep: `worker/tests/test_job_worker_integration.py`,
`worker/job_worker.py`'nin async polling yolunu egzersiz eder ve bu yol
KENDİ commit'lerini yapar — standart `conn` fixture'ının rollback tabanlı
test izolasyonunu bypass eder. 2026-09-02'de tam paketin canlıya karşı
çalıştırılması, sentinel `tarih_id=209912` (yıl 2099) için 4 fact
tablosunda + `ingestion_batch` + `source_asset` + `dim_tarih`'te kalıcı
test verisi bırakmıştı — üç turda tespit edilip temizlendi (detay:
`dokumanlar/06_canli_veri_operasyon_gunlugu.md`, 2026-09-03 girdisi).

## Kalite Kapıları (SRS §13.9)
G-1 birim+golden · G-2 kapsam≥85% · G-3 entegrasyon · G-4 güvenlik
G-5 RLS/lisans · G-6 model MAPE · G-7 lint+tip

## v1.5 Uyumu
- CI'daki golden testi P0-2'yi doğrular (Sanayi iletim+dağıtım ayrı satır).
- scheduled-refresh, hava verisini source_kind='api' olarak yazar (P0-3).
- deploy tamamen açık kaynak/self-host (ADR-5); GHCR ücretsiz.
