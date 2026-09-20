# GitHub Copilot — Proje Talimatları (EPP)

Bu depoda kod üretirken aşağıdaki kurallara ve `dokumanlar/` klasöründeki
Markdown dokümanlara UYULMALIDIR. Çelişki olursa `dokumanlar/` esastır.

## 📚 Referans Dokümanlar (ÖNCE OKU)
**Tek giriş noktası:** `dokumanlar/10_TEKNIK_MASTER_DOKUMAN.md` — Faz 0'dan
bugüne mimari, veri modeli, parser, pipeline, KPI, güvenlik, CI/CD ve
kronolojik geçmişin gerçek koda/git'e karşı doğrulanmış tek dosyası.
Diğer `dokumanlar/` dosyaları bunun altında, değişmeyen sözleşmeleri tutar
(bkz. `dokumanlar/00_INDEX.md` tam dizin). `dokumanlar/`'a yazarken: güncel
sayı/durum YALNIZ `09_PROJE_DURUMU.md`/`10_TEKNIK_MASTER_DOKUMAN.md`'ye
yazılır; başka bir dosyaya (HISTORICAL/olay günlüğü) bir rakam/durum
yazılıyorsa MUTLAKA tarihe çapalanmalıdır ("2026-09-03 itibarıyla +%6,9"
gibi, yalnız "+%6,9" değil) — bkz. master dokümandaki "Doküman Yönetim
Kuralı" bölümü.
- `dokumanlar/01_kavramsal_tasarim.md` — proje amacı, mimari, fazlar
- `dokumanlar/02_srs_ozet.md` — KRİTİK P0 kuralları (asla ihlal etme)
- `dokumanlar/03_veri_modeli.md` — tablolar, DDL, ilişkiler
- `dokumanlar/04_kpi_sozlesmeleri.md` — KPI formülleri + kenar durumlar
- `dokumanlar/05_kaynak_dosya_sozlesmesi.md` — parser kolon haritası
- `dokumanlar/06_adr_dashboard_teknoloji.md` — ADR: Streamlit (Faz 2), Next.js ertelendi
- `dokumanlar/09_PROJE_DURUMU.md` — GÜNCEL, canlı DB'ye karşı doğrulanmış durum

## Proje Özeti
EPP: EPDK aylık+yıllık sektör raporu verilerini (Excel/Word) PostgreSQL'e
yükleyen, Open-Meteo ile zenginleştiren, KPI üreten açık kaynak platform.

## Teknoloji (yalnız açık kaynak)
- Sunum: **Streamlit** (`app/dashboard.py`, Faz 2) — Next.js+TS "Son Faz"'a
  ertelendi, henüz yazılmadı; `app/` altında Next.js kodu YOK.
- Worker: Python 3.12, **framework-agnostik** (`worker/`) — FastAPI
  KULLANILMIYOR (ADR-7).
- DB: PostgreSQL (Supabase, `supabase/migrations/`)
- Parser: pandas, openpyxl, python-docx ; Hava: Open-Meteo ; Test: pytest

## KESİN MİMARİ KURALLARI (ASLA İHLAL ETME)
1. **P0-2 fact_tuketim grain:** doğal anahtar (il_kodu, tarih_id, grup_id, baglanti).
   baglanti ∈ {iletim, dagitim} NOT NULL. İKİ AYRI kısıt:
   - Aktif index (batch_id YOK): UNIQUE ... (il_kodu,tarih_id,grup_id,baglanti) WHERE is_active
   - Batch tekilliği (batch_id VAR): UNIQUE (...,baglanti,ingestion_batch_id)
   Aktif index'e ASLA batch_id ekleme.
2. **P0-3 source_asset:** source_kind file|api; api'de file yok (source_uri+request_hash).
3. **P0-5 ingestion_batch:** UNIQUE(source_asset_id, parser_version, schema_version)
   — **2026-09-17'de düzeltildi:** `source_asset` dedup'lanmadığı için bu kısıt
   pratikte hiç tetiklenmiyordu; gerçek koruma her loader'ın kendi ön-kontrolünde
   (bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §14 madde 5). `status`'a 2026-09-18'de
   7. bir terminal durum eklendi: `mutabakat_reddedildi` (bkz. §6.1).
4. **P0-4 aktivasyon:** eski pasifleme = yeni aktifleme, aynı doğal-anahtar kapsamı, tek transaction.
5. **P0-6 KPI:** Faz 0 production = KPI-01..10,13,23,24. KPI-11/12 yalnız altyapı; β/γ Faz 3.
6. **OD-1/OD-2:** hdd_baz=18, cdd_baz=22 sistem_parametre'den. Hava normu 10y sabit, tüketim 5y rolling.
7. **il referansı:** il_kodu (plaka, dim_il.il_kodu'ya FK) — 'il_id' DEĞİL.

## Kodlama Standartları
- Python: Ruff (lint+format), mypy tip ipuçları.
- SQL: PostgreSQL; snake_case; Türkçe karaktersiz kolon.
- Parametreli sorgu (string birleştirme YASAK). Sırlar env'de.
- Commit: Conventional Commits (feat:, fix:, test:...).

## Veri Kalite (parser)
- Negatif değer → REDDET; bilinmeyen il/grup/kaynak → KARANTİNA + uyarı.
- İl toplamı ↔ 'TÜRKİYE' ±%0,5. Boş hücre = NULL (0 değil).

## Golden Dataset
worker/tests/golden/ — input CSV + expected/kpi_expected.json.
Testler ±%0,5 tolerans. P0-2 testi: Sanayi iletim(150000)+dağıtım(90000)=6 satır, duplicate DEĞİL.

## Dizin
app/ (web) · worker/ (parsers,kpi,jobs,tests) · db/ (schema.sql) ·
migrations/ · data/ (git'e girmez) · dokumanlar/ (md — kod DEĞİL)

## Yanıt Dili
Açıklamalar Türkçe; kod/kolon adları İngilizce snake_case.

## Çalışma Akışı — Prompt/Kapanış Dosyaları (2026-09-18'den beri kalıcı kural)
- **Görev girişi:** `Claude outputs/PROMPT_*.md` — kullanıcı bir görevi bu
  dosyaya yazıp "oku ve uygula" der.
- **Kapanış çıktısı:** her turun kapanış raporu SOHBETE DEĞİL, DOSYAYA
  yazılır: `Claude outputs/kapanis_<YYYY-MM-DD>_<kisa_konu>.md`. Sohbete
  yalnız 3-5 satırlık bir özet + dosya yolu yazılır — uzun rapor asla
  doğrudan sohbete basılmaz.
- `Claude outputs/` `.gitignore`'dadır — bu dosyalar (hem prompt hem
  kapanış) repoya HİÇBİR ZAMAN commit edilmez, yalnız iki oturum arasında
  elle/cloud-okumayla taşınır.
- Gerekçe: raporların elle iki oturum arasında taşınması yavaş ve kota
  israfıydı; cloud oturumu repoyu doğrudan okuyabiliyor.

## Otomatik Kontroller — "Ateşlediği Gösterilmeden Tamamlanmaz" Kuralı (2026-09-20'den beri kalıcı kural)
Yeni bir otomatik kontrol (workflow adımı, pre-commit hook, DB kısıtı,
doğrulama script'i, kapı fonksiyonu) eklendiğinde, **kasıtlı bozuk bir
örnekle gerçekten ateşlediği gösterilmeden** tamamlanmış sayılmaz.
Gerekçe: bu projede aynı arıza tekrar tekrar çıktı — `scheduled-
backup.yml`'in pg_dump sürüm uyuşmazlığı, `UNIQUE(source_asset_id,
parser_version,schema_version)`'ın hiç tetiklenememesi, `sqlfluff`
pre-commit hook'unun `files` deseni eşleşmediği için hiç ateşlememesi,
`.pre-commit-config.yaml`'ın hiçbir yerde çağrılmaması,
`validate_rls_static.py`'nin 3 dosyalık donmuş listesi VE test paketinin
kendisinin durum sızdırması (aşağıdaki madde) — hiçbiri "bu kontrol
gerçekten çalışıyor mu?" diye SORULDUĞU için bulunmadı, hepsi tesadüfen
(bkz. `Claude outputs/kapanis_2026-09-20_kontrol_denetimi.md`,
`Claude outputs/kapanis_2026-09-20_test_izolasyon.md`, tam envanterler).

## Test Paketi İdempotentliği (2026-09-20'den beri kalıcı kural)
Test paketi idempotent olmalıdır: aynı veritabanı üzerinde arka arkaya
iki kez çalıştırıldığında aynı sonucu vermelidir. Bir test yazdığı
veriyi temizlemekle yükümlüdür. "Fresh disposable'da yeşil" TEK BAŞINA
yeterli kanıt değildir — yeşilliğin koşullara değil doğruluğa
dayandığını göstermez. Gerekçe: `job_worker` testlerinin commit edip
temizlememesi, `test_is_kuyruk_atomik_sahiplenme`'nin önceki koşudan
kalma `job_id` ile sessizce yanlış geçmesine/kalmasına yol açtı —
**kendisi durum sızdıran bir paket, üretim kodundaki durum sızıntılarını
(örn. batch 4-8'in 19 gün `running`'de kalması) yapısal olarak
GÖREMEZ** (bkz. `Claude outputs/kapanis_2026-09-20_test_izolasyon.md`).
CI'ya paketi aynı DB'de iki kez çalıştıran bir doğrulama adımı ÖNERİLDİ
(maliyet/değer tartışması `10_TEKNIK_MASTER_DOKUMAN.md` §16.3'te),
henüz UYGULANMADI.
