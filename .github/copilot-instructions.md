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
3. **P0-5 ingestion_batch:** UNIQUE(source_asset_id, parser_version, schema_version).
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
