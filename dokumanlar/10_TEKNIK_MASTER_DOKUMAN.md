# EPP — Teknik Master Doküman

**Bu doküman**, Faz 0'dan bugüne EPP (EPDK Elektrik Piyasası Platformu)
projesinde yapılan HER ŞEYİN tek bir yerde, gerçek koda/migration'a/git
geçmişine karşı doğrulanmış hâlidir. Amaç: hem mevcut durumun tek
referansı hem de projeye sonradan bakacak biri (ya da gelecekteki bir
Claude oturumu) için tam bağlam kaynağı.

**Yöntem notu:** Bu doküman `dokumanlar/`'daki diğer notların kopyası
DEĞİLDİR — her iddia gerçek kaynağa (git log, migration dosyası, .py
kaynak kodu, canlı Supabase sorgusu) karşı yeniden doğrulandı. Bir
çelişki bulunduğunda KOD/GİT esas alındı, çelişki ayrıca not düşüldü
(bkz. §14 Çelişki Kayıtları).

## Sürüm Geçmişi

| Sürüm | Tarih | Değişiklik | Doğrulama kapsamı |
|---|---|---|---|
| v1.0 | 2026-09-08 | İlk yazım | 141 commit (2026-08-18→09-07), 25 migration + 2 ci-only, 11 worker/*.py + 10 yıllık word_20XX.py + 5 diğer script, 25 test dosyası (248 `def test_`, 230 pytest ID non-integration / 276 tüm dosyalar), 4 GitHub Actions workflow, 11 mevcut `dokumanlar/` dosyası, canlı Supabase (RLS/GRANT) doğrudan sorgulandı |
| v1.1 | 2026-09-08 | §9.4/Ek A test sayısı düzeltmesi | v1.0'ın "230 pytest ID non-integration" rakamı YANLIŞTI — temiz bir kabukta (`env -i`, `.env` erişilemez) doğrudan doğrulandı: 19 unit/regresyon dosyası TEK BAŞINA **227** ID veriyor (`skipif` toplamayı değil çalıştırmayı engelliyor, bu iki kavramın karışması hataya sebep olmuştu). 230, bu oturumun WSL koşusuna ÖZGÜ bir rakam (227 yerel + 3 gerçek `test_auth_integration.py` çağrısı) — genel/ortam-bağımsız bir sabit DEĞİL |

---

## İçindekiler
1. [Proje Özeti ve Amacı](#1-proje-özeti-ve-amacı)
2. [Mimari](#2-mimari)
3. [Veri Modeli](#3-veri-modeli)
4. [EPDK Kaynak Dosya Sözleşmesi](#4-epdk-kaynak-dosya-sözleşmesi)
5. [Parser Mimarisi](#5-parser-mimarisi)
6. [Ingestion Pipeline](#6-ingestion-pipeline)
7. [KPI Sözleşmeleri](#7-kpi-sözleşmeleri)
8. [Güvenlik](#8-güvenlik)
9. [CI/CD](#9-cicd)
10. [Faz Bazlı İlerleme Geçmişi](#10-faz-bazlı-i̇lerleme-geçmişi)
11. [Bilinen Sorunlar / Açık Maddeler](#11-bilinen-sorunlar--açık-maddeler)
12. [Nasıl Çalıştırılır / Geliştirme Ortamı](#12-nasıl-çalıştırılır--geliştirme-ortamı)
13. [Sözlük / Kısaltmalar](#13-sözlük--kısaltmalar)
14. [Çelişki Kayıtları](#14-çelişki-kayıtları)
- [Ek A: Kaynak Dosya Envanteri](#ek-a-kaynak-dosya-envanteri)

---

## 1. Proje Özeti ve Amacı

### 1.1 Ne için var, kim kullanacak
EPP, EPDK'nın (Enerji Piyasası Düzenleme Kurumu) yayınladığı **Elektrik
Piyasası Sektör Raporu** (aylık Excel/Word ekleri + yıllık raporlar)
verilerini yükleyip, Open-Meteo hava verisiyle zenginleştirip, KPI'lar
üretip bir dashboard'da gösteren **açık kaynak** bir platformdur.
Kullanıcı kitlesi: veri ekibi/paydaşlar (iç panel, `viewer` rolü),
veri girişi yapan operatörler (`data_operator` rolü — şu an yalnız
altyapı var, UI yok, bkz. §11), yöneticiler (`admin`).

### 1.2 Dört Temel Yetenek
(Kaynak: `dokumanlar/01_kavramsal_tasarim.md` §2)
1. **Veri Alımı:** Dosya yükleme (Excel/Word) + API çekimi (Open-Meteo;
   ileride EPİAŞ, Faz 5)
2. **Depolama & Modelleme:** PostgreSQL yıldız şema, batch bazlı sürümleme
3. **Analitik:** KPI'lar, karşılaştırma, korelasyon, dashboard
4. **Tahminleme:** (Faz 4, henüz başlamadı) hava + takvim ile zaman
   serisi tahmini

### 1.3 Nihai Vizyon ve Faz Haritası
| Faz | İçerik | Durum |
|---|---|---|
| Faz 0 | İskelet: şema, RLS, golden test, CI/CD | ✅ TAMAMLANDI |
| Faz 1 | Asenkron worker (job_status kuyruğu) | ✅ TAMAMLANDI |
| Faz 2 | Dashboard (Streamlit), gerçek DB sorguları | ✅ TAMAMLANDI |
| Faz 3 | Hava normalizasyonu (KPI-11/12/23/24 production) | ✅ TAMAMLANDI |
| Faz B | Çok-kullanıcılı Supabase Auth girişi | ✅ TAMAMLANDI (2026-09-05) |
| — | 2016-2025 tarihsel Word genişlemesi (T11/T10/T4) | ✅ TAMAMLANDI |
| — | `fact_tuketim_ulke_geneli` (Sanayi dahil ülke geneli) | ✅ TAMAMLANDI (2026-09-08) |
| Faz 4 | Tahminleme (ML, zaman serisi) | ⛔ Başlamadı |
| Faz 5 | EPİAŞ entegrasyonu | ⛔ Başlamadı |
| Faz 6 | TEİAŞ projeksiyon | ⛔ Başlamadı |
| "Son Faz" | Next.js+TS'e geçiş + LinkedIn yayını | ⛔ Ertelendi (ADR-7) |

---

## 2. Mimari

### 2.1 Üç Katman
(Kaynak: `dokumanlar/01_kavramsal_tasarim.md` §3, `dokumanlar/06_adr_dashboard_teknoloji.md`)
```
SUNUM  : Streamlit (app/dashboard.py)  — Next.js+TS "Son Faz"'a ertelendi (ADR-7)
İŞLEM  : Python (worker/)              — parser, ingest, pipeline, kpi, analytics, jobs
VERİ   : PostgreSQL (Supabase)         — yıldız şema + batch sürümleme + RLS
```
Doküman "İŞLEM" katmanı için orijinalde FastAPI öngörüyordu
(`dokumanlar/01_kavramsal_tasarim.md` §6); **gerçekte hiçbir FastAPI
kodu yok** — `worker/` doğrudan Streamlit'ten (`app/dashboard.py`) ya da
CLI script'lerinden (`worker/scripts/*.py`, `worker/job_worker.py`)
çağrılan düz Python modülleridir. Bu bir çelişki değil, ADR-7'nin
"framework-agnostik worker katmanı" kararının doğal sonucu — bkz. §2.3.

### 2.2 ADR Kayıtları
Proje 4 mimari karar kaydı (ADR) tutuyor — hepsi `dokumanlar/`
içinde belgelenmiş, ADR-1 ila ADR-4 numaraları hiç kullanılmamış
(muhtemelen SRS'in kendi Ek'lerindeki farklı bir numaralandırmaya
karşılık geliyor, bu repoda ayrı dosya olarak yok):

| ADR | Konu | Karar | Kaynak |
|---|---|---|---|
| ADR-5 | Deploy stratejisi | Tescilli PaaS yok; GHCR (ücretsiz) + Docker Compose self-host (SSH) | `.github/workflows/deploy.yml` başlığı |
| ADR-6 | Bileşen lisansları | Uygulama bileşenleri OSI açık kaynak; GitHub/Actions/GHCR yönetilen servis istisnası | `01_kavramsal_tasarim.md` §6 |
| ADR-7 | Sunum katmanı | Streamlit kalır (Faz 2); Next.js+TS'e geçiş "Son Faz"a (LinkedIn yayını) ertelendi, İPTAL değil | `06_adr_dashboard_teknoloji.md` (kendi dosyası) |
| ADR-8 | RLS tasarım alternatifi | `authenticated`+`current_app_role()`'e TAM geçiş (fiziksel roller kaldırılıp) — **denendi (2026-08-19), TAMAMLANMADAN terk edildi (2026-08-31)**: mevcut `viewer/data_operator/admin` + `current_app_role()` hibrit modeli zaten yeterliydi | `01_kavramsal_tasarim.md` §6 (satır 55-70) |

**ADR-8 numaralandırma tuzağı (dokümanın kendi notu):** ADR-8'in
planladığı migration adları (`20260819_0004_fix_rls_policies.sql`,
`20260819_0005_harden_service_role_grants.sql`) hiç commit'lenmedi;
bu numaralar sonradan TAMAMEN FARKLI, gerçek migration'lar için yeniden
kullanıldı (`seed_dimensions.sql` / `uretim_mwh_nullable.sql` — bkz.
§3.2). Git log'da eski taslak adlarını arayan biri karışmasın diye not.

### 2.3 Framework-Agnostik İlke
`worker/` paketi HİÇBİR Streamlit/FastAPI importu içermez —
`app/dashboard.py` `worker/*.py` fonksiyonlarını doğrudan çağırır,
`worker/auth.py`'nin kendi modül notu bunu açıkça ADR-7'nin ilkesi
olarak tanımlar: "ileride Next.js/FastAPI'ye geçilirse bu modül
DEĞİŞMEDEN kullanılabilir." Bu ilke tutarlı uygulanmış (kod taramasıyla
doğrulandı — `worker/` içinde `import streamlit` YOK).

### 2.4 Uçtan Uca Veri Akışı
(Kaynak: `dokumanlar/01_kavramsal_tasarim.md` §4, `worker/pipeline.py`,
`worker/ingest.py`)
```
1. Kullanıcı/script EPDK dosyası okur → SHA-256 hash (source_asset.file_hash)
2. source_asset (kind='file'|'api') + ingestion_batch (status='queued') oluşur
3. Worker batch'i ATOMİK sahiplenir (ingest.batch_sahiplen, advisory lock)
   → parse (worker/parser.py veya worker/scripts/word_*.py)
   → doğrulama (worker/kpi.py:dogrula_*) → kabul edilenler fact tablosuna
     is_active=FALSE olarak yazılır
4. otomatik_onaya_uygun() kontrolü (mutabakat + red/karantina=0):
   - TUTUYORSA → pipeline.batch_onayla() OTOMATİK çağrılır (job_worker.py)
   - TUTMUYORSA → batch 'running' kalır, ELLE onay beklenir
     (worker/scripts/onayla.py --batch-id N)
5. Aktivasyon (P0-4): TEK transaction'da eski aktif sürüm is_active=false,
   yeni batch is_active=true — advisory lock ile eşzamanlılık korunur
6. Dashboard (app/dashboard.py) her zaman yalnız is_active=true satırları
   gösterir (fact_hava_aylik hariç — UPSERT modeli, bkz. §3.4)
```
Bu akış Faz 0'dan beri DEĞİŞMEDİ; Faz 1 yalnız 3-4. adımı asenkron hâle
getirdi (job_status kuyruğu, bkz. §6.5).

---

## 3. Veri Modeli

Kaynak: `db/schema.sql` (Faz 0 referans şeması) + 25 migration dosyası
(kümülatif gerçek durum) + canlı Supabase'e karşı doğrudan sorgu.

### 3.1 Boyut (dim_*) Tabloları
| Tablo | Grain / PK | Not |
|---|---|---|
| `dim_tarih` | `tarih_id` (YYYYMM ya da YYYY00 yıllık) | `yil`, `ay`, `ceyrek`, `donem_tipi` |
| `dim_il` | `il_kodu` (1-81, plaka) | `lat`/`lon` migration 0008'de eklendi (hava için) |
| `dim_kaynak` | `kaynak_id` | üretim kaynak türü; `yenilenebilir_mi` bool; migration 0007 Motorin/Nafta ekledi |
| `dim_tuketici_grubu` | `grup_id` | Aydınlatma/Mesken/Sanayi/Tarımsal/Kamu ve Özel Hizmetler (kanonik 5) |
| `dim_lisans` | `lisans_id` | 'Lisansli'/'Lisanssiz' CHECK |

### 3.2 Fact Tabloları — Tam Envanter
Ortak desen (fact_hava_aylik ve fact_tuketim_ulke_geneli kısmi istisna,
aşağıya bkz.): `id BIGSERIAL PK`, doğal anahtar kolonları, değer
kolon(ları), `ingestion_batch_id FK`, `is_active BOOLEAN`, iki kısıt
(batch tekilliği + aktif partial unique index — P0-2/P0-4).

| Tablo | Doğal anahtar (grain) | Değer kolonları | Hangi P0/Karar'ın sonucu |
|---|---|---|---|
| **`fact_tuketim`** | `(il_kodu, tarih_id, grup_id, baglanti)` | `tuketim_mwh NUMERIC(16,3) CHECK >=0` | **P0-2 KRİTİK**: `baglanti ∈ {iletim,dagitim}` grain'in PARÇASI, NOT NULL — iletim/dağıtım BİRLEŞTİRİLMEZ |
| `fact_uretim` | `(il_kodu, tarih_id, kaynak_id, lisans_id)` | `kurulu_guc_mw NOT NULL`, `uretim_mwh NULLABLE (migration 0005)` | `uretim_mwh` aylık il×kaynak grain'inde kaynakta hiç yok — nullable yapıldı, sahte 0 YAZILMADI |
| `fact_abone` | `(il_kodu, tarih_id, grup_id)` | `abone_sayisi BIGINT CHECK >=0` | — |
| `fact_serbest_tuketici` | `(il_kodu, tarih_id, tur, grup_id)` | `tuketim_mwh`, `tuketici_sayisi` | migration 0006 grain'i düzeltti (`tur` gerçek T13 değerleri: 'Serbest Tuketici'/'ST Olma Hakki Bulunmayan Aboneler'/'ST Olma Hakkini Kullanmayan Aboneler' — 'Lisansli'/'Lisanssiz' YANLIŞ VARSAYIMDI) |
| `fact_hava_aylik` | `UNIQUE(il_kodu, tarih_id)` | `t_ort`,`hdd`,`cdd`,`radyasyon`,`ruzgar` | **FARKLI SÜRÜMLEME** — bkz. §3.4 |
| `fact_hava_aylik_log` | append-only | `old_data`/`new_data JSONB` | fact_hava_aylik'in her UPSERT'i burada JSONB snapshot bırakır |
| `fact_tuketim_ulke_geneli` | `(tarih_id, grup_id)` | `tuketim_mwh` | **il_kodu/baglanti YOK** — kaynağı T11'in Genel Toplam satırı, zaten il kırılımsız (2026-09-05, migration 20260905_0002) |

### 3.3 İşlem/Config Tabloları
| Tablo | Amaç |
|---|---|
| `source_asset` | Bir dosya/API çağrısının kimliği — `source_kind ∈ {file,api}` (P0-3): file→`file_name`+`file_hash` NOT NULL, api→`source_uri`+`request_hash` NOT NULL |
| `ingestion_batch` | Bir işleme denemesi — `status ∈ {queued,running,succeeded,failed,retrying,dead_letter}`, `UNIQUE(source_asset_id, parser_version, schema_version)` (P0-5: aynı dosya farklı parser sürümüyle YENİDEN işlenebilir) |
| `audit_log` | Append-only iz — INSERT/UPDATE her önemli olayda (`ingest_tamamlandi`, `batch_onaylandi`) JSONB payload ile; UPDATE/DELETE hiç kimseye GRANT edilmez |
| `job_status` | Faz 1 asenkron kuyruk — `status ∈ {queued,running,succeeded,failed,retrying,dead_letter}`, `attempt_count`, `heartbeat_at` (bayat-heartbeat kurtarma) |
| `veri_kapsam_disi` | "Kaynakta gerçekten yok" (parser hatası DEĞİL) kaydı — PK `(tarih_id, fact_tablosu, nitelik)`, `ingestion_batch`'ten BİLİNÇLİ BAĞIMSIZ (migration 0012, 2026-09-02) |
| `sistem_parametre` | Koda gömülmeyen config (HDD/CDD baz sıcaklıkları, hava/tüketim norm yılı — OD-1/OD-2) |
| `kpi_esik` | Dashboard'daki trafik-ışığı renk eşikleri (migration 20260905_0001) |

### 3.4 Sürümleme Modelleri — İKİ FARKLI Desen
1. **Batch + is_active** (fact_tuketim, fact_uretim, fact_abone,
   fact_serbest_tuketici, fact_tuketim_ulke_geneli): veri ÜZERİNE
   YAZILMAZ, her yeniden-işleme yeni bir batch/satır ekler, aktivasyon
   TEK transaction'da eskiyi pasifler yeniyi aktifler (P0-4).
2. **UPSERT** (yalnız `fact_hava_aylik`): batch-versiyonlama/is_active
   YOK — `worker/jobs/fetch_weather.py` doğrudan `UNIQUE(il_kodu,
   tarih_id)` üzerinden UPSERT eder, değişiklik geçmişi
   `fact_hava_aylik_log`'a JSONB olarak yazılır (migration
   20260819_0009). **Neden farklı:** hava verisi Open-Meteo'nun kendi
   geçmiş verisini GÜNCELLEYEBİLDİĞİ (reanalysis düzeltmesi) bir API
   kaynağı — EPDK'nın statik, bir kere yayınlanan raporlarından farklı
   bir doğa taşıyor, "eski sürüm sakla" burada anlamsız.

### 3.5 İlişki Özeti
Klasik yıldız şema: her `fact_*` tablosu `dim_tarih`+`dim_il`(+diğer
dim_*)'e FK ile bağlı; `fact_tuketim_ulke_geneli` istisna (yalnız
`dim_tarih`+`dim_tuketici_grubu`, il kırılımı yok — bkz. §3.2). Tüm
fact tabloları `ingestion_batch`'e FK; `ingestion_batch` → `source_asset`'e
FK. `audit_log`/`veri_kapsam_disi` bu zincirin DIŞINDA (append-only /
bilinçli bağımsız).

---

## 4. EPDK Kaynak Dosya Sözleşmesi

Kaynak: `dokumanlar/05_kaynak_dosya_sozlesmesi.md` (Ek F), gerçek
2016+ dosyalarla çapraz doğrulanmış.

### 4.1 Çapa (Anchor) Tabanlı Okuma İlkesi
Parser SABİT hücre/satır numarasına GÜVENMEZ (Word'ün "Tablo N.M"
alan-kodu numaralandırması boş render edilebiliyor, gerçek bulgu) —
değişmez METİN etiketlerini arar: tablo başlıkları ('Tablo 1', 'Tablo
7 - Faturalanan'...), sütun başlıkları ('İLLER', 'Kaynak Türü'...),
satır etiketleri ('TÜRKİYE', 'Genel Toplam'). Normalizasyon: trim +
BÜYÜK harf + Türkçe sadeleştirme (İ→I).

### 4.2 T1-T13 Tam Harita
| Tablo | İçerik | Hedef |
|---|---|---|
| T1 | Lisanslı kurulu güç (il×kaynak) | `fact_uretim` |
| T2/T3 | Lisanslı üretim (kaynak/il) | `fact_uretim` |
| T4/T5/T6 | Lisanssız kurulu güç/üretim | `fact_uretim` |
| T7 | Faturalanan tüketim (tür) | `fact_tuketim` |
| **T8** | **Faturalanan tüketim (il)** | **`fact_tuketim`** |
| T9/T10 | Tüketici sayısı | `fact_abone` |
| **T11** | **Tüketim (iletim/dağıtım!)** | **`fact_tuketim.baglanti`** (P0-2) |
| T12 | Tüketim (dağıtım şirketi) | **parse edilmiyor** — bkz. §4.3 |
| T13 | Serbest tüketici (il×tür×grup) | `fact_serbest_tuketici` (yalnız Excel yılları, bkz. §4.4) |

**Düzeltme notu (2026-09-08 taslak onayında istenen teyit):** Bu
dokümanın bir önceki taslağında "T12, T8 gibi atlanıyor" varsayımı
vardı — bu **YANLIŞTI**. Gerçek kaynak (`05_kaynak_dosya_sozlesmesi.md`
satır 20) T8'in **gerçekten parse edildiğini ve `fact_tuketim`'i
beslediğini** gösteriyor; bilinçli olarak parse EDİLMEYEN tablo yalnız
**T12**'dir (T11 ile redundant olduğu için — bkz. §4.3).

### 4.3 Bilinçli Parse Edilmeyen: T12
2026-08-30'da gerçek dosyayla doğrulandı: T12'nin grain'i doküman
başlığının ima ettiği "dağıtım bölgesi" değil, gerçek kolon adı 'Lisans
Unvanı' — **dağıtım şirketi** (21 şirket + ulusal "İLETİMDEN BAĞLI
TÜKETİCİLER (TÜRKİYE)" satırı, yalnız Sanayi). T12'nin Genel Toplam ve
iletim/Sanayi rakamları T7/T11 ile birebir eşleşiyor → **T11 ile
redundant, hiçbir yeni bilgi taşımıyor** — bu yüzden `worker/parser.py`'de
hiç implemente edilmedi. İleride dağıtım-şirketi-bazlı bir KPI
gerekirse, statik bir `dim_il → dagitim_sirketi` eşleme tablosuyla
T11'in il bazlı verisinden türetilebilir (bilgi kaybı yok).

### 4.4 Word (2016-2025) Kapsamı — 3 Bilinçli Dışlama Kararı
EPDK'nın 2023 öncesi aylık raporları **Word (.docx)** formatındaydı
(2026+ Excel/.xlsx); Word formatı Excel'deki bazı tabloları hiç
basmıyor. `dokumanlar/07_word_parser_kapsam.md`'de kayıtlı 3 karar:

| Karar | Kapsam dışı | Neden | Telafi |
|---|---|---|---|
| **Karar 1** | T13 → `fact_serbest_tuketici` (Word yıllarında) | Word kaynağında Serbest Tüketici tablosu hiç basılmıyor | `veri_kapsam_disi`'nde işaretli |
| **Karar 2** | Sanayi grubu → `fact_tuketim` (Word yıllarında) | T11'de Sanayi TEK birleşik sütun (iletim/dağıtım ayrımı YOK) — P0-2 grain'i kaynakta karşılanamıyor, UYDURULMADI | **2026-09-05'te kısmen telafi edildi**: `fact_tuketim_ulke_geneli` (il/baglanti kırılımı gerektirmeyen ayrı bir tablo, bkz. §3.2) Sanayi DAHİL tüm grupları T11'in Genel Toplam satırından okuyor |
| **Karar 3** | T1 (Lisanslı kurulu güç) → `fact_uretim` (Word yıllarında) | Word'de il×kaynak birleşik Lisanslı tablosu yok (yalnız T4/Lisanssız var) | `veri_kapsam_disi`'nde işaretli |

Bu 3 karar DEĞİŞMEDİ — `fact_tuketim_ulke_geneli` Karar 2'yi İPTAL
ETMEDİ, yalnız il kırılımı gerektirmeyen AYRI bir ihtiyacı (ülke geneli
Sanayi serisi) kapattı.

---

## 5. Parser Mimarisi

### 5.1 `worker/parser.py` — Excel (2026+), Kalıcı/Tek Parser
2026'dan itibaren EPDK raporları **.xlsx** formatında — `worker/parser.py`
bu formatın KALICI parser'ı (gelecekte yeni her ay için değişmeden
çalışması beklenir). `openpyxl` ile çapa-tabanlı okuma (§4.1), `il_kodu_bul`/
`grup_esle`/`kaynak_esle` gibi paylaşılan eşleme fonksiyonlarını (Word
parser'ları da bunları import edip yeniden kullanır) ve
`epdk_aylik_isle()` (tam batch orkestrasyonu: T1-T13 sırayla okuma +
doğrulama + yükleme) barındırır.

### 5.2 Word (2016-2025) — `word_ortak.py` + 10 Ayrı Yıllık Tarif
`worker/scripts/word_ortak.py`, TÜM yılların ORTAK, gerçekten
yıl-bağımsız olan kısmını taşır (`gez()`: body'yi orijinal sırada
gezer — python-docx'in resmi `document.tables` API'si bu sırayı
VERMEZ, gerçek bulgu; `basliklari_topla()`: her tablonun önceki dolu
paragrafını bulur; `tek_aday_bul()`: metin aramasıyla TAM 1 aday
zorunlu kılar, birden fazla/hiç aday ValueError; `hedef_donem_kolonu_bul()`:
çoklu-dönem karşılaştırma tablolarında hedef sütunu metinle bulur;
`t4_tablosunu_bul()`, `grup_kolonlarini_coz()`,
`genel_toplam_satirini_oku()` — bkz. §5.4).

**Neden 10 AYRI dosya (`word_2016.py`...`word_2025.py`), tek ortak
parser DEĞİL:** Her yılın EPDK şablonu gerçek, önemli formatsal
sürprizler taşıyor — sütun düzeni, tablo numaralandırması, taksonomi
etiketleri yıldan yıla değişiyor. Bu TEK SEFERLİK bir tarihsel
aktarım (kalıcı bakım gerektirmeyecek, `worker/parser.py`'nin aksine)
— "yıl bazlı ayrı tarif" bilinçli bir mimari tercih, kod tekrarını
göze alıp her yılın kendi sürprizlerini izole tutuyor.

### 5.3 Gerçek Format Sürprizleri (Yıl Yıl, Doğrulanmış)
| Yıl | Sürpriz | Çözüm |
|---|---|---|
| 2016 | T10 (Tüketici Sayısı) tablosu HİÇ YOK; Ocak-Mart'ta İstanbul 2 satıra bölünmüş; Temmuz'da Adana satırı kayıp | T10 aramanın kendisi try/except'te; İstanbul satırları dict-toplamayla birleştirilir; Adana Genel Toplam'dan TÜRETİLİR (audit_log'da `turetilmis=true` işaretli) |
| 2017-2020 | T11 tablosu bazı yıllarda "İl" kelimesi OLMADAN başlıklı (T4'ün il-breakdown tablosuyla karışabilir) | İçerik bazlı ayırt etme (satır sayısı ~82-84 vs küçük tablo) |
| 2021/2022 | Taksonomi RENAME: "Ticarethane"→"Kamu ve Özel Hizmetler", "Tarımsal Sulama"→"Tarımsal" (2022 Ocak-Nisan eski küme, Mayıs-Aralık yeni küme) | `_GRUP_TAKMA_ADLAR` alias sözlüğü + mevsimsellik kanıtıyla (2023-2025 Tarımsal'ın Mart→Mayıs 2,8-4,2 kat sıçraması) doğrulanmış RENAME kararı |
| 2023-2025 | Word raporları 2021'den itibaren AYRICA "Dönemler Arası Karşılaştırma" tabloları basıyor (bir önceki yılın aynı ayını da gösterir) | `genel_toplam_satirini_oku()` bu tabloları HİÇ ARAMAZ — yalnız T11'in kendi tablosu kullanılır, "yanlış kolon" riski yapısal olarak yok (bkz. §5.4 ve §6.4) |

### 5.4 `fact_tuketim_ulke_geneli` Tasarımı (2026-09-05)
İlk tasarım önerisi "Sanayi dahil küçük bir karşılaştırma tablosu ara"
idi — araştırma bunun GEREKSİZ ve RİSKLİ olduğunu gösterdi (2024-10 için
3 farklı aday tablo bulunuyor: tek-ay/kümülatif/tüketici-sayısı,
karıştırılması kolay). Bulunan daha sağlam çözüm: **fact_tuketim için
zaten bulunan T11 tablosunun kendi "Genel Toplam" satırı**, il kırılımı
olmayan, Sanayi DAHİL tüm grupların (Aydınlatma/Kamu ve Özel Hizmetler/
Mesken/Sanayi/Tarımsal) ülke geneli değerini ZATEN veriyor —
`genel_toplam_satirini_oku()` bu satırı, `t11_oku()` ile AYNI sütun→grup
eşlemesini (`grup_kolonlarini_coz()`, paylaşılan helper) kullanarak okur.
120 ayın (2016-2025) TAMAMINDA gerçek docx'lere karşı doğrulandı — sıfır
eksik ay, sıfır format hatası.

---

## 6. Ingestion Pipeline

### 6.1 Batch Yaşam Döngüsü
```
queued → (is_sahiplen, advisory lock) → running
  → başarılı: succeeded (aktivasyon SONRASI) | başarısız: retrying → dead_letter | failed
```
`ingestion_batch.status` değerleri: `queued`, `running`, `succeeded`,
`failed`, `retrying`, `dead_letter`. Faz 0'da senkron (elle script
çağrısı); Faz 1'de `job_status` kuyruğu üzerinden asenkron (bkz. §6.5).
Sahiplenme `ingest.batch_sahiplen()` ile ATOMİK (advisory lock) —
aynı batch'i iki worker aynı anda işleyemez.

### 6.2 audit_log Felsefesi — Hiçbir Şeyin Üzerine Yazılmama
`audit_log` append-only'dir (UPDATE/DELETE hiç kimseye GRANT
edilmez, `worker/validate_rls_static.py` bunu statik olarak doğrular).
Her önemli olay (`ingest_tamamlandi`, `batch_onaylandi`) bir JSONB
`payload` ile kaydedilir — **reddedilen (`red_satirlari`) satırların TAM
İÇERİĞİ dahil**. Bu tasarım kararı 2026-09-08'de kritik önem kazandı:
reddedilen satırların audit_log'da saklanmış olması, aylar sonra
"neden bu il/grup eksik" sorusunun GERÇEK VERİYLE (tahminle değil)
yanıtlanabilmesini sağladı (bkz. §6.4).

### 6.3 Doğrulama Kuralları — Red / Karantina Ayrımı
`worker/kpi.py:dogrula_tuketim()` / `dogrula_uretim()` / `dogrula_abone()`
/ `dogrula_serbest_tuketici()` her satırı ikiye ayırır:
- **RED**: negatif değer (`tuketim_mwh < 0` vb.) — satır fact tablosuna
  HİÇ YAZILMAZ, `audit_log.red_satirlari`'nda kayıtlı kalır.
- **KARANTİNA**: bilinmeyen grup/tür — satır fact tablosuna YAZILMAZ,
  ayrıca işaretlenir (uygun bir alias eklenmeden geçmez, ValueError).
`otomatik_onaya_uygun()` red=0 VE karantina=0 VE mutabakat≠False
şartını arar; tutmazsa elle onay beklenir.

### 6.4 VAKA — 39 Aylık "Mutabakat Uyumsuzluğu" (2026-09-08)
`fact_tuketim_ulke_geneli`'nin 120 aylık backfill'inden sonra, 39 ay
`fact_tuketim`'in il bazlı toplamıyla (Sanayi hariç 4 grup, `baglanti`
SUM ile katlanmış) ≤%0,5 tolerans dışında çıktı. **Kök neden araştırıldı
ve KANITLANDI (tahmin değil):** Bu bir veri hatası DEĞİLDİ — `kpi.
dogrula_tuketim()`'in negatif değer reddi kuralı İKİ FARKLI
GRANÜLERLİKTE BAĞIMSIZ uygulanıyor:
- **İl seviyesi** (`fact_tuketim`): bir ilin Tarımsal/Aydınlatma değeri
  negatifse SATIR reddedilip hiç yazılmıyor.
- **Ülke seviyesi** (`fact_tuketim_ulke_geneli`): T11'in Genel Toplam
  satırı, EPDK'nın KENDİ NETLEŞTİRDİĞİ (bu negatif düzeltmeleri ZATEN
  içeren) toplam.

Sonuç: `fact_tuketim`'in aktif il toplamı, reddedilen (negatif) illerin
payı kadar sistematik olarak YÜKSEK çıkıyordu. Kanıt (2020-02 Tarımsal,
en kötü vaka, %459 fark): `audit_log`'da 7 il için reddedilen değerler
toplamı = −88.166,69 MWh; düzeltilmiş toplam (107.375,11 − 88.166,69 =
19.208,42) ≈ `fact_tuketim_ulke_geneli` (19.208,40). **Kalıcı çözüm:**
`worker/scripts/mutabakat_ulke_geneli.py` (yeni script) audit_log'daki
bilinen reddedilen satırları hesaba katarak karşılaştırır — migration/veri
temizliği GEREKMEDİ, her iki tablo da zaten doğruydu. 479/479 (tarih,grup)
çifti bu düzeltmeyle uyumlu çıktı; 120/120 ay aktive edildi (yalnız
2016-12 4/5 grupla — Tarımsal o ay ÜLKE seviyesinde de negatif çıktığı
için hiç yüklenmedi, kullanıcı kararıyla kabul edildi). **Kalıcı kural:**
gelecekteki her yeni ay için de aynı durum (bir ilde negatif düzeltme)
tekrar çıkabilir — bu BEKLENEN bir davranıştır, `mutabakat_ulke_geneli.py`
standart mantığı bunu otomatik hesaba katar, tekrar "bulunmasına" gerek
yoktur. (Tam detay: `dokumanlar/06_canli_veri_operasyon_gunlugu.md`
2026-09-08 kaydı.)

### 6.5 `job_worker.py` — Faz 1 Asenkron Kuyruk
Harici broker YOK (Redis/Celery/RabbitMQ) — salt Postgres polling
(`ingest.is_sahiplen`/`is_basarili`/`is_basarisiz`), ADR-6'nın
"self-host edilebilir, minimum dış bağımlılık" çizgisiyle tutarlı.
`python worker/job_worker.py` (`--once`, varsayılan, kuyruğu boşaltıp
çıkar) veya `--loop --interval N` (sürekli poll). Otomatik aktivasyon
eşiği (2026-08-30 kullanıcı kararı): `otomatik_onaya_uygun()` tutarsa
`batch_onayla()` OTOMATİK çağrılır; tutmazsa batch 'running' bırakılıp
net bir uyarı basılır. Hata durumunda `is_basarisiz()` üstel geri
çekilmeyle 'retrying', `_MAX_DENEME` aşılınca 'dead_letter' — bayat
heartbeat'e sahip (worker çökmüş) işler sonraki bir `is_sahiplen()`
çağrısında geri alınır.

---

## 7. KPI Sözleşmeleri

Kaynak: `dokumanlar/04_kpi_sozlesmeleri.md` (Ek B) + `worker/kpi.py` (29
fonksiyon, satır satır doğrulandı). **Ortak kurallar:** yalnız
`is_active=true` kayıtlar; sıfıra bölme → NULL ("hesaplanamaz"), sahte
0 ÜRETİLMEZ; oranlar 1 ondalık, kabul toleransı ±%0,5; baz sıcaklıklar
`sistem_parametre`'den okunur (OD-1, koda gömülmez).

### 7.1 Üretim & Kapasite (Faz 0 production)
| KPI | Formül | Kenar durum |
|---|---|---|
| KPI-01 Toplam kurulu güç (MW) | Σ kurulu_guc_mw | yoksa 0 |
| KPI-02 Toplam üretim (MWh) | Σ uretim_mwh (lisanslı) | yoksa 0 |
| KPI-03 Yenilenebilir pay (%) | Σ uretim(yen) / Σ uretim ×100 | payda 0→NULL |
| KPI-04 Kaynak payı (%) | Σ uretim(kaynak)/Σ uretim ×100 | payda 0→NULL |
| KPI-05 Kapasite faktörü (%) | uretim/(kurulu×saat)×100 | kurulu 0→NULL |
| KPI-06 HHI | Σ pay² (pay=kaynak/toplam, ölçek 0-1) | payda 0→NULL |
| KPI-07 Lisanssız pay (%) | Σ uretim(lisanssız)/Σ uretim ×100 | payda 0→NULL |

### 7.2 Tüketim (Faz 0 production)
| KPI | Formül | Kenar durum |
|---|---|---|
| KPI-08 Toplam tüketim (MWh) | Σ tuketim_mwh (tüm baglanti) | yoksa 0 |
| KPI-09 Grup payı (%) | Σ tuketim(grup)/Σ tuketim ×100 | payda 0→NULL |
| KPI-10 Abone başı tüketim (MWh) | Σ tuketim/Σ abone | abone 0→NULL |
| KPI-13 YoY (%) | (t − t₋₁₂ay)/t₋₁₂ay ×100 | geçmiş yoksa VEYA grup kümesi t/t₋₁₂ay arasında BİREBİR uyuşmuyorsa → NULL |

**KPI-13'ün grup-kümesi kısıtı (2026-09-03):** KPI-25/26 ile AYNI kök
nedene aynı disiplin — Word yılı (Sanayi yok) ile Excel yılı (Sanayi
var) karşılaştırılırsa sahte bir YoY üretilirdi (gerçek örnek: %+70,9
sahte vs %+2,2 gerçek, Sanayi'nin ikisinden de çıkarılmasıyla).

### 7.3 Hava Türetimleri (Faz 0 production)
| KPI | Formül |
|---|---|
| KPI-23 HDD | Σ_gün max(0, 18−t_gün), aylık toplam |
| KPI-24 CDD | Σ_gün max(0, t_gün−22), aylık toplam |

### 7.4 Hava Normalizasyonu (Faz 3'te production, 2026-08-30)
- **KPI-11** arındırılmış tüketim = gerçek − β·(HDD−HDD_norm) − γ·(CDD−CDD_norm)
  — β/γ: geçmiş gözlemler üzerinde OLS (min 12 ay, `beta_gamma_tahmin_et`);
  yetersizse NULL.
- **KPI-12** norm sapması = (arındırılmış − tüketim_norm)/tüketim_norm ×100
  — tüketim_norm: son 5 yıl aynı-ay ARINDIRILMIŞ ortalama, ROLLING (OD-2).
- HDD_norm/CDD_norm: aynı ay için son 10 yılın SABİT ortalaması (OD-2).
- `worker/analytics.py:kpi_11_12_hesapla()` (il bazlı) +
  `kpi_11_12_ulusal_hesapla()` (Türkiye geneli agregasyon, Option A —
  il bazlı sonuçları topluyor, ayrı bir regresyon KOŞMUYOR).

### 7.5 CAGR (Yıllık, n = son_yıl − ilk_yıl)
Jenerik formül: `(son/ilk)^(1/n) − 1` (`kpi_cagr`).
- **KPI-25** CAGR — toplam tüketim (%): yalnız Sanayi'yi İÇEREN yıllar
  seriye girer (Word 2023-2025 hariç, Karar 2) — filtre olmasaydı sahte
  bir CAGR üretilirdi (gerçek örnek: -%2,2 sahte). Bugün yalnız 2026 tek
  Sanayi'li yıl → NULL ("hesaplanamaz"), ikinci Sanayi'li tam yıl
  (2027+) gelince otomatik seriye girecek.
- **KPI-27** CAGR — Sanayi-HARİÇ tüketim (%): Sanayi TÜM yıllardan
  açıkça çıkarılarak hesaplanır (KPI-25'in TERSİ strateji — sorunlu
  grubu sil, sorunlu yılı değil). KPI-25'İN YERİNE GEÇMEZ (resmi "toplam
  tüketim" tanımını karşılamaz). 2023→2025 (3 tam yıl) için canlıda
  +%6,9 hesaplanıyor (2026-09-03 doğrulaması).
- **KPI-26** CAGR — yenilenebilir kurulu güç (%): STOK metriği (aylar
  TOPLANMAZ, yılın son ayı alınır). Yalnız Lisanslı verisi (T1) OLAN
  yıllar seriye girer — Word 2023-2025'te T1 yok (Karar 3), filtre
  olmasaydı sahte CAGR üretilirdi (AYNI kök neden KPI-25 ile).

### 7.6 `kpi_esik` — Trafik Işığı Renk Eşikleri
Migration `20260905_0001_kpi_esik_seed.sql` ile eklendi (OD-3: eşikler
config tablosunda, PO onaylı). `worker/kpi.py:esik_rengi(deger,
yesil_alt, sari_alt, yon)` — `yon='yukselik'` (değer büyüdükçe iyi) ya
da `'alcelik'` (değer küçüldükçe iyi, örn. HHI). `deger=None` → renk
`None` ("hesaplanamaz"ı sahte bir renkle GİZLEMEZ).

---

## 8. Güvenlik

### 8.1 RLS/GRANT Modeli
3 fiziksel PostgreSQL rolü: `viewer` (SELECT, yalnız `is_active=true`),
`data_operator` (INSERT/UPDATE, SELECT politikası YOK — kasıtlı, "veri
operatörü yükler/günceller, taramaz"), `admin` (FOR ALL). Rol seçimi
`public.current_app_role()` (SECURITY DEFINER) fonksiyonuyla —
`auth.jwt()`'in `app_metadata.role` claim'ini okur, bilinen 3 değer
dışındaysa NULL döner (sessizce `viewer` VARSAYILMAZ). RLS politikaları
ÇİFT KAPILI: hem PostgreSQL'in fiziksel rol hedeflemesi (`TO viewer`)
HEM `current_app_role()`'ün doğru değeri döndürmesi gerekir.

### 8.2 GRANT/RLS Kopukluk Zinciri — Gerçek Olay (2026-09-04)
`20260819_0002_rls_roles.sql`'in GRANT/RLS kapsamı baştan eksikti —
canlı kullanımda `permission denied for table dim_tarih` ve ardından
sessiz sıfır-satır sonuçları olarak ortaya çıktı. 4 migration'la
kapatıldı (`20260904_0001`-`0004`): eksik `dim_*` GRANT'ları, policy'siz
açık kalmış RLS DISABLE, `sistem_parametre`/`kpi_esik`/`job_status`
GRANT'ları, aynı desenin bu 3 tabloda da DISABLE'ı. **Ayrıca ADR-7'nin
kendi RLS notunda** (bkz. §2.2), `postgres` kullanıcısının `SET ROLE
viewer` yapamaması PG17'nin `pg_auth_members.set_option=true`
gerektirmesinden kaynaklandığı (pooler modu DEĞİL) — dar yetkili
`app_dashboard_service` rolü (migration `20260819_0016`, `WITH INHERIT
FALSE, SET TRUE`) ile çözüldü. Ayrıca `auth` şemasına GRANT devri
Supabase platformunda mümkün olmadığından `current_app_role()`
SECURITY DEFINER yapıldı (migration `20260819_0018`) ve main'e hiç
girmemiş 14 adet belgesiz `USING(true)` bypass politikası temizlendi
(migration `20260819_0019`, git-arkeolojisiyle kaynağı bulundu — bkz.
`06_adr_dashboard_teknoloji.md`).

### 8.3 Supabase Auth Entegrasyonu (Faz B, 2026-09-05)
`worker/auth.py` (framework-agnostik): `giris_yap(email, sifre)`
Supabase Auth'a (`sign_in_with_password`) doğrular, JWT'yi ÇÖZER (imza
doğrulaması yapmaz — belirteç zaten Supabase'in kendisinden geliyor),
`app_metadata.role`'ü okur (bilinen 3 değer dışıysa erişim reddedilir).
`rol_baglantisi_ac()` `DATABASE_URL_DASHBOARD` (`app_dashboard_service`,
**session-mode**, port 5432 — `DATABASE_URL`'in transaction-mode pooler'ı,
port 6543'ten FARKLI, `SET ROLE`/GUC kalıcılığı için gerekli) ile yeni
bir bağlantı açar, `request.jwt.claims` GUC'unu gerçek JWT ile set edip
`SET ROLE <rol>` yapar (`rol` her zaman whitelist'e karşı doğrulanır,
`psycopg.sql.Identifier`/`Literal` — ham string birleştirme YOK).
Başarısız girişte GENEL bir hata ("E-posta veya şifre hatalı") — hesabın
var olup olmadığı SIZDIRILMAZ. Yeni kullanıcı eklemek kod değişikliği
DEĞİL — Supabase Dashboard'dan `app_metadata.role` elle set edilir.

### 8.4 Oturum Süresi + Login Rate-Limiting (Aşama 2, 2026-09-05)
- **8 saatlik mutlak oturum süresi** (`app/dashboard.py:GIRIS_SURESI_SN`):
  `rol_baglantisi_ac()` JWT'yi yalnız giriş anında bağlantıya gömdüğünden
  Supabase'in kendi JWT süresi (1 saat, resmi dok. doğrulandı) hiç
  UYGULANMIYORDU — `st.session_state.giris_zamani` ile elle takip
  ediliyor, süre dolunca zorla çıkış.
- **Login rate-limiting** (`worker/auth.py`): Supabase'in sign-in-with-
  password için AYRI bir deneme sınırı OLMADIĞI resmi dokümantasyondan
  doğrulandı (yalnız OTP/anonim-giriş için var) — panel açık internette
  (Streamlit Community Cloud) barındırıldığından süreç-içi bir sayaç
  eklendi: e-posta başına 15 dk'da 5 başarısız denemeden sonra
  `GirisKilitli`, Supabase'e hiç istek atmadan reddedilir. Hesap
  varlığını SIZDIRMAZ (sayaç e-postanın kendisine bağlı).

---

## 9. CI/CD

Kaynak: `.github/workflows/{ci,security,deploy,scheduled-refresh}.yml`
(4 workflow dosyası, tam okundu).

### 9.1 `ci.yml` — 5 İş (Job)
| Job | İçerik |
|---|---|
| `worker` (Worker: lint · types · validation) | ruff check + format, mypy, `worker/validate_rls_static.py`, `worker/dogrula.py` (golden veri karşılaştırma), `pytest worker/tests -v` (bu job DATABASE_URL/DATABASE_URL_DASHBOARD hiç SET ETMEZ → `pytestmark skipif` ile TÜM 6 `*_integration.py` otomatik atlanır), `compileall` |
| `integration` (Schema validation + static RLS validation) | `worker`'a `needs` bağımlı. Disposable `postgres:16` servisi → `supabase/ci-only/01_roles_bootstrap.sql` (anon/authenticated/service_role taklit) → `00_auth_stub.sql` (auth şema stub) → **TÜM 25 migration sırayla** (`ON_ERROR_STOP=1`) → `validate_rls_static.py` + `validate_role_access.py` (GERÇEK `SET ROLE`+sorgu ile RLS davranışı) + yalnız **5** `*_integration.py` dosyası isimle tek tek çağrılır (`test_ingest/pipeline/job_worker/analytics/fetch_weather_integration.py`) — **`test_auth_integration.py` bu listede YOK** (bkz. not) |

**`test_auth_integration.py` — CI'da HİÇ ÇALIŞMAZ, manuel-only:** Diğer
5 dosya `DATABASE_URL`'e göre `skipif` yapar (CI'nin disposable
`postgres:16`'sıyla uyumlu); bu dosya **`DATABASE_URL_DASHBOARD`**'a
göre `skipif` yapar (gerçek Supabase Auth/JWT akışını test eder, düz
`postgres:16`'da anlamı yok). Ne `worker` job'ı (hiçbir DB env'i set
etmez) ne `integration` job'ı (yalnız `DATABASE_URL` set eder, isim
listesinde bu dosya da YOK) bu testleri ÇALIŞTIRIR — **yalnız gerçek
Supabase'e karşı elle** (`DATABASE_URL_DASHBOARD` tanımlıyken)
çalışır. Bu doküman yazılırken (WSL container, `.env`'de gerçek
`DATABASE_URL_DASHBOARD` mevcut) doğrudan çalıştırılıp doğrulandı: 3/3
test PASSED (gerçek Supabase Auth'a karşı, `giris_yap` yanlış kimlik/
`rol_baglantisi_ac` sentetik+admin claim senaryoları).
| `supabase-tooling` | `npm ci` + `npm audit --audit-level=high` |
| `sql` (SQL lint) | `sqlfluff lint db supabase/migrations supabase/ci-only --dialect postgres` |
| `quality-gate` | `worker`+`integration`+`supabase-tooling`+`sql`'e `needs` — branch protection'ın ZORUNLU kontrolü budur |

**Migration listesi ELLE, glob DEĞİL:** `integration` job'ı her migration
dosyasını TEK TEK, isimle `psql -f` çağırır — yeni bir migration
eklendiğinde bu listeye DE elle eklenmezse CI o migration'ı hiç
uygulamaz (defalarca tekrarlanan bir gerçek disiplin: her yeni migration
turu bunu unutmamak zorunda kaldı, bkz. §10).

### 9.2 `security.yml` — 6 İş
`gitleaks` (secret tarama, PR'larda `pull-requests:read` gerekiyor —
Dependabot PR'ları fork gibi davranıyor), `pip-audit --strict`,
`npm audit --audit-level=high`, `trivy` (fs+deps+secret+misconfig,
HIGH/CRITICAL'da job FAIL — SARIF/code-scanning YOK, GHAS Free-plan
private repo'da desteklenmiyor, düz tablo çıktısı job summary'ye
yazılıyor), `bandit` (`-r worker app -x worker/tests -s B101` — B101
assert kullanımı testlerin/`INSERT...RETURNING`'in kendi idiomu,
bilinçli skip), `license-check` (yalnız OSI-uyumlu lisanslara izin,
GPL-3.0/Proprietary/UNKNOWN blok; LGPL-3.0 psycopg için BİLİNÇLİ
istisna — kütüphane bağımlılığı, değiştirilip yeniden dağıtılmıyor).
Haftalık cron (`0 6 * * 1`) + her push/PR.

### 9.3 `deploy.yml` / `scheduled-refresh.yml`
- **deploy.yml** (ADR-5): `build-push` (GHCR) job'ı **`if: false` ile
  DEVRE DIŞI** — `web/` klasörü ve Dockerfile'lar henüz yok. `migrate`
  (`PROD_DATABASE_URL` ile TÜM migration'ları glob'la sırayla uygular —
  ci.yml'in aksine BURADA glob kullanılıyor), `deploy-ssh` (self-host,
  Coolify alternatifi yorumda), `smoke` job'ları `build-push`'a
  `needs` bağımlı olduğundan OTOMATİK skip ediliyor.
- **scheduled-refresh.yml**: her gün 04:00 UTC, `python -m worker.jobs.
  fetch_weather --incremental` (bir önceki tam ay). **Gerçek olay
  (2026-09-04/05):** bu adım aylarca "başarılı" görünüyordu çünkü
  `if: false` ile KAPALIYDI; gerçekten açılınca `PROD_DATABASE_URL`
  secret'inin repo'da hiç tanımlı olmadığı ortaya çıktı — kod hatası
  DEĞİL, eksik bir GitHub secret'tı (bkz. §10).

### 9.4 Test Stratejisi
25 dosya, **248 benzersiz `def test_*`** fonksiyonu (19 unit/regresyon +
**6** `*_integration.py`, bkz. §9.1 kutucuğu). Bunlar birden fazla
sayıyla raporlanır, hepsi doğru — ölçüm kapsamı farklı:
- **227**: pytest'in 19 unit/regresyon dosyasından TEK BAŞINA topladığı
  test ID sayısı (parametrize genişlemesiyle 199 def → 227 ID) —
  **doğrudan doğrulandı (2026-09-08):** temiz bir kabukta, `.env`
  hiç erişilebilir DEĞİLKEN (`env -i`) ve `DATABASE_URL`/
  `DATABASE_URL_DASHBOARD` set EDİLMEDEN `pytest worker/tests
  --collect-only` çalıştırıldı — 6 `*_integration.py` HARİÇ tutulunca
  **227**, TÜMÜ dahil edilince **276** çıktı (`skipif` yalnız
  ÇALIŞTIRMAYI engeller, TOPLAMAYI değil — bu iki kavramın
  karıştırılması önceki bir taslakta yanlışlıkla "230" yazılmasına
  sebep olmuştu, bkz. §14 madde 4).
- **230 (bu oturumun WSL koşusundaki gerçek rapor)**: `fact_tuketim_
  ulke_geneli` turlarında (WSL/Docker container, GERÇEK `.env`)
  çalıştırılan "230 passed" rakamı = **227 (yukarıdaki, tamamen yerel)
  + 3 (`test_auth_integration.py`)** — yalnız 5 dosya `--ignore`
  edilmişti, `test_auth_integration.py`'nin kendi `DATABASE_URL_
  DASHBOARD` gate'i o ortamda TANIMLI olduğundan bu 3 test YANLIŞLIKLA
  değil, GERÇEKTEN çalışıp geçmişti (rollback-izole, zararsız — canlı
  Supabase Auth'a karşı). Bkz. §14 madde 4.
- **276**: pytest'in TÜM 25 dosyadan (6 `*_integration.py` DAHİL)
  topladığı ID sayısı — hiçbir CI job'ı bunu TEK SEFERDE çalıştırmaz
  (integration job'ı yalnız 5'ini isimle çağırır, `test_auth_
  integration.py` HİÇBİR CI job'ında çalışmaz, bkz. §9.1).

**⚠️ Canlı Supabase'e karşı test çalıştırma kuralı (README, 2026-09-03):**
Tam pytest paketi ASLA canlıya karşı çalıştırılmaz — yalnız CI'nin
izole `postgres:16`'sında. Gerçek bir olay: 2026-09-02'de tam paketin
yanlışlıkla canlıya karşı çalıştırılması, `test_job_worker_integration.py`
KENDİ commit'lerini yaptığından (standart `conn` fixture'ının rollback
izolasyonunu bypass eder), sentinel `tarih_id=209912` için kalıcı test
verisi bırakmıştı — 3 turda tespit edilip temizlendi. Bundan sonra
canlıya karşı yerel doğrulama YALNIZ hedefli `-k <desen>` alt kümesiyle
yapılıyor.

---

## 10. Faz Bazlı İlerleme Geçmişi

Kaynak: `git log` (141 commit, 2026-08-18→2026-09-07), tarih sırasıyla
yeniden kuruldu. Her aşamada gerçek bug'lar/kararlar isimlendirilmiştir.

### Faz 0 — İskelet (2026-08-18/19)
`db/schema.sql` (yıldız şema referansı), `dokumanlar/` (SRS özetleri),
CI/CD iskeleti, golden dataset. İlk RLS/rol politikaları eklendi
(`20260819_0001`-`0003`). **Gerçek bug'lar bu turda:** `current_app_role()`
EXECUTE grant'ı eksikti; CI'ın `postgres:16`'sı Supabase'in yönetilen
rollerine (anon/authenticated/service_role) sahip değildi ("role does
not exist" hataları) — `supabase/ci-only/01_roles_bootstrap.sql` ile
çözüldü; `auth` şeması stub'ı (`00_auth_stub.sql`) gerçek Postgres'te
var olan ama düz `postgres:16`'da olmayan şemayı taklit etmek için
eklendi.

### Faz 1 — Asenkron Worker (2026-08-30)
`job_status` kuyruğu + `worker/job_worker.py` (bkz. §6.5). Koşullu
otomatik onay eşiği bu turda karara bağlandı (kullanıcı kararı,
`otomatik_onaya_uygun()`).

### Faz 2 — Dashboard (2026-08-30)
`app/dashboard.py` gerçek `worker/analytics.py`/`worker/kpi.py`
sorgularına bağlandı (önceden statik `data/tr_ocak2026.py`). Gerçek
bug'lar: `ModuleNotFoundError` (worker/ paketi bulunamadı — `sys.path`
düzeltmesi); KPI-09 payı kartının İl filtresini yansıtmaması.

### Faz 3 — Hava Normalizasyonu (2026-08-30, 3 commit'lik seri)
Şema + `worker/kpi.py` (β/γ regresyon, hava/tüketim normu) +
`worker/jobs/fetch_weather.py` (Open-Meteo entegrasyonu) +
dashboard KPI-11/12/25/26 kartları + `scheduled-refresh.yml`. KPI-25/26
"Sanayi dahil/Lisanslı-var yıl filtresi" kısıtları BU AŞAMADA değil,
**2026-09-02'de** (aşağıya bkz.) eklendi — ilk sürüm sahte CAGR
üretiyordu.

### 2016-2022 Word Tarihsel Genişlemesi (2026-08-31 → 2026-09-03)
En yoğun, en çok gerçek-veri-sürprizi çıkan aşama. Sırayla: 2025→2024→
2023 (Excel'e en yakın format) → T4/KPI-26 düzeltmesi → **2022'den
2016'ya GERİYE DOĞRU** (2022 kısmi: Mayıs-Aralık, Ocak-Nisan taksonomi
sorunuyla beklemede → 2021 yalnız T4 → **taksonomi RENAME kararı**
(Ticarethane→Kamu ve Özel Hizmetler, Tarımsal Sulama→Tarımsal, 2 bağımsız
kanıtla doğrulandı) → 2021 tam yıl + 2022 açıldı → 2020/2019/2018/2017
(hepsi T11 12/12, T10 kaynakta yapısal olarak yok) → **2016** (SON yıl,
en çok format sürprizi: T10 hiç yok, İstanbul bölünmüş satır, Temmuz
Adana kaybı → çift-kaynaklı türetme, tahmin DEĞİL). Ortam engeli
(Miniconda ile Windows Akıllı Uygulama Denetimi'nin pandas'ı bloklaması)
2026-09-02'de İLK KEZ karşılaşıldı ve çözüldü (bkz. §11.5). Sonuç:
2016-2022'nin 167 batch'i `worker/scripts/toplu_onayla_word.py` ile
toplu aktive edildi (2026-09-03).

### GRANT/RLS Kopukluk Zinciri (2026-09-03/04)
Bkz. §8.2 — Faz B'nin RLS kök nedeni bulunması (2026-09-03) + 4
migration'lık dim/sistem_parametre/kpi_esik/job_status GRANT+RLS
düzeltme turu (2026-09-04).

### Faz B — Çok-Kullanıcılı Auth (2026-09-03/05)
`worker/auth.py`, gerçek giriş ekranı, `app_dashboard_service` özel
rolü, `current_app_role()` SECURITY DEFINER, 14 belgesiz bypass
politikasının temizlenmesi (bkz. §8.2/8.3), Ahmet'in admin hesabı +
uçtan uca doğrulama (2026-09-03) → 8 saatlik oturum + login
rate-limiting (Aşama 2, 2026-09-05, bkz. §8.4).

### Regresyon Testleri + Dashboard Cilası (2026-09-04)
`test_word_2023/2024/2025.py` (36 yeni test) — önceki "2023-2025 eksik"
açık maddesi kapandı. `veri_kapsam_disi` dashboard'a bağlandı (Aşama 7).
Tüm `@st.cache_data`'lara `ttl=1800` eklendi (önceden TTL yoktu, yeni
veri görünmesi için elle "Reboot app" gerekiyordu). "Sistem Durumu"
bölümü (son batch'ler + iş kuyruğu, Görev 2).

### `kpi_esik` + KPI-11/12 Türkiye Geneli (2026-09-05, Görev 3/4)
Dashboard'a trafik-ışığı renk eşikleri + `kpi_11_12_ulusal_hesapla()`
(Option A: il bazlı sonuçları topla, ayrı regresyon KOŞMA).

### Scheduled Refresh Kök Nedeni + 2016-2025 `fact_hava_aylik` Backfill (2026-09-05)
`scheduled-refresh.yml` aylarca "başarılı" görünüyordu çünkü adım
`if: false` ile kapalıydı (bkz. §9.3); gerçekten açılınca kök neden
eksik `PROD_DATABASE_URL` secret'i çıktı (Open-Meteo ile hiç ilgisi
yoktu). 6 aylık elle backfill'in ardından **2016-2025'in TAMAMI (120 ay)**
`fact_hava_aylik`'e backfill edildi. **Gerçek bulgu (tahmin değil):**
Open-Meteo'nun resmi dokümantasyonundaki limitler (600/dk vb.)
YANILTICIYDI — gerçek engel dokümante edilmemiş bir **saatlik kota**
(61. istekte 429, yanıt gövdesi "Hourly API request limit exceeded"
diyordu). Kısa backoff'lar işe yaramadı; çözüm 65 dk'lık gerçek bekleme
molalarıydı (~3 saat toplam süre). Sonuç: KPI-11/12'nin 10 yıllık sabit
hava normu penceresi ilk kez tam doldu, 2026-02..06 için "hesaplanamaz"
yerine gerçek değer üretmeye başladı.

### `fact_tuketim_ulke_geneli` (2026-09-05/08) {#faz-ulke-geneli}
Bkz. §3.2, §5.4, §6.4 — yeni tablo + parser + 120 ay backfill + 39 aylık
mutabakat vakasının kök nedeni bulunup kalıcı olarak çözülmesi. Bu süreç
sırasında **Windows Smart App Control** (SAC) `psycopg`+`lxml`'in
derlenmiş bileşenlerini bloklamaya başladı (önceki 2026-09-03 SAC
olayından FARKLI bileşenler — bkz. §11.5) — çözüm WSL2 + Docker Dev
Container'a geçiş oldu (yol boyunca ayrı, gerçek bir "C: sürücüsü 39 MB
boş" sorunu da çıkıp `wsl --update` + disk temizliğiyle çözüldü).

---

## 11. Bilinen Sorunlar / Açık Maddeler

### 11.1 2026 Excel Format Uyumu — AÇIK DEĞİL, DOĞRULANMIŞ
Bu doküman taslağının onay turunda "2026 Excel format uyumu (gerçekte
test edilip edilmediği DOĞRULANACAK)" bir açık madde olarak öngörülmüştü
— araştırma bunun **zaten çözülmüş** olduğunu gösterdi: `worker/parser.py`
yalnız senkron (gerçek Ocak 2026 dosyasına karşı doğrulanmış sentetik
xlsx, `worker/tests/test_parser.py` + `worker/dogrula.py`) DEĞİL, canlı
Supabase'de **6 gerçek ay** (202601-202606) ile de kanıtlanmış durumda
(`dokumanlar/06_canli_veri_operasyon_gunlugu.md` satır 148-161). Gerçek
açık madde: 2026-07'den itibaren HENÜZ hiçbir ay yüklenmedi (EPDK'nın
raporu henüz yayınlamamış olması muhtemel — parser'ın kendisiyle ilgisi
yok).

### 11.2 KPI-25/27'nin `fact_tuketim_ulke_geneli`'yi Kullanıp Kullanmayacağı
Açık karar — `fact_tuketim_ulke_geneli` yalnız VERİ hazırlığı olarak
eklendi (2026-09-05/08), KPI formülü (`worker/analytics.py:
yillik_tuketim_serisi_getir`/`yillik_tuketim_sanayi_haric_serisi_getir`)
BU TURDA değiştirilmedi. Karar verilirse KPI-25'in bugünkü "yalnız
Sanayi'yi içeren yıl" filtresi muhtemelen gevşetilebilir (artık 2016-2025
için de ülke geneli Sanayi verisi var) — ama bu doğrudan `fact_tuketim`
(il bazlı) ile `fact_tuketim_ulke_geneli` (ülke bazlı) arasında bir
KARIŞIK KAYNAK KPI'sı tasarımı gerektirir, dikkatli ele alınmalı.

### 11.3 2016-12 Tarımsal — Kalıcı Eksik
`fact_tuketim_ulke_geneli`'de 2016-12 yalnız 4/5 grupla aktif (Tarımsal
o ay ülke seviyesinde de negatif çıktığı için hiç yüklenmedi, kasıtlı —
bkz. §6.4). Dashboard'da bu ay/grup için "veri yok" görünmesi beklenir.

### 11.4 Admin Rol-Atama UI'ı ve Veri Girişi UI'ı — Ertelendi
`data_operator` rolünün RLS izin altyapısı TAM kurulu (INSERT/UPDATE)
ama HİÇBİR UI'ı yok — bugün bir `data_operator` girişinde dashboard
açık bir bilgi mesajı gösterir ("veri girişi ekranı henüz yok",
2026-09-05 kararı). Yeni kullanıcı eklemek/rol atamak hâlâ tamamen elle
(Supabase Dashboard). İkisi de bilinçli olarak ERTELENDİ (kullanıcı
sayısı arttığında/ihtiyaç netleştiğinde ayrı bir iş kalemi).

### 11.5 Windows Smart App Control — Bu Makineye Özgü, Kod Sorunu DEĞİL
İki AYRI olayda (2026-09-03: numpy/pandas; 2026-09-07/08: psycopg+lxml)
Windows'un Smart App Control özelliği bu makinedeki conda ortamının
derlenmiş bileşenlerini bloklamıştır. İlk olayda çözüm PyPI wheel'e
geçmekti (`pip install --force-reinstall --no-cache-dir <paket>`);
ikincisinde bu yetmedi, WSL2+Docker Dev Container'a geçildi. **Proje
koduyla hiçbir ilgisi yok** — yalnız geliştiricinin kendi Windows
makinesindeki bir güvenlik politikası. Gelecekte tekrarlanırsa: önce
hafif çözümü dene, yetmezse WSL/Dev Container'a geç.

### 11.6 Faz 4/5/6 — Henüz Başlamadı
Tahminleme (Faz 4), EPİAŞ (Faz 5), TEİAŞ projeksiyon (Faz 6) ve Next.js
"Son Faz"a geçiş — hiçbiri için kod/tasarım çalışması başlamadı.

### 11.7 `deploy.yml`'in `build-push` Job'ı Devre Dışı
`web/` klasörü ve Dockerfile'lar henüz yok — otomatik CD akışı (GHCR
imaj build) fiilen çalışmıyor, yalnız `migrate` (manuel/push tetikli DB
migration) ve `deploy-ssh`/`smoke` (build-push'a bağımlı, otomatik skip)
tanımlı. Şu an gerçek deploy Streamlit Community Cloud (manuel/otomatik
git-push senkronu) üzerinden — `deploy.yml` bunu YÖNETMİYOR.

---

## 12. Nasıl Çalıştırılır / Geliştirme Ortamı

### 12.1 Yerel Kurulum
```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
pipx install pre-commit && pre-commit install && pre-commit install --hook-type commit-msg
```
Bağımlılıklar (`requirements.txt`): `streamlit`, `pandas`, `numpy`,
`openpyxl`, `requests`, `python-dotenv`, `psycopg[binary]`, `supabase`,
`python-docx`. Dev (`requirements-dev.txt`): `ruff`, `mypy`, `pytest`
(+`pytest-cov`), `sqlfluff==3.3.0`, `bandit`.

### 12.2 Dashboard Çalıştırma
```bash
streamlit run app/dashboard.py
```
`.env`'de `DATABASE_URL_DASHBOARD` tanımlıysa (canlı kurulum) panel
ZORUNLU e-posta/şifre girişi ister (bkz. §8.3). Tanımlı değilse yerel
dosya verisiyle (`data/tr_ocak2026.py`) ya da varsa `DATABASE_URL` ile
girişsiz çalışır.

### 12.3 CI'nin Disposable Postgres Akışı
Yerelde gerçek bir Postgres'e ihtiyaç YOK — CI kendi `postgres:16`
container'ını her çalıştırmada sıfırdan kurar (bkz. §9.1). Yerelde tam
entegrasyon testi çalıştırmak isteyen biri aynı adımları (roller
bootstrap → auth stub → 25 migration → validate script'leri) kendi
`postgres:16`'sına uygulayabilir.

### 12.4 Supabase Canlı Bağlantı — İKİ FARKLI Connection String
| Değişken | Rol | Pooler modu | Kullanım |
|---|---|---|---|
| `DATABASE_URL` | `postgres` (service, RLS'ten muaf) | transaction-mode, port 6543 | Script'ler, backfill, `worker/analytics.py`'nin doğrudan sorguları |
| `DATABASE_URL_DASHBOARD` | `app_dashboard_service` (dar yetkili) | **session-mode, port 5432** | Yalnız `worker/auth.py:rol_baglantisi_ac()` — `SET ROLE`/GUC kalıcılığı için session-mode ZORUNLU |
Bu ikisini KARIŞTIRMAMAK kritik — `DATABASE_URL` ile `SET ROLE viewer`
`permission denied` verir (bkz. §8.2).

### 12.5 Windows'a Özgü Not — Smart App Control + WSL2/Dev Container
Bkz. §11.5. Bu makinede Windows Smart App Control derlenmiş Python
bileşenlerini (psycopg, lxml) bloklarsa: `.devcontainer/devcontainer.json`
(`mcr.microsoft.com/devcontainers/python:1-3.11-bookworm`) ile WSL2
içinde bir Docker container'a geçilebilir — Linux tarafında bu SAC
sınırlaması hiç devreye girmez. `docker run -v <repo>:/workspace -v
<EPDK dosya klasörü>:/epdk-verileri:ro ... sleep infinity` + `docker
exec` ile interaktif çalışılabilir.

---

## 13. Sözlük / Kısaltmalar

### 13.1 Türkçe Şema Terimleri → Anlamı
| Terim | Anlamı |
|---|---|
| `il_kodu` | İl plaka kodu (1-81), `dim_il`'e FK — **`il_id` DEĞİL** (adlandırma kuralı) |
| `tarih_id` | `YYYYMM` (aylık) ya da `YYYY00` (yıllık) — `dim_tarih`'e FK |
| `grup_id` | Tüketici grubu (Aydınlatma/Mesken/Sanayi/Tarımsal/Kamu ve Özel Hizmetler) |
| `baglanti` | `iletim` \| `dagitim` — **P0-2**, `fact_tuketim` grain'inin PARÇASI |
| `is_active` | Bir fact satırının GÜNCEL aktif sürüm olup olmadığı (batch-sürümleme modeli) |
| `ingestion_batch` | Bir dosya/API çekiminin BİR işleme denemesi |
| `source_asset` | Bir dosyanın/API çağrısının kimliği (hash/URI ile) |
| `karantina` | Bilinmeyen grup/tür yüzünden fact'e YAZILMAYAN satır |
| `kapsam_disi` (`veri_kapsam_disi`) | "Kaynakta gerçekten yok" (parser hatası DEĞİL) kaydı |
| `mutabakat` | İki bağımsız toplamın (örn. il toplamı vs Genel Toplam) tutarlılık kontrolü |

### 13.2 Kısaltma Anahtarı
| Kısaltma | Açılımı |
|---|---|
| P0-N | SRS'in "asla ihlal edilmemesi gereken" kritik mimari kuralları (§2, bkz. `02_srs_ozet.md`) |
| OD-N | Konfigürasyon kuralları (baz sıcaklıklar, norm pencereleri — `sistem_parametre`'den okunur) |
| Karar 1/2/3 | Word (2016-2025) kapsam dışı kararları (T13/Sanayi-baglanti/T1, bkz. §4.4) |
| ADR-N | Architecture Decision Record (bkz. §2.2) |
| G-N | CI/CD kalite kapıları (SRS §13.9: birim+golden, kapsam, entegrasyon, güvenlik, RLS/lisans, model MAPE, lint+tip) |
| RLS | Row Level Security (PostgreSQL) |
| DSO | Distribution System Operator (dağıtım şirketi, T12 bağlamında) |
| HDD/CDD | Heating/Cooling Degree Days (ısıtma/soğutma derece günü) |
| SAC | Smart App Control (Windows güvenlik özelliği, bkz. §11.5) |
| WSL2 | Windows Subsystem for Linux 2 |

---

## 14. Çelişki Kayıtları

Bu doküman yazılırken bulunan, önceki notlarla gerçek kod/git arasındaki
çelişkiler — hepsi KOD/GİT esas alınarak çözüldü:

1. **T8/T12 karışıklığı** (bu doküman taslağının onay turunda kullanıcı
   tarafından da işaretlendi): önceki bir özet notu "T12, T8 gibi
   parse edilmiyor" diyordu. Gerçek kaynak (`05_kaynak_dosya_sozlesmesi.md`)
   **T8'in gerçekten parse edilip `fact_tuketim`'i beslediğini**
   gösteriyor — yalnız **T12** (T11 ile redundant olduğu için) bilinçli
   olarak parse edilmiyor. Düzeltildi, bkz. §4.2/§4.3.
2. **"2026 Excel format uyumu doğrulanacak" varsayımı**: bu doküman
   taslağının §11 planında "açık madde" olarak öngörülmüştü — araştırma
   `worker/parser.py`'nin zaten 6 gerçek 2026 ayıyla (202601-202606)
   canlıda kanıtlanmış olduğunu gösterdi. Düzeltildi, bkz. §11.1.
3. **İşlem katmanı için "FastAPI" iddiası**: `dokumanlar/01_kavramsal_
   tasarim.md` §6 tablosu "Backend: Python 3.12 + FastAPI" diyor —
   gerçek kodda HİÇ FastAPI yok, `worker/` düz Python modülleri
   (Streamlit/CLI'dan doğrudan çağrılıyor). Bu iptal edilmiş bir plan
   değil, muhtemelen henüz güncellenmemiş bir doküman satırı — kod esas
   alındı, bkz. §2.1/§2.3.
4. **`worker/tests`'te KAÇ `*_integration.py` var, ve bu oturumun KENDİ
   "230 passed" iddiası tam doğru muydu:** README (Ek D) "6
   `*_integration.py`" diyor — bu doküman yazılırken bu sayı BAĞIMSIZ
   doğrulandı: gerçekten **6** dosya var (`test_analytics_integration.py`,
   **`test_auth_integration.py`**, `test_fetch_weather_integration.py`,
   `test_ingest_integration.py`, `test_job_worker_integration.py`,
   `test_pipeline_integration.py`) — README doğruydu. **Ama bu
   oturumun kendi önceki "230/230 pytest yeşil" raporları**
   (`fact_tuketim_ulke_geneli` turlarında, WSL/Docker container'ında
   çalıştırılan) yalnız **5** dosyayı `--ignore` etmişti —
   `test_auth_integration.py` YANLIŞLIKLA listeye dahil edilmemişti.
   Bu dosya `DATABASE_URL` değil **`DATABASE_URL_DASHBOARD`**'a göre
   `skipif` yapıyor (farklı bir env değişkeni) — WSL container'ının
   `.env`'inde bu tanımlı olduğundan, dosyanın 3 testi SESSİZCE
   ATLANMADI, **gerçekten canlı Supabase Auth'a karşı çalıştı ve
   geçti** (doğrudan doğrulandı: `test_giris_yap_yanlis_kimlik_
   bilgisiyle_none_doner`, `test_rol_baglantisi_ac_sentetik_claim_ile_
   dogru_rolu_uygular`, `test_rol_baglantisi_ac_admin_claim_ile_tum_
   veriye_erisir` — 3/3 PASSED). **Sonuç:** önceki "230 passed" rakamı
   SAYI olarak doğruydu ama "tamamen yerel/offline" çerçevelemesi tam
   doğru değildi — 227'si gerçekten yerel, 3'ü (rollback-izolasyonlu,
   zararsız ama GERÇEK) canlı Supabase Auth çağrısıydı. Bu doküman
   §9.4'te bu nüansı düzeltilmiş hâliyle yansıtır.

---

## Ek A: Kaynak Dosya Envanteri

| Kategori | Sayı | Detay |
|---|---|---|
| Git commit | 141 | 2026-08-18 → 2026-09-07 |
| Migration | 25 | `supabase/migrations/20260819_0001` → `20260905_0002` |
| ci-only SQL | 2 | `00_auth_stub.sql`, `01_roles_bootstrap.sql` |
| `worker/*.py` (üst düzey) | 11 | `analytics, auth, db, dogrula, ingest, job_worker, kpi, parser, pipeline, validate_rls_static, validate_role_access` |
| `worker/jobs/*.py` | 1 | `fetch_weather.py` |
| `worker/scripts/*.py` | 15 | `word_ortak.py` + `word_2016..2025.py` (10) + `backfill.py`, `onayla.py`, `toplu_onayla_word.py`, `mutabakat_ulke_geneli.py` |
| `app/*.py` | 1 | `dashboard.py` |
| Test dosyası | 25 | `worker/tests/*.py` (6 `*_integration.py` + 19 unit/regresyon) |
| Test fonksiyonu | 248 tanım / 227 (19 non-integration dosya TEK BAŞINA) / 276 (tüm 25 dosya) | bkz. §9.4 — 230, yalnız bu oturumun bir WSL koşusuna özgü (227+3) bir rakam |
| GitHub Actions workflow | 4 | `ci.yml`, `security.yml`, `deploy.yml`, `scheduled-refresh.yml` |
| `dokumanlar/*.md` (bu dosya hariç) | 11 | `00_INDEX` → `09_PROJE_DURUMU` |
| Fact tablosu | 7 | `fact_tuketim`, `fact_uretim`, `fact_abone`, `fact_serbest_tuketici`, `fact_hava_aylik(+log)`, `fact_tuketim_ulke_geneli` |
| Dim tablosu | 5 | `dim_tarih`, `dim_il`, `dim_kaynak`, `dim_tuketici_grubu`, `dim_lisans` |
| KPI (Faz 0-3 production) | 20 | KPI-01..13, 23..27 (KPI-14..22 SRS'te tanımlı değil/bu repoda hiç geçmiyor) |

