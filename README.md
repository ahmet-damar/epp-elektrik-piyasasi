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

## Kalite Kapıları (SRS §13.9)
G-1 birim+golden · G-2 kapsam≥85% · G-3 entegrasyon · G-4 güvenlik
G-5 RLS/lisans · G-6 model MAPE · G-7 lint+tip

## v1.5 Uyumu
- CI'daki golden testi P0-2'yi doğrular (Sanayi iletim+dağıtım ayrı satır).
- scheduled-refresh, hava verisini source_kind='api' olarak yazar (P0-3).
- deploy tamamen açık kaynak/self-host (ADR-5); GHCR ücretsiz.
