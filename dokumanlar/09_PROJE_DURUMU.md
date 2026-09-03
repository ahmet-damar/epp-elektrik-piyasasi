# EPP — Proje Durum Raporu (2026-09-03)

**Amaç:** Bu dosya tek başına okunduğunda projenin GÜNCEL durumunu anlatır.
`dokumanlar/SABAH_OZETI.md` tek bir gece-turu dizisinin (2016-2022 Word
aktarımı) notu olarak yazılmıştı ve artık projenin tamamını temsil etmiyor —
bkz. `00_INDEX.md`'deki not. Bu rapor **canlı Supabase DB'sine karşı
SALT OKUNUR sorgularla** ve repo'nun tam commit geçmişiyle (96 commit,
`2943fb7`'den `c70fc8c`'ye) çapraz doğrulanarak yazıldı — hangi kısmın
nereden geldiği için bkz. §4.

---

## 1. TAMAMLANAN İŞLER

### 1.1 Mimari iskelet (Faz 0/1)

Yıldız şema (`dim_tarih/il/kaynak/tuketici_grubu/lisans` + `fact_tuketim/
abone/uretim/serbest_tuketici/hava_aylik`), `source_asset`/`ingestion_batch`/
`is_active` sürümleme (P0-2..P0-5), RLS (`viewer/data_operator/admin` +
`current_app_role()`), asenkron `job_worker.py` (Postgres-only kuyruk,
`FOR UPDATE SKIP LOCKED`) — commit `2943fb7`'den `cbbd766`'ye (Faz 0/1).
**15 migration** (`supabase/migrations/20260819_0001..0015`) canlı Supabase
projesine uygulı durumda (DB'den doğrulandı — şema sorguları başarıyla
çalıştı).

### 1.2 Excel dönemi — 2026 canlı veri

`worker/parser.py` (openpyxl, gerçek EPDK `.xlsx` dosyasına karşı yazıldı,
commit `c518734`) 2026'nın kaynak formatı. **DB'den doğrulandı:** 2026 Ocak-
Haziran (6 ay) — T11/T10/T4/T1/T13'ün **TAMAMI yüklü VE aktif** (6/6 her
tabloda). Faz 1 asenkron worker + P0-4 aktivasyon + P0-5 batch versiyonlama
production'da (commit `3d351dd`, `cbbd766`). Şubat-Haziran 2026 arasında
EPDK'nın kendi şablonu bir kez değişti (T11 kümülatif→aylık türetme +
T13 kolon kayması, commit `05cb608`/`3248bfe`) — elle bulunup düzeltildi,
detay `06_canli_veri_operasyon_gunlugu.md`.

### 1.3 Word aktarımı — 2016-2025 (tek seferlik tarihsel aktarım)

Mimari karar (07 belgesi, 2026-08-31): docx parser'ı `worker/parser.py`'a
KALICI bir dal olarak eklenmedi — her yıl kendi `worker/scripts/word_YYYY.py`
tarifini taşıyor, ortak çekirdek `worker/scripts/word_ortak.py`
(`basliklari_topla`/`tek_aday_bul`/`t4_tablosunu_bul`/
`hedef_donem_kolonu_bul`). **10 yıl (2016-2025) için 10 ayrı script var**
(DB'den ve dosya sisteminden doğrulandı — bkz. §2 aktivasyon tablosu):

| Yıl | T11 (tüketim) | T10 (abone) | T4 (lisanssız güç) | Kaynak |
|---|---|---|---|---|
| 2025 | 12/12 yüklü, **aktif** | 12/12, **aktif** | 12/12, **aktif** | tek şablon |
| 2024 | 12/12, **aktif** | 12/12, **aktif** | 12/12, **aktif** | tek şablon (1 başarısız deneme, idempotency bug, düzeltildi) |
| 2023 | 12/12, **aktif** | 12/12, **aktif** | 12/12, **aktif** | 2 iç şablon (Ocak-Nisan / Mayıs-Aralık) |
| 2022 | 12/12, running | 12/12 yüklü, running | 11/12, running (Temmuz kapsam_disi — kaynak hatası) | 2 iç şablon (Ocak-Nisan eski taksonomi) |
| 2021 | 12/12, running | 2/12 yüklü (Kas-Ara), running; Oca-Eki kapsam_disi | 12/12, running | il-only→il×grup geçişi Kasım'da |
| 2020 | 12/12, running | 0/12 (tüm yıl kapsam_disi — il-only) | 12/12, running | kapak-paragrafı ay/yıl çapası |
| 2019 | 12/12, running | 0/12 (kapsam_disi — il-only) | 12/12, running | Güneş 2-kolon ayrımı |
| 2018 | 12/12, running | 0/12 (kapsam_disi — il-only) | 12/12, running | "BOŞ-VERİ-ŞEHİR" anomali satırı |
| 2017 | 12/12, running | 0/12 (kapsam_disi — il-only) | 12/12, running | sayfa-sonu başlık tekrarı |
| 2016 | 12/12, running (Temmuz/Adana Genel Toplam'dan türetildi) | 0/12 (kapsam_disi — tablo hiç yok) | 12/12, running | İstanbul'un bazı aylarda ikiye bölünmesi |

T1 (Lisanslı kurulu güç) ve T13 (Serbest Tüketici) **2016-2025'in TAMAMINDA
kaynakta yok** — Karar 3/Karar 1 ile `veri_kapsam_disi`'ye işaretli (aşağıya
bkz.), hiç yüklenmedi (yüklenecek bir kaynak da yok).

**"running" = yüklendi ama `onayla.py` ile hiç aktive edilmedi** (bkz. §2 —
bu, 2016-2022'nin TEK ve en büyük açık işi).

### 1.4 Taksonomi / kapsam kararları

- **Karar 1 (T13 kapsam dışı):** Word döneminde Serbest Tüketici tablosu hiç
  yok. `veri_kapsam_disi` ile işaretli, **DB'den doğrulandı: 120 satır**
  (`fact_serbest_tuketici`, `(tumu)`, 2016-2025 × 12 ay).
- **Karar 2 (Sanayi/`baglanti` kapsam dışı, yalnız `fact_tuketim`):** Word
  kaynağı Sanayi-İletim/Dağıtım ayrımını vermiyor; Sanayi grubu Word
  dönemlerinde `fact_tuketim`'e hiç yüklenmiyor (diğer tablolarda ETKİLENMEZ
  — `fact_abone` Sanayi dahil, 405 satır/ay ile Mart 2024'te doğrulandı).
- **Karar 3 (T1 kapsam dışı):** Word döneminde Lisanslı kurulu güç için
  il×kaynak birleşik tablo yok. `veri_kapsam_disi`'de **DB'den doğrulandı:
  120 satır** (`fact_uretim`, `lisans_durumu=Lisanslı`, 2016-2025 × 12 ay)
  + Temmuz 2022'nin T4 (Lisanssız) kaynak hatası için **1 ek satır**
  (`lisans_durumu=Lisanssız`, 2022) — **toplam `veri_kapsam_disi`: 311
  satır** (DB'den sayıldı).
- **Taksonomi RENAME kararı (2021/2022/2016-2020):** "Ticarethane"→"Kamu ve
  Özel Hizmetler", "Tarımsal Sulama"→"Tarımsal" — 2023-2025'in kanonik
  "Tarımsal" grubunun gerçek mevsimsellik verisiyle (Mart→Mayıs oranları)
  doğrulandı, kod alias'ıyla uygulandı (`worker/parser.py:GRUP_ESLEME`
  DEĞİŞMEDİ — yalnız her yılın kendi script'inde alias).
  **`veri_kapsam_disi`'de İSTİSNAİ satır bazlı çözümler** (şema/genel karar
  DEĞİL, yalnız o ayın kendine özgü kaynak kusuru): Temmuz 2016/Adana
  (T11 türetme, `c70fc8c`), Temmuz 2022 T4 (kapsam_disi), Ağustos/Eylül
  2018 "BOŞ-VERİ-ŞEHİR" anomali satırı (atlandı).

### 1.5 KPI katmanı

- **Faz 0 production:** KPI-01..10, 13, 23, 24 (P0-6).
- **Faz 3 production (2026-08-30, commit `76059b7`/`a138f8b`/`99ac617`):**
  KPI-11 (arındırılmış tüketim, β/γ OLS regresyon) + KPI-12 (norm sapması) —
  hava normalizasyonu, `worker/jobs/fetch_weather.py` (Open-Meteo) +
  `scheduled-refresh.yml`.
  **DB'den doğrulandı:** `fetch-weather-1` parser_version'ından **1
  `succeeded` batch** var (hava verisi UPSERT modeli, `is_active`/batch-
  versiyonlama YOK — `fact_hava_aylik_log` append-only JSONB).
- **KPI-25/26/27 (2026-09-02/03 düzeltildi):** KPI-25 (tüketim CAGR) ve
  KPI-26 (yenilenebilir kurulu güç CAGR) Word/Excel dönemleri arasındaki
  kapsam farkları (Sanayi dahil/hariç, Lisanslı var/yok, tam/kısmi yıl)
  yüzünden sahte sonuç üretiyordu — ikisi de artık yalnız KARŞILAŞTIRILABİLİR
  yılları seriye alıyor, yetersizse `None`/"hesaplanamaz" (sahte sayı
  ÜRETİLMİYOR). Yeni **KPI-27** (Sanayi-hariç tüketim CAGR, KPI-25'in
  YERİNE GEÇMEZ) eklendi — canlı veride 2023→2025 için **+%6,9**.
  Kod: `worker/analytics.py`, sözleşme: `04_kpi_sozlesmeleri.md`.

### 1.6 Test/CI durumu

**Bu turda gerçekten çalıştırılarak doğrulandı** (bkz. §4 — canlı DB
integration testleri README Ek D kuralı gereği BURADA çalıştırılmadı, CI
loglarından okundu):
- `worker/tests/` toplam **194 test dosyası-fonksiyonu**, hepsi PASS:
  - **154 test** bu turda yerelde çalıştırıldı (entegrasyon olmayan 14
    dosya: `test_word_2016..2022.py` [7×, 72 test], `test_parser.py`,
    `test_ingest_unit.py`, `test_golden.py`, `test_kpi_faz3.py` [1 test
    hariç], `test_fetch_weather.py`) — **hepsi geçti.**
  - **1 test** (`test_kpi_faz3.py::test_beta_gamma_tahmin_et_bilinen_
    dogrusal_iliski`) bu makinede `numpy.linalg.lstsq` üzerinde native bir
    çökmeye (Windows fatal exception) neden oluyor — **yerel-ortam kısıtı**
    (bu oturumda zaten bilinen pandas/mypy SAC engelleme ailesiyle aynı
    kökten, conda-forge/Windows'a özgü); CI'nin Linux runner'ında (commit
    `c70fc8c`, 2026-09-03) **PASSED** olarak doğrulandı.
  - **39 test** (5 entegrasyon dosyası: `test_ingest_integration.py`,
    `test_pipeline_integration.py`, `test_job_worker_integration.py`,
    `test_analytics_integration.py`, `test_fetch_weather_integration.py`)
    canlıya karşı BURADA çalıştırılmadı (`README.md` "Canlı Supabase'e
    Karşı Test Çalıştırma Kuralı") — CI'nin aynı `c70fc8c` çalışmasında,
    disposable `postgres:16` container'ına karşı **hepsi PASSED**.
- **`ruff check`/`ruff format --check`:** temiz (repo geneli, bu turda
  çalıştırıldı).
- **`mypy` (`app worker`):** bu makinede pandas'la AYNI Windows Akıllı
  Uygulama Denetimi kısıtı yüzünden yerelde çalıştırılamıyor — CI'nin
  `c70fc8c` çalışmasında **"Success: no issues found in 42 source files."**
- **Eksik test kapsamı (hâlâ geçerli, 07 belgesinden devralındı, bu turda
  dosya sistemi taramasıyla TEYİT edildi):** `word_2023.py`/`word_2024.py`/
  `word_2025.py` için DEDİKE regresyon testi YOK (`worker/tests/` içinde
  `test_word_2023/2024/2025.py` dosyası bulunmuyor) — yalnız script-içi
  assertion'lara (81 il, Genel Toplam tutarlılığı) güveniliyor.
  `word_2016.py`..`word_2022.py`'nin YEDİSİ İÇİN test dosyası VAR (72 test).

### 1.7 Mimari kararlar (ADR'ler)

- **ADR-6:** Uygulama bileşenleri OSI açık kaynak (GitHub Actions/GHCR
  yönetilen-servis istisnası hariç).
- **ADR-7 (`06_adr_dashboard_teknoloji.md`, 2026-08-30):** Sunum katmanı
  Streamlit (Faz 2) — Next.js+TypeScript'e geçiş İPTAL EDİLMEDİ, "Son Faz"
  (LinkedIn yayını) öncesine ertelendi. Bilinen kısıt: `worker/analytics.py`
  `DATABASE_URL` üzerinden RLS'ten muaf bağlıyor (tek-kullanıcılı Faz 2
  kapsamında kabul edilebilir, çok-kullanıcılı erişimden ÖNCE çözülmeli —
  Supavisor transaction-mode pooler `SET ROLE`'ü reddediyor).
- **ADR-8 (terk edildi, 2026-08-31 kayıt altına alındı):** RLS'i tamamen
  `authenticated`+`current_app_role()` moduna taşıyan alternatif tasarım
  kısmen başlanıp bırakıldı — mevcut `viewer/data_operator/admin` mimarisi
  zaten yeterli olduğu canlı Supabase'de doğrulandığından gerek kalmadı.

---

## 2. AKTİVASYON DURUMU

**Bu bölüm DB'den TAZE sorgulanarak üretildi (2026-09-03), en çok karışan
nokta olduğu için özellikle vurgulanıyor.**

| Yıl | T11 yüklü/aktif | T10 yüklü/aktif | T4 yüklü/aktif | T1 yüklü/aktif | T13 yüklü/aktif |
|---|---|---|---|---|---|
| 2016 | 12/**0** | 0/**0** (12 kapsam_disi) | 12/**0** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2017 | 12/**0** | 0/**0** (12 kapsam_disi) | 12/**0** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2018 | 12/**0** | 0/**0** (12 kapsam_disi) | 12/**0** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2019 | 12/**0** | 0/**0** (12 kapsam_disi) | 12/**0** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2020 | 12/**0** | 0/**0** (12 kapsam_disi) | 12/**0** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2021 | 12/**0** | 2/**0** (10 kapsam_disi) | 12/**0** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2022 | 12/**0** | 12/**0** | 11/**0** (1 kapsam_disi) | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2023 | 12/**12** | 12/**12** | 12/**12** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2024 | 12/**12** | 12/**12** | 12/**12** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2025 | 12/**12** | 12/**12** | 12/**12** | 0/**0** (12 kapsam_disi) | 0/**0** (12 kapsam_disi) |
| 2026 | 6/**6** | 6/**6** | 6/**6** | 6/**6** | 6/**6** |

**Okuma notu:** "yüklü" = fact tablosunda o tarih_id için satır var (aktif
olsun olmasın). "0 yüklü (N kapsam_disi)" = kaynakta gerçekten yok, açıkça
işaretli — bu bir eksiklik/hata DEĞİL. Boş hücre (0/0, kapsam_disi notu
YOK) hiçbir yıl-tablo kombinasyonunda YOK — **DB'den doğrulandı: 2016-2026
arası, T1/T4/T10/T11/T13'ün HİÇBİR ay-tablo kombinasyonu tamamen
dokunulmamış durumda değil** (ya yüklü ya da kapsam_disi).

**AÇIKÇA belirtiliyor (kritik nokta):**
- **0 batch yanlışlıkla aktive edilmiş DEĞİL** — hiçbir 2016-2022 batch'i
  `is_active=true` değil, DB'den doğrulandı (`fact_tuketim`/`fact_abone`/
  `fact_uretim`'de 2016-2022 için `is_active=true` satır sayısı: **0**).
- **2016-2022'nin TAMAMI (167 batch — DB'den sayıldı: `parser_version LIKE
  'word-20%'` VE yıl 2016-2022, hepsi `status='running'`) aktivasyon
  BEKLİYOR** — bu, `onayla.py`'nin BİLİNÇLİ OLARAK hiç çağrılmamasının
  (kesin kural, "gece-boyu gözetimsiz çalışma" disiplini) doğrudan sonucu,
  bir hata DEĞİL.
- **2023, 2024, 2025, 2026 TAMAMEN aktif** — 42 batch (`fact_tuketim`/
  `fact_abone` için ortak) + 36 T4 batch'i (`53-88` aralığı, 2026-09-02'de
  aktive edildi) + 2026'nın 6 Excel batch'i, hepsi DB'den doğrulandı.
  Bunların aktive EDİLMESİ GEREKİP EDİLMEDİĞİ sorusu YOK — zaten aktif ve
  aktif olmaları doğru (2024'ün 1 `failed` batch'i hariç — bilinen bir
  idempotency-bug denemesi, zararsız, aynı ay başka bir batch'le
  başarıyla tamamlandı).

---

## 3. GERİYE KALANLAR (somut, aksiyon alınabilir)

1. **Aktivasyon kararı — 2016-2022, 167 batch (T11/T10 + T4).** Ahmet'in
   `worker/scripts/onayla.py --batch-id <id>` (ya da toplu) ile gözden
   geçirip aktive etmesi gerekiyor. Bu YAPILMADAN 2016-2022 verisi
   dashboard'da GÖRÜNMEZ (yalnız `is_active=true` satırlar raporlanır).
2. **Kırmızı/red satırların örneklem doğrulaması — 2016-2022 için hâlâ
   YAPILMADI.** 68 batch, 161 red satırı (kpi.dogrula_tuketim() reddi,
   tümü negatif "Tarımsal"/"Aydınlatma" değeri) + 30 "atlanan" (boş
   hücre, il/grup detayı kayıtlı değil) — tam liste `SABAH_OZETI.md`'de.
   2023/2024/2025'in kendi red satırları AKTİVASYONDAN ÖNCE DB'den
   sorgulanarak teyit edilmişti (07 belgesi) — 2016-2022 için bu adım
   henüz atılmadı.
3. **Testsiz kalan alan — hâlâ geçerli:** `word_2023.py`/`word_2024.py`/
   `word_2025.py` için dedike pytest regresyon testi YOK (dosya sistemi
   taramasıyla bu turda teyit edildi — `worker/tests/test_word_2023/2024/
   2025.py` yok). `word_2016..2022.py`'nin YEDİSİ İÇİN test VAR (72 test).
4. **Bilinen ama düzeltilmemiş kaynak-veri kusurları** (uydurulmadı,
   `veri_kapsam_disi` ile işaretlendi — düzeltme GEREKMİYOR, yalnız
   bilgi amaçlı):
   - Temmuz 2022 T4 — o ayın "İllere ve Kaynaklara Göre Dağılım" tablosu
     bir önceki ayın (il-only) birebir kopyası, kaynakta kalıcı olarak
     elde edilemez.
   - Ağustos/Eylül 2018 T4 — "BOŞ-VERİ-ŞEHİR" adlı, hiçbir gerçek
     il_kodu'na eşlenemeyen fazladan bir satır (küçük değer, atlandı).
   - 2016-2022'nin 30 "atlanan" (boş hücre) satırı — özellikle 2017'nin
     11/12 ayı ve 2018'in 10/12 ayı, il/grup detayı KAYDEDİLMEMİŞ
     (gözlemlenebilirlik boşluğu, madde 2'yle aynı kök).
5. **T1 (Lisanslı kurulu güç), T13 (Serbest Tüketici) — 2016-2025'in
   TAMAMINDA kalıcı olarak kaynakta yok** (Karar 1/Karar 3, bkz. §1.4) —
   bu bir "geriye kalan iş" DEĞİL, kapanmış bir karar; yalnız KPI-25/26'nın
   bu yılları neden dışladığını hatırlatmak için burada tekrar not edilir.
6. **Faz 2 dashboard'u `veri_kapsam_disi`'yi henüz TÜKETMİYOR** — 311
   satırlık kapsam-dışı bilgisi kullanıcıya UI'da hiç yansımıyor (07/03
   belgelerinde önceden not edilmiş, hâlâ açık).
7. **RLS/Supavisor pooler uyumsuzluğu (ADR-7 notu)** — çok-kullanıcılı
   erişime geçilmeden ÖNCE çözülmesi gereken bir mimari kısıt, şu an
   Faz 2'nin tek-kullanıcılı kapsamında sorun değil.

---

## 4. BU RAPORUN GÜVENİLİRLİK NOTU

**Bu turda CANLI Supabase'e karşı gerçekten sorgulanarak doğrulandı**
(yalnız SELECT/COUNT, hiçbir yazma yapılmadı):
- §2'deki TÜM aktivasyon tablosu (`dim_tarih` × `fact_tuketim`/
  `fact_abone`/`fact_uretim` [lisans_id ile T1/T4 ayrımı] × `is_active`).
- `veri_kapsam_disi`'nin TAMAMI (311 satır, tablo/nitelik/yıl kırılımı).
- `ingestion_batch`'in TAMAMI (253 satır, `parser_version`/`status`
  kırılımı) — 167 running (2016-2022), 1 failed (2024), 80 succeeded.
- §1.6'daki test sonuçları (154 test yerelde çalıştırıldı; 39 entegrasyon
  testi + 1 numpy testi CI'nin `c70fc8c` çalışmasının LOG'undan okunarak
  doğrulandı — CI'da tekrar çalıştırılmadı, yalnız en son yeşil çalışmanın
  kaydı okundu).
- `mypy`/CI durumu — aynı şekilde `c70fc8c`'nin CI log'undan okundu.

**Yalnızca önceki `.md` dosyalarından/commit mesajlarından DEVRALINDI,
bu turda yeniden doğrulanmadı** (okuyucu bunlara "muhtemelen doğru, ama
bu raporun kendi kanıtı değil" gözüyle bakmalı):
- §1.4'teki taksonomi mevsimsellik doğrulaması (2023-2025 Mart→Mayıs
  oranları) — sayılar `SABAH_OZETI.md`/`08` belgesinden alındı, bu turda
  DB'ye karşı yeniden hesaplanmadı.
- §1.5'teki KPI-27 "+%6,9" değeri — `04_kpi_sozlesmeleri.md`'den alındı
  (2026-09-03 tarihli, bu rapor da aynı gün yazıldığından muhtemelen hâlâ
  geçerli, ama bu turda `worker/analytics.py` fonksiyonu yeniden
  çağrılmadı).
- 2023/2024/2025'in kırmızı satırlarının aktivasyon-öncesi çapraz
  doğrulandığı iddiası (§3 madde 2) — `07_word_parser_kapsam.md`'nin
  kendi anlatımına dayanıyor, bu turda o dönemin audit_log'u TEK TEK
  yeniden okunmadı (yalnız o dönemin batch'lerinin ŞU AN aktif olduğu
  DB'den doğrulandı — aktivasyon KARARININ isabetliliği değil, aktivasyon
  DURUMU bu turun kanıtı).
- §1.1-1.3, §1.7'deki commit hash'leri `git log --oneline`'dan (bu turda
  gerçekten çalıştırıldı) alındı — ama her commit'in İÇERİĞİ tek tek
  `git show` ile incelenmedi, yalnız commit mesajları ve ilgili `.md`
  dosyalarındaki anlatımlar eşleştirildi.

**Hiç doğrulanmayan/dışarıda bırakılan:** `app/dashboard.py`'nin ŞU AN
gerçekten çalışıp çalışmadığı (Streamlit sunucusu bu turda başlatılmadı);
Open-Meteo API'sinin şu an erişilebilir olup olmadığı; `db/schema.sql`'in
canlı DB şemasıyla bire bir aynı olup olmadığı (migration dosyaları
listelendi, şemanın kendisi `information_schema` üzerinden yalnız
ihtiyaç duyulan tablolar için sorgulandı, tam bir şema diff'i yapılmadı).
