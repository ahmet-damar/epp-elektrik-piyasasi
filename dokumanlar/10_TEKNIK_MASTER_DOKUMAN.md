# EPP — Teknik Master Doküman

> **STATUS: LIVE (güncel durum) + MASTER (üst özet)** — bu dosya ve
> `09_PROJE_DURUMU.md`, değişen sayı/durumun YAŞADIĞI tek iki yerdir;
> diğer `dokumanlar/` dosyaları yalnız değişmeyen sözleşmeyi tutar
> (2026-09-07 denetimi — bkz. "Doküman Yönetim Kuralı" bölümü, aşağıda).

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

## Doküman Yönetim Kuralı ("D kuralı", 2026-09-07 denetiminden)

**Değişen durum ve sayılar YALNIZ `09_PROJE_DURUMU.md` ve bu dosyada
(`10_TEKNIK_MASTER_DOKUMAN.md`) yaşar.** Diğer `dokumanlar/` dosyaları
ya değişmeyen bir sözleşmeyi tutar (**STATUS: ACTIVE**) ya da geçmişte
yazılmış bir olay günlüğüdür (**STATUS: HISTORICAL**, append-only —
güncel durum için asla okunmaz, yalnız o anın kaydı olarak durur).

**Tarih çapası şartı (2026-09-08'de eklendi):** HISTORICAL veya LIVE bir
dosyaya yazılan HER rakam ve durum ifadesi, yazıldığı anda tarihe
çapalanmalıdır — "2026-09-03 itibarıyla +%6,9" gibi, yalnız "+%6,9"
değil. Çapasız yazılan bir rakam, aylar sonra hâlâ güncelmiş gibi
okunur ve ayrı bir temizlik turu gerektirir. Güncel değer HER ZAMAN
`09_PROJE_DURUMU.md` veya bu dosyadan okunur, başka hiçbir dosyadan
değil — HISTORICAL bir dosyadaki tarihli bir rakam yalnız "o tarihte
neydi" sorusuna cevaptır, "şu an ne" sorusuna değil.

**Gerekçe:** 2026-09-08'deki bir tarama, D kuralının kendisinin (STATUS
etiketleri) tek başına yetmediğini gösterdi — HISTORICAL dosyalarda
meşru olarak kalan ama tarihe çapalanmamış 4 rakam/durum ifadesi
(`07_word_parser_kapsam.md`'deki "+%6,9" dahil), aylar sonra güncel
sanılıp ayrıca düzeltilmek zorunda kaldı. Bu madde geriye dönük bir
temizlik ZORUNLULUĞU GETİRMEZ (mevcut çapasız rakamlar olduğu gibi
kalabilir) — yalnız BUNDAN SONRA HISTORICAL/LIVE dosyalara yazılacak
her yeni rakam için geçerlidir.

## Sürüm Geçmişi

| Sürüm | Tarih | Değişiklik | Doğrulama kapsamı |
|---|---|---|---|
| v1.0 | 2026-09-07 | İlk yazım | 141 commit (2026-08-18→09-07), 25 migration + 2 ci-only, 11 worker/*.py + 10 yıllık word_20XX.py + 5 diğer script, 25 test dosyası (248 `def test_`, 230 pytest ID non-integration / 276 tüm dosyalar), 4 GitHub Actions workflow, 11 mevcut `dokumanlar/` dosyası, canlı Supabase (RLS/GRANT) doğrudan sorgulandı |
| v1.1 | 2026-09-07 | §9.4/Ek A test sayısı düzeltmesi | v1.0'ın "230 pytest ID non-integration" rakamı YANLIŞTI — temiz bir kabukta (`env -i`, `.env` erişilemez) doğrudan doğrulandı: 19 unit/regresyon dosyası TEK BAŞINA **227** ID veriyor (`skipif` toplamayı değil çalıştırmayı engelliyor, bu iki kavramın karışması hataya sebep olmuştu). 230, bu oturumun WSL koşusuna ÖZGÜ bir rakam (227 yerel + 3 gerçek `test_auth_integration.py` çağrısı) — genel/ortam-bağımsız bir sabit DEĞİL |
| v1.2 | 2026-09-07 | 13 dokümanlık dış denetim (ChatGPT/Gemini/Sonnet analizleriyle çapraz) — §4.2/§4.3/§14.1 (T8'in "düzeltmesi" geri alındı, T8 de T12 gibi parse edilmiyor), §7.5 (KPI-28 numara çakışması notu), §12.4 (`prepare_threshold` notu eklendi), tüm "2026-09-08" tarihleri "2026-09-07"ye düzeltildi (git log'a karşı doğrulandı — commit `ecba6b5` dahil hepsi 09-07) | `grep -rn "T8" worker/parser.py worker/pipeline.py`, `grep -rn "KPI-28" worker/`, `git log --format='%cd' --date=iso` (tüm commit'ler 2026-09-07); ayrıca `05_kaynak_dosya_sozlesmesi.md`, `03_veri_modeli.md`, `01_kavramsal_tasarim.md`, `00_INDEX.md`, `.github/copilot-instructions.md`, `09_PROJE_DURUMU.md` bu turda düzeltildi (bu dosyanın kapsamı dışı, kendi commit'lerinde ayrı listelenir) |
| v1.3 | 2026-09-07 | Aşama 1 (operasyonel güvenlik) başladı — C2: `worker/tests/conftest.py` ile prod DB'ye karşı test guard'ı KOD SEVİYESİNDE eklendi, §9.4'e not düşüldü | Sahte `pooler.supabase.com` URL'i ile pytest exit code 3 ile durduruldu; aynı URL + `ALLOW_DESTRUCTIVE_TESTS=true` ile 276 test normal toplandı; DB env'siz 227 test hatasız koştu (regresyon yok) |
| v1.4 | 2026-09-07 | B2: `ci.yml`'in `integration` job'ı artık `deploy.yml` ile AYNI glob mantığını kullanıyor + uygulanan/toplam migration sayısı karşılaştırması eklendi (§9.1/§9.3) | Gerçek CI koşusu (run 34157349173): sahte bir migration dosyası hiçbir listeye eklenmeden glob'a yakalandı, kendi `RAISE NOTICE`'ı loga düştü, `Uygulanan: 26 / Toplam dosya: 26` doğrulaması geçti; test dosyası sonraki commit'te geri alındı |
| v1.5 | 2026-09-07 | C1: `worker/scripts/backup.py` + `dokumanlar/11_yedekleme_runbook.md` eklendi (§8.5) — Supabase Free plan'de otomatik yedek YOK | Gerçek disaster-recovery drill'i (disposable postgres:17, WSL/Docker): migration'lardan şema + `pg_restore --data-only` ile veri geri yüklendi, 19/19 tablo canlı Supabase'in `COUNT(*)` değerleriyle birebir eşleşti, 0 hata (ikinci denemede — ilk denemedeki 6 seed-tablosu hatası `--exclude-table` ile düzeltildi) |
| v1.6 | 2026-09-07 | C3: `worker/jobs/fetch_weather.py:main()` 0 satır yazılırsa FAIL ediyor + `scheduled-refresh.yml`'e `if: failure()` özet adımı eklendi (§9.3) | `yaml.safe_load` ile sözdizimi doğrulandı, ruff/mypy temiz; GitHub'ın scheduled-workflow bildirim davranışı resmi dokümantasyondan doğrulandı (cron'u oluşturan kullanıcıya gider — `git log` ile bu proje için repo sahibi olduğu teyit edildi), kişisel bildirim AÇIK mı kod seviyesinde doğrulanamadığı için elle teyit gerektiği not edildi |
| v1.7 | 2026-09-07 | C4: 8 tabloda (`dim_*`×5 + `sistem_parametre`/`kpi_esik`/`job_status`) RLS geri açıldı (§8.2), istisnasız tamlık kontrolü eklendi, **canlıya uygulandı** | Disposable postgres:16 + GERÇEK CI (run 34159706854 pozitif, 34159900787 negatif/fake-tablo-fail, 34160105007 revert-sonrası yeşil) + canlı Supabase'in tümünde doğrulandı: 19/19 tablo RLS+policy, dashboard yolu (viewer/data_operator/admin) gerçek JWT ile test edildi, `postgres` rolünün `rolbypassrls=true` olduğu canlıda teyit edildi (varsayılmadı) |
| v1.8 | 2026-09-08 | Aşama 1 kapanışı — `scheduled-backup.yml` (haftalık pg_dump, §8.5), `app_dashboard_service` için `idle_in_transaction_session_timeout=30min` **canlıya uygulandı** (§8.2, C4 olayının tekrarına karşı) | idle timeout: disposable postgres:16'da 27/27 migration + canlıda `pg_roles.rolconfig` doğrulandı, kısa-timeout testiyle (2s) gerçek `IdleInTransactionSessionTimeout` kanıtlandı, normal ardışık kullanım etkilenmedi. `scheduled-backup.yml`: YAML doğrulandı, CI yeşil — **gerçek bir koşu henüz doğrulanamadı** (`gh` token'ının `workflow` izni yok, 403); açık madde olarak sonraki oturuma bırakıldı |
| v1.9 | 2026-09-08 | `scheduled-backup.yml` gerçek koşuyla UÇTAN UCA doğrulandı (§8.5/§9) — 2 gerçek CI hatası bulunup düzeltildi (pg_dump sürüm uyumsuzluğu + PATH sırası) | Üçüncü koşu (run 34192746673) başarılı: dump 1.61 MB, artifact indirilip `pg_restore --list` ile içeriği incelendi, disposable postgres:17'ye (canlı Supabase'in kendi major sürümü — bkz. v1.10) restore edilip **19/19 tablo canlı Supabase'in `COUNT(*)` değerleriyle birebir eşleşti**; 100 KB eşiği ayrı bir koşuda (geçici 5 MB) GERÇEKTEN FAIL ettirilip `upload-artifact`'in atlandığı görüldü, sonra geri alındı (run 34193103617 nihai yeşil) |
| v1.10 | 2026-09-08 | Aşama 2/C5 — KPI-25 TAMAMEN `fact_tuketim_ulke_geneli`'ye taşındı (tam yıl+5/5 grup şartı), KPI-27 il bazlı `fact_tuketim`'de kaldı — §7.5/§11.2 (artık KAPANDI), `04_kpi_sozlesmeleri.md` güncellendi | Canlı veriyle doğrulandı: KPI-25 artık **+%3,1** (2017→2025, n=8 — önceden sürekli 'hesaplanamaz'dı, GERÇEK fonksiyonel değişiklik), KPI-27 **+%3,8** (2016→2025, n=9, kod değişmedi). 2 pytest testi (`test_yillik_serilerinden_cagr`, `test_kpi_25_eksik_yil_seriye_girmez`) yeni tabloya taşındı, canlıya karşı `-k` ile hedefli çalıştırılıp (rollback-izole) PASSED |
| v1.11 | 2026-09-08 | Aşama 2 — `app/dashboard.py`'nin idle-in-transaction KÖK NEDENİ düzeltildi (§8.2): bağlantı `autocommit=True`'ya alındı + ölü bağlantıyı sessizce yeniden kuran `_baglanti_saglikli_mi()`/reconnect mantığı eklendi | Canlıda GERÇEK testlerle kanıtlandı: `autocommit=True` ile 2s `idle_in_transaction_session_timeout`'tan 3s sonra ikinci sorgu SORUNSUZ çalıştı (hata hiç fırlamadı — `autocommit=False` ile AYNI test önceki turda hatayı gerçekten üretmişti); kasıtlı kapatılan bir bağlantı `_baglanti_saglikli_mi()` tarafından doğru tespit edilip saklanan JWT claim'iyle sessizce yeniden bağlandı |
| v1.12 | 2026-09-08 | C1 düzeltmesi — yedekleme runbook'undaki restore hedefi `postgres:16`'dan `postgres:17`'ye (canlı Supabase'in kendi major sürümü) düzeltildi, tatbikat yeniden koşuldu (§8.5) | Disposable postgres:17'ye restore: 19/19 tablo yine BİREBİR eşleşti, PG17'ye özgü `transaction_timeout` GUC uyarısı da (postgres:16 hedefte görülen) bu sefer HİÇ çıkmadı — 0 hata, 0 uyarı |
| v1.13 | 2026-09-08 | "Doküman Yönetim Kuralı" bölümü yazıldı (D kuralı artık yalnız STATUS etiketi değil, ayrı bir bölüm) + tarih çapası şartı eklendi — `.github/copilot-instructions.md`'ye de tek satır yansıtıldı | Gerekçe: aynı gün yapılan KPI-25/27 taramasında 4 çapasız/eskimiş rakam bulunmuştu (bkz. commit `d141a79`) — bu madde onun tekrarını önlemek için, geriye dönük temizlik ZORUNLULUĞU getirmiyor |
| v1.14 | 2026-09-08 | **Gün sonu kapanışı.** 13-dokümanlık dış denetimin TAMAMI (Aşama 0/1/2 + D kuralı tarih çapası) bu gün içinde kapandı — açık madde YOK. `09_PROJE_DURUMU.md`'nin "Sonraki Oturum Devam Noktası" bölümü yeniden yazıldı: bugünün özeti, C6'nın tam listesi, Faz 4 önerisi (Eskişehir pilotu + seasonal-naive baseline), ve bir sonraki oturumun ilk işi (2026-09-13 Pazar 03:00 UTC — `scheduled-backup.yml`'in İLK gerçek cron koşusunun kontrolü) | Yalnız doküman — kod/migration/canlı DB'ye dokunulmadı. pytest 227/227, CI+Security yeşil, git temiz |
| v1.15 | 2026-09-08 | Aşama 3 (boş KPI'ları aç) — ADIM 1 (T11-Genel-Toplam vs T7 tanım dikişi kontrolü) + ADIM 2 (`fact_tuketim_ulke_geneli` 2026+ Excel'e genişletildi, KPI-13 girdisi taşındı) — §5.5 | 6/6 ay (202601-202606) gerçek dosyaya karşı test edildi (4/6 birebir, 2/6 <%0,02 fark) — T11 seçildi, T7 değil. Canlıya 30 satır eklendi (629 toplam). Gerçek bir de-kümülatif bug'ı bulunup düzeltildi (regresyon testiyle). KPI-13 2026-06↔2025-06 için artık **+%7,1** (önceden hep 'hesaplanamaz'), eski il-bazlı yol hâlâ None (regresyon yok) — canlıda doğrulandı |
| v1.16 | 2026-09-08 | Aşama 3/ADIM 3 madde 1 — `fact_tuketim_ulke_geneli` batch bağımlılığı düzeltmesi (migration `20260908_0002`, `kumulatif_tuketim_mwh` kolonu + `tutarlilik_ulke_geneli_kumulatif.py`) — §5.6 | Disposable postgres:17'de 279/279 pytest + mevcut 30 satır sıfırdan yeniden işlenip canlıyla ondalık basamağa kadar eşleşti; simüle edilmiş bir "N-1 sonradan değişti" senaryosunda yeni script beklenen TEK satırı doğru yakaladı, başka yanlış pozitif yok. Canlıya migration + kolon backfill uygulandı (30/30), mutabakat (479/0 uyumsuz) ve yeni tutarlılık script'i (30/0 tutarsız) canlıda YEŞİL |
| v1.17 | 2026-09-08 | `worker/tests/conftest.py`'nin canlı-DB koruması, 2026-09-02'deki İLE BİREBİR AYNI sızıntı desenini (test kirliliği canlı Supabase'de) TEKRAR üretti (`.env`'in `load_dotenv()`'le kontrolden SONRA yüklenmesi yüzünden atlandı) — bulundu, canlı kirlilik temizlendi (85 fact + 3 batch + 3 source_asset + 1 dim_tarih), koruma kalıcı düzeltildi — bkz. `06_canli_veri_operasyon_gunlugu.md` 2026-09-08 (devam) kaydı | Düzeltme öncesi/sonrası CANLI olarak reprodüklendi: aynı senaryo düzeltme öncesi sessizce geçiyordu, sonrası `exit code 3` ile doğru durdu. Temizlik sonrası mutabakat (479/0) + tutarlılık (30/0) script'leri tekrar YEŞİL, 278/279 pytest (tek "hata" — canlı Auth'a bilerek bağımlı `test_auth_integration.py`'nin bu turda disposable DB'ye yönlendirilmiş olması, beklenen) |
| v1.18 | 2026-09-08 | **Gün sonu kapanışı (2).** Aşama 3 ADIM 1-2 (`1232cb3`) + ADIM 3 madde 1 (`df616e6`) bu gün içinde kapandı — ADIM 3 madde 2-4 + ADIM 4-5 AÇIK, HİÇBİRİNE başlanmadı. `09_PROJE_DURUMU.md`'nin "Sonraki Oturum Devam Noktası" bölümü güncellendi: sıradaki iş (ADIM 3 madde 2 — üretim tabloları) netleştirildi, `conftest.py` korumasının HÂLÂ kendi regresyon testi olmadığı (2026-09-02 ve 2026-09-08'de iki kez delinmiş bir koruma) açık madde olarak eklendi | Yalnız doküman — kod/migration/canlı DB'ye dokunulmadı. CI+Security yeşil, git temiz |
| v1.19 | 2026-09-09 | Gece çalışması (gözetimsiz) MADDE 0 — `worker/tests/test_conftest_guard.py` eklendi, `conftest.py`'nin canlı-DB koruması artık kendi pytest regresyon testine sahip (2026-09-02 ve 2026-09-08'de iki kez delinmişti) | Testin anlamlı olduğu (vacuous değil) kanıtlandı: `conftest.py` geçici olarak 2026-09-08 öncesinin buggy sürümüne döndürülüp aynı test suite'i çalıştırıldı — `.env`'den yükleme senaryosu (2026-09-08 bug'ının reprodüksiyonu) beklendiği gibi FAILED verdi, diğer iki senaryo PASSED kaldı; düzeltilmiş sürüm geri yüklenip 3/3 PASSED doğrulandı. Yalnız disposable/subprocess — canlı DB'ye hiç dokunulmadı |
| v1.20 | 2026-09-09 | Gece çalışması MADDE 1 — `fact_uretim_kaynak_geneli` + `fact_uretim_il_geneli` (migration `20260909_0001`), `fact_tuketim_ulke_geneli` ile AYNI desen, kümülatif DEĞİL — §5.7. **YALNIZ disposable postgres:17'de, CANLIYA UYGULANMADI** | Disposable postgres:17'de migration 29/29, RLS 21/21 tablo, role-access tamamen geçti, pytest 281/282 (tek beklenen "hata" — auth integration). sqlfluff temiz |
| v1.21 | 2026-09-09 | Gece çalışması MADDE 2 — T2/T3/T5/T6 Excel parser fonksiyonlarında GERÇEK bir hata bulunup düzeltildi: sabit kolon okuyordu (yalnız Ocak dosyasında doğruydu), artık `_ay_kolonu_bul()` ile doğru ay kolonunu buluyor — §5.8 | 6/6 gerçek dosyada (202601-202606) T2↔T3 ve T5↔T6 ONDALIK BASAMAĞA KADAR birebir eşleşti (Lisanslı/Lisanssız ayrı ayrı). Yeni regresyon testleri (her iki başlık stili, "komşu ay değeri sessizce dönmüyor" kontrolü). pytest 285/286 (tek beklenen "hata") |
| v1.22 | 2026-09-09 | Gece çalışması MADDE 3 — `worker/scripts/mutabakat_uretim.py`: il↔kaynak çapraz mutabakat, ±%0,5 tolerans, aktivasyonu engelleyen `periyot_aktivasyona_uygun_mu()` gate fonksiyonu — §5.9. **YALNIZ disposable postgres:17'de** | 4 yeni entegrasyon testi (kasıtlı uyumsuz veri gerçekten yakalandı, her iki batch bloklandı, gate fonksiyonu her iki yönde test edildi). Gerçek 6 aya karşı (parser çıktıları): 12/12 (6 ay × 2 lisans) birebir eşleşti |
| v1.23 | 2026-09-09 | Gece çalışması MADDE 4 — `fact_uretim_kaynak_geneli`/`fact_uretim_il_geneli` için tam yükleme altyapısı (`ingest`/`kpi`/`pipeline` fonksiyonları) + `backfill_uretim_excel.py` (mutabakat-gated aktivasyon) — §5.10. **YALNIZ disposable postgres:17'de, CANLIYA UYGULANMADI** | 6/6 ay gerçek dosyadan yüklendi, mutabakat 6/6 UYGUN, 6/6 aktive edildi (101+942 satır, hepsi aktif). mutabakat_uretim.py CLI'ı 12/12 uyumlu doğruladı. RLS/role-access veri sonrası da 21/21 YEŞİL. pytest 291/292 (tek beklenen "hata") |

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
| — | `fact_tuketim_ulke_geneli` (Sanayi dahil ülke geneli) | ✅ TAMAMLANDI (2026-09-07) |
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
| `fact_tuketim_ulke_geneli` | `(tarih_id, grup_id)` | `tuketim_mwh` | **il_kodu/baglanti YOK** — kaynağı T11'in Genel Toplam satırı, zaten il kırılımsız (2026-09-05, migration 20260905_0002). 2016-2025 (Word) + **2026+ (Excel, 2026-09-08'den beri — bkz. §5.5)** TEK tanımda |

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
Yazan tablo sayısı tam **5**'tir (T1/T4/T10/T11/T13) — "Hedef" kolonu tek
başına yanıltıcı olabildiği için bir **Durum** kolonu eklendi (bkz.
`05_kaynak_dosya_sozlesmesi.md`, aynı doğrulamayla senkron):

| Tablo | İçerik | Hedef | Durum |
|---|---|---|---|
| T1 | Lisanslı kurulu güç (il×kaynak) | `fact_uretim` | Parse edilir, **YAZAR** |
| T2/T3 | Lisanslı üretim (kaynak/il) | `fact_uretim` | Parse edilmez — il×kaynak kesişimi kaynakta yok |
| T4 | Lisanssız kurulu güç | `fact_uretim` | Parse edilir, **YAZAR** |
| T5/T6 | Lisanssız üretim (kaynak/il) | `fact_uretim` | Parse edilmez — T2/T3 ile aynı sebep |
| T7 | Faturalanan tüketim (tür, ülke geneli) | `fact_tuketim` | Parse edilir ama **YAZMAZ** — yalnız mutabakat |
| T8 | Faturalanan tüketim (il) | `fact_tuketim` | **Parse edilmez — T11 ile redundant** (bkz. §4.3) |
| T9 | Tüketici sayısı (tür, ülke geneli) | `fact_abone` | Parse edilir ama **YAZMAZ** — yalnız mutabakat |
| T10 | Tüketici sayısı (il) | `fact_abone` | Parse edilir, **YAZAR** |
| **T11** | **Tüketim (iletim/dağıtım!)** | **`fact_tuketim.baglanti`** (P0-2) | Parse edilir, **YAZAR** (+ Genel Toplam satırı → `fact_tuketim_ulke_geneli`) |
| T12 | Tüketim (dağıtım şirketi) | **parse edilmiyor** — bkz. §4.3 | **Parse edilmez — T11 ile redundant** |
| T13 | Serbest tüketici (il×tür×grup) | `fact_serbest_tuketici` (yalnız Excel yılları, bkz. §4.4) | Parse edilir, **YAZAR** |

**Düzeltme notu (2026-09-07, geri alındı — bkz. §14.1):** v1.0 taslağı
burada "T12, T8 gibi atlanıyor notu YANLIŞTI, T8 gerçekten parse
ediliyor" diye bir "düzeltme" içeriyordu. Bu **düzeltmenin kendisi
yanlıştı** — kaynak olarak gösterilen `05_kaynak_dosya_sozlesmesi.md`
satır 20 yalnızca **hedef haritası** (plan), aynı dosyanın satır 105'i
ise kodun (`worker/parser.py`, `worker/pipeline.py`) T8'i **hiç
implemente etmediğini** açıkça söylüyor. Doğrusu: **T8 de T12 gibi
parse edilmiyor**, ikisi de T11 ile redundant. Bu, dokümanın kendi
yöntem kuralının ("çelişkide kod esas alınır, doküman değil") burada
ihlal edildiği somut bir örnektir.

### 4.3 Bilinçli Parse Edilmeyen: T8 ve T12
2026-08-30'da gerçek dosyayla doğrulandı: T12'nin grain'i doküman
başlığının ima ettiği "dağıtım bölgesi" değil, gerçek kolon adı 'Lisans
Unvanı' — **dağıtım şirketi** (21 şirket + ulusal "İLETİMDEN BAĞLI
TÜKETİCİLER (TÜRKİYE)" satırı, yalnız Sanayi). T12'nin Genel Toplam ve
iletim/Sanayi rakamları T7/T11 ile birebir eşleşiyor → **T11 ile
redundant, hiçbir yeni bilgi taşımıyor** — bu yüzden `worker/parser.py`'de
hiç implemente edilmedi. İleride dağıtım-şirketi-bazlı bir KPI
gerekirse, statik bir `dim_il → dagitim_sirketi` eşleme tablosuyla
T11'in il bazlı verisinden türetilebilir (bilgi kaybı yok).

**T8 aynı sınıfa girer:** T11 ile birebir aynı il×tüketici-grubu verisini
tekrarlıyor (T11 ayrıca Sanayi'yi iletim/dağıtım olarak ayırıyor, T8
ayırmıyor) → hiçbir yeni bilgi taşımadığı için o da implemente
edilmedi (`worker/parser.py` satır 17-24).

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

### 5.5 `fact_tuketim_ulke_geneli`'nin 2026+ Excel Genişlemesi (2026-09-08, Aşama 3/ADIM 1-2)
**Tanım dikişi kontrolü (ADIM 1) — GERÇEK dosyaya karşı, 3'ten fazla ay
(202601-202606, TÜMÜ) test edildi:** Excel T11'in kendi "Genel Toplam"
satırı da (Word'deki gibi) kullanılabiliyor, ama Excel'de bu satır
**KÜMÜLATİF** (başlıkta açıkça "Kümülatif Faturalanan..." yazıyor — aynı
kümülatiflik `fact_tuketim`'in T11'i için zaten biliniyordu, bkz. §6.4/
`worker/pipeline.py` satır ~358). De-kümülatif edildiğinde (`worker/
parser.py:tablo11_genel_toplam_satiri_oku()` + `worker/ingest.py:
yil_ici_onceki_tuketim_ulke_geneli_toplami()`, `fact_tuketim`'in T11
de-kümülatif etme deseniyle BİREBİR AYNI), **T7 ile karşılaştırıldığında
6 ayın 4'ü ONDALIK BASAMAĞA KADAR birebir eşleşti** (202601/03/04/05);
2 ayda (202602, 202606) toplam tüketimin **%0,02'sinin altında** (3.708
MWh / 208 MWh) küçük bir fark bulundu — EPDK'nın kendi T7/T11 arası doğal
bir tutarsızlığı olduğu değerlendirildi (Word'de aynı karşılaştırma
2023-06 için TAM eşleşmişti, bkz. §5.4 civarı araştırma notu), bu ADIM'ın
de-kümülatif mantığından KAYNAKLANMIYOR. **Karar: T7 DEĞİL, T11'in kendi
Genel Toplam satırı kullanıldı** — seri 2016-2025 (Word, T11) ile 2026+
(Excel, T11) arasında TEK bir tanımda kalıyor, 2025→2026 sınırında dikiş
atlamıyor.

**Gerçek bir bug bulundu ve düzeltildi (ADIM 2 uygulaması sırasında):**
`yil_ici_onceki_tuketim_ulke_geneli_toplami()`'nin ilk sürümü `is_active
=true` filtreliyordu — bu tablo elle onaya kadar `is_active=false`
kaldığından (bkz. `pipeline.isle_ay_ulke_geneli_excel()` "onayla
ÇAĞRILMADI" notu), art arda 6 ayı hiçbiri aktive edilmeden işleyen bir
toplu backfill'de HER ay "önceki toplam"ı BOŞ görüp kendi KÜMÜLATİF
değerini yanlışlıkla "aylık" olarak yazdı (canlıda gerçekten oldu, 6
batch silinip düzeltmeyle yeniden çalıştırıldı). Düzeltme: filtre
`is_active`'ten, her (tarih_id, grup_id) için EN SON batch'i alan bir
`DISTINCT ON (... ORDER BY ingestion_batch_id DESC)` sorgusuna çevrildi
— aktivasyon durumundan bağımsız çalışır. Regresyon testi eklendi
(`test_yil_ici_onceki_tuketim_ulke_geneli_toplami_aktivasyonsuz_calisir`).

**Sonuç (canlı, 2026-09-08):** 2026-01..06, 30 yeni satır (629 toplam
aktif satır — 599 + 30), `worker/scripts/backfill_ulke_geneli_excel.py`
ile yüklenip `pipeline.batch_onayla()` ile aktive edildi. **KPI-13
(YoY)** girdisi `fact_tuketim`'den (il bazlı) `fact_tuketim_ulke_geneli`
(ülke geneli, `worker/analytics.py:ulke_geneli_tuketim_getir()`) taşındı
— canlıda kanıtlandı: 2026-06 vs 2025-06 (Word/Excel sınırını geçen bir
çift) artık **+%7,1** gerçek bir değer veriyor (eskiden HER ZAMAN
'hesaplanamaz' dönüyordu, grup kümesi — Sanayi — uyuşmuyordu; il bazlı
`fact_tuketim` DEĞİŞMEDİĞİNDEN eski yolla hâlâ None döndüğü de ayrıca
doğrulandı — regresyon yok, yalnız KPI-13'ün girdisi değişti).

### 5.6 `fact_tuketim_ulke_geneli` Batch Bağımlılığı Düzeltmesi (2026-09-08, Aşama 3/ADIM 3 madde 1)
**Kalan sorun (§5.5'teki "en son batch" düzeltmesinden SONRA bile):** ay
N'nin aylık değeri, ay N-1'in İŞLENDİĞİ ANDAKİ en son batch'inden
türetiliyordu — ama N-1 SONRADAN başka (düzeltilmiş) bir batch'le
aktive edilirse, N'nin zaten kayıtlı değeri artık hiçbir aktif veriden
türetilmemiş oluyordu ve bunu YAKALAYACAK hiçbir mekanizma yoktu (projenin
batch izolasyonu ilkesine aykırı, sessiz bir bağımlılık).

**Düzeltme (migration `20260908_0002`):** `fact_tuketim_ulke_geneli`'ye
nullable `kumulatif_tuketim_mwh` kolonu eklendi (yalnız Excel ayları için
dolu — Word ayları NULL kalıyor, kaynakta zaten kümülatif kavramı yok).
`ingest.yil_ici_onceki_tuketim_ulke_geneli_toplami()` KALDIRILDI, yerine
`ingest.onceki_ay_kumulatif_ulke_geneli_getir()` geldi — artık önceki
ayların toplamını YENİDEN HESAPLAMIYOR, yalnız bir önceki ayın KAYITLI
kümülatifini tek satır okuyor. Yeni formül: aylık = bu batch'in kendi
kümülatifi − önceki ayın KAYITLI kümülatifi.

**Yeni kalıcı script — `worker/scripts/tutarlilik_ulke_geneli_kumulatif.py`:**
her aktif Excel ayı için, kayıtlı aylık değerin "kendi kümülatifi − önceki
ayın GÜNCEL aktif kümülatifi" ile hâlâ eşleştiğini doğrular; N-1 sonradan
değişirse bunu AÇIKÇA (exit code 1 + rapor) yakalar — sessiz kalmaz.

**Doğrulama (disposable postgres:17, 2026-09-08):** migration + 279/279
pytest yeşil; mevcut 6 ay (202601-202606, 30 satır) sıfırdan bu YENİ yolla
yeniden işlendi — canlıdaki `tuketim_mwh` değerleriyle ONDALIK BASAMAĞA
KADAR birebir eşleşti (regresyon yok, yalnız eksik denetim eklendi).
Script'in gerçekten yakaladığı KANITLANDI: 2026-02'ye kasıtlı 500.000 MWh
farklı bir kümülatifle superseding bir batch aktive edilip script
çalıştırıldı — yalnız beklenen (202603, Sanayi) satırı tutarsız
işaretlendi, başka hiçbir satır yanlış pozitif vermedi.

**Canlıya uygulama (2026-09-08):** migration + `worker/scripts/
backfill_ulke_geneli_kumulatif_kolon.py` (aynı 6 kaynak dosyadan T11
kümülatif değerini okuyup yalnız yeni kolonu dolduran, `tuketim_mwh`'ye
DOKUNMAYAN tek seferlik script) canlıda çalıştırıldı — 30/30 satır
güncellendi. `mutabakat_ulke_geneli.py` (479 çift, 0 uyumsuz) ve
`tutarlilik_ulke_geneli_kumulatif.py` (30 çift, 0 tutarsız) canlıda YEŞİL.

### 5.7 `fact_uretim_kaynak_geneli` + `fact_uretim_il_geneli` (2026-09-09, gece çalışması — Aşama 3/ADIM 3 madde 2)
**⚠️ Bu turda YALNIZ disposable postgres:17'de doğrulandı — CANLIYA
UYGULANMADI, kod/tablo/RLS/GRANT sabah onayla uygulanacak (gözetimsiz
gece çalışması sınırı, bkz. `09_PROJE_DURUMU.md` "Sonraki Oturum Devam
Noktası").**

Migration `20260909_0001_fact_uretim_kaynak_il_geneli.sql` — KPI-02/03/
05/06/07 için üretim verisi hazırlığı, `fact_tuketim_ulke_geneli` ile
BİREBİR AYNI batch/is_active/RLS/policy/GRANT deseni, iki tablo:

- `fact_uretim_kaynak_geneli (tarih_id, kaynak_id, lisans_id, uretim_mwh)`
  — kaynak-bazında ülke geneli üretim (Excel T2+T5, Word Tablo 1.6+1.11).
- `fact_uretim_il_geneli (tarih_id, il_kodu, lisans_id, uretim_mwh)` —
  il-bazında ülke geneli üretim (Excel T3+T6, Word Tablo 1.7+1.12).

**Neden İKİ tablo, tek değil:** ADIM 1 araştırması (bkz. §5.5 öncesi
Aşama 3 araştırma notları) EPDK'nın ne Excel ne Word formatında il×kaynak
JOINT bir kırılım vermediğini kanıtlamıştı — yalnız iki AYRI marjinal
seri var. İkisinin AYRI tutulması, aralarındaki tutarlılığın (`worker/
scripts/mutabakat_uretim.py`, ADIM 3 madde 3) bağımsız bir çapraz-kontrol
olarak çalışmasını sağlıyor — parser hatalarını anında yakalar.

**⚠️ KÜMÜLATİF DEĞİL:** §5.6'daki `kumulatif_tuketim_mwh` deseni buraya
KASITLI OLARAK kopyalanmadı — Excel T2/T3/T5/T6 zaten AY BAZINDA değer
veriyor (ADIM 1'de gerçek dosyaya karşı doğrulandı, Şubat < Ocak örneği).

**`lisans_id` her iki tabloda da var** (Lisanslı/Lisanssız) — hem
mutabakat script'inin (tarih_id, lisans_id) bazında karşılaştırma
yapabilmesi hem de gelecekteki KPI-05'in (ADIM 5, bu turda YOK) pay/payda
tutarlılığı için gerekli.

**Doğrulama (disposable postgres:17, 2026-09-09):** migration 29/29
uygulandı (önceki 28 + bu 1), `validate_rls_static.py` → 21/21 tablo
RLS+policy (önceki 19 + bu 2 yeni), `validate_role_access.py` → TAMAMEN
geçti, tam pytest paketi → 281/282 (tek "hata" — canlı Auth'a bilerek
bağımlı `test_auth_integration.py`'nin disposable DB'ye yönlendirilmiş
olması, beklenen, regresyon DEĞİL). `sqlfluff lint` temiz.

### 5.8 T2/T3/T5/T6 Excel Parser Fonksiyonları — GERÇEK Bir Hata Bulundu ve Düzeltildi (2026-09-09, gece çalışması — Aşama 3/ADIM 3 madde 2)
**Bulgu:** `tablo_kaynak_toplam_oku()` (T2/T5) ve `tablo_il_toplam_oku()`
(T3/T6) fonksiyonları ZATEN VARDI (önceki bir turda, muhtemelen T1/T4 ile
birlikte, yalnız 2026 Ocak dosyasına karşı doğrulanmıştı — bkz. §5.1
modül notu) ama HER ZAMAN sabit bir kolon (`column=2` / `il_sutun+1`)
okuyorlardı. Gerçek dosyaya (202606) karşı doğrulama sırasında bulundu:
bu tablolar TEK bir ay değil, **Ocak'tan raporun kendi ayına kadar TÜM ay
kolonlarını AYNI SAYFADA** taşıyor (kümülatif DEĞİL — her kolon kendi
ayının marjinal değeri). Sabit kolon yalnız Ocak dosyasında (tek kolon)
doğru sonuç veriyordu — Haziran gibi sonraki bir ayda **SESSİZCE Ocak'ın
değerini dönerdi** (asla test edilmemişti, çünkü paylaşılan sentetik
fixture da yalnız 202601 kullanıyordu).

**Ek bulgu:** T2/T3'ün ay başlıkları yalnız ay adı ("OCAK", "ŞUBAT", ...),
T5/T6'nınki yıl+ay birleşik ("2026 OCAK", "2026 ŞUBAT", ...) — dosyaya
karşı doğrulandı, kullanıcının MADDE 2 talimatında da önceden
işaretlenmişti.

**Düzeltme:** yeni `_ay_kolonu_bul()` — `tarih_id`in ayına karşılık gelen
kolonu, normalize edilmiş başlığın SON kelimesini ay adıyla karşılaştırıp
bulur (hem "HAZIRAN" hem "2026 HAZIRAN" için çalışır, tek fonksiyon).
Sabit kolon numarasına bağımlılık tamamen kaldırıldı.

**Doğrulama:**
- 6 gerçek dosyanın (202601-202606) TAMAMINA karşı: her ay için T2
  (kaynak-bazında ülke toplamı) ile T3 (il-bazında ülke toplamı)
  **ONDALIK BASAMAĞA KADAR BİREBİR eşleşti** (Lisanslı), aynı şekilde T5
  ile T6 (Lisanssız) de birebir eşleşti — bu, ADIM 3 madde 3'ün çapraz
  mutabakat script'inin ülke-geneli seviyede zaten tutarlı olacağının
  güçlü bir kanıtı.
- Yeni birim testleri (`worker/tests/test_parser.py`): hem T2/T3 stili
  ("OCAK") hem T5/T6 stili ("2026 OCAK") çok-kolonlu sentetik sayfalarla,
  komşu ayın değerinin SESSİZCE dönmediği AÇIKÇA doğrulandı (regresyon
  testi — eski koda karşı çalıştırılsa FAIL verirdi); bulunamayan bir ay
  istenirse boş DataFrame (sahte değer YOK) döndüğü de test edildi.
- Tam pytest paketi (disposable postgres:17, fresh): **285/286** (tek
  beklenen "hata" — yine `test_auth_integration.py`).

### 5.9 `mutabakat_uretim.py` — Çapraz Mutabakat Script'i (2026-09-09, gece çalışması — Aşama 3/ADIM 3 madde 3)
**Bu işin asıl güvencesi (kullanıcı talimatı):** `fact_uretim_il_geneli`
ile `fact_uretim_kaynak_geneli` AYNI üretim toplamının BAĞIMSIZ iki
kırılımı — her (tarih_id, lisans_id) çifti için toplamları eşleşmelidir.
`worker/scripts/mutabakat_uretim.py`, `mutabakat_ulke_geneli.py`
deseninde ama tek farkla: burada iki taraf da EŞİT derecede "yeni" (biri
uzun süredir aktif değil) — `is_active` FİLTRELENMEZ, her iki tarafın da
EN SON batch'i karşılaştırılır (§5.6'nın batch-bağımlılığı dersiyle
tutarlı). ±%0,5 tolerans dışı kalan (tarih_id, lisans_id) çifti, İKİ
tablonun da batch'ini "uyumsuz" (aktivasyona uygun DEĞİL) işaretler —
hangi tablonun hatalı olduğu script seviyesinde belli olmadığından.

**Aktivasyon engelleme:** `periyot_aktivasyona_uygun_mu(conn, tarih_id)`
— `pipeline.otomatik_onaya_uygun()` ile AYNI `(bool, sebep)` imzası. ADIM
3 madde 4'ün backfill/pipeline kodu, bir periyodu aktive etmeden ÖNCE bunu
çağırmalı (henüz o pipeline kodu yazılmadı — bu yalnız gate fonksiyonunu
hazırlıyor).

**Doğrulama:**
- 4 yeni entegrasyon testi (`worker/tests/test_mutabakat_uretim.py`):
  uyumlu veri geçer, KASITLI OLARAK üretilen uyumsuz veri (İl=1000,
  Kaynak=850, %15 fark) hem detayda hem `uyumsuz_batch_idler`'da doğru
  yakalanır (HER İKİ batch de bloklanır), gate fonksiyonunun her iki yönü
  (uygun/uygun değil) ayrı ayrı test edildi.
- **Gerçek 6 aya karşı (parser çıktıları, henüz DB'ye yüklenmeden):**
  12/12 (6 ay × 2 lisans türü) toplam ONDALIK BASAMAĞA KADAR birebir
  eşleşti — script'in gerçek veriyle YEŞİL çıkacağının kanıtı (gerçek DB
  yüklemesi ADIM 3 madde 4'te).

### 5.10 Excel Üretim Backfill'i + Mutabakat-Gated Aktivasyon (2026-09-09, gece çalışması — Aşama 3/ADIM 3 madde 4)
**⚠️ Bu turda YALNIZ disposable postgres:17'de doğrulandı — CANLIYA
UYGULANMADI, sabah onayla uygulanacak.**

Eksik altyapı tamamlandı: `ingest.fact_uretim_kaynak_geneli_yukle()` +
`ingest.fact_uretim_il_geneli_yukle()` (`fact_tuketim_ulke_geneli_yukle()`
ile AYNI desen, KÜMÜLATİF DEĞİL), `kpi.dogrula_uretim_geneli()` (yalnız
negatif `uretim_mwh` reddi — `dogrula_uretim()`'den farklı, `kurulu_
guc_mw` burada YOK), `pipeline.isle_ay_uretim_excel()` (T2+T5→kaynak
tablosu, T3+T6→il tablosu, AYNI batch_id altında — `isle_ay_ulke_geneli_
excel()` ile AYNI desen: `fact_uretim`'in T1/T4 batch zincirine
DOKUNMAZ), ve `_DOGAL_ANAHTAR`'a iki yeni tablo eklendi (P0-4 aktivasyon
mekanizmasının bu tabloları tanıması için).

**Önemli tasarım notu (kod incelemesi sırasında bulundu, canlıya
dokunmadan düzeltildi):** `isle_ay_uretim_excel()` başlangıçta T2/T3'ü
(ve T5/T6'yı) AYNI sayfa nesnesini paylaştığı varsayımıyla yazılmıştı —
gerçek dosyada doğru (ikisi de "Tablo 2-3"/"Tablo 5-6" birleşik sayfa),
ama sentetik test workbook'unda (`worker/tests/test_parser.py`) T2/T3/T5/
T6 AYRI sayfalar. Her tablo artık AYRI `_sayfa()` çağrısıyla bulunuyor —
gerçek dosyada maliyetsiz (aynı sayfaya çözülüyor), sentetik/test
senaryosunda DOĞRU çalışıyor. Bu, pipeline entegrasyon testi yazılırken
bulundu ve GERÇEK backfill'e dokunmadan (henüz çalıştırılmamıştı)
düzeltildi.

`worker/scripts/backfill_uretim_excel.py` — `backfill_ulke_geneli_
excel.py`'nin `MANIFEST`'ini yeniden kullanır, yükler, SONRA her ay için
`mutabakat_uretim.periyot_aktivasyona_uygun_mu()`'yu çağırır — yalnız
UYGUN çıkan aylar aktive edilir (kullanıcı talimatı: "tutmuyorsa
aktivasyonu ENGELLE").

**Doğrulama (disposable postgres:17, fresh, canlıya dokunmadan):**
- `--dry-run`: 6/6 ayda kaynak toplamı = il toplamı (fark 0).
- Gerçek yükleme + aktivasyon: 6/6 ay başarıyla yüklendi, **mutabakat
  6/6 ayda UYGUN çıktı, 6/6 ay aktive edildi** (hiçbiri bloklanmadı).
- `fact_uretim_kaynak_geneli`: 101 satır (hepsi aktif); `fact_uretim_
  il_geneli`: 942 satır (hepsi aktif).
- `mutabakat_uretim.py` CLI'ı canlı veriyle (disposable) çalıştırıldı:
  **12/12 (tarih_id, lisans_id) çifti uyumlu, 0 uyumsuz**.
- `validate_rls_static.py`/`validate_role_access.py`: veri yüklendikten
  SONRA da 21/21 tablo YEŞİL.
- 2 yeni pipeline entegrasyon testi (`worker/tests/
  test_pipeline_integration.py`): uçtan uca yükleme (idempotency dahil —
  ikinci çağrı ATLANIR) + mutabakat-uygunluk + gerçek aktivasyon
  (`batch_onayla()` sonrası `is_active=true`).
- Fresh disposable postgres:17'de tam pytest paketi: **291/292** (tek
  beklenen "hata" — `test_auth_integration.py`).

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
İÇERİĞİ dahil**. Bu tasarım kararı 2026-09-07'de kritik önem kazandı:
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

### 6.4 VAKA — 39 Aylık "Mutabakat Uyumsuzluğu" (2026-09-07)
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
2026-09-07 kaydı.)

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
- **KPI-25** CAGR — toplam tüketim (%), RESMİ tanım: **2026-09-08'de
  (Aşama 2/C5) `fact_tuketim_ulke_geneli`'ye TAŞINDI** — önceki (2026-09-03)
  "yalnız Sanayi'yi İÇEREN yıllar" filtresi il bazlı `fact_tuketim`
  içindi ve pratikte yalnız 2026'yı bırakıyordu (sürekli 'hesaplanamaz').
  Yeni kaynak Sanayi DAHİL tüm grupları 2016-2025'in TAMAMI için
  içerdiğinden filtre GEREKSİZLEŞTİ, kaldırıldı. Yeni şart: bir yıl
  yalnız TAM 12 ay VE 5/5 grup mevcutsa (60/60 satır) seriye girer — bu
  **2016'yı KASITLI olarak dışarıda bırakır** (2016-12 Tarımsal kaynakta
  hiç yüklenmedi, bkz. §11.3). İl bazlı `fact_tuketim` ile ASLA
  karıştırılmaz (grain karışımı riski, bkz. §11.2 — artık KAPANMIŞ
  karar). Canlıda 2017→2025 (9 nokta, n=8) için **+%3,1** hesaplanıyor
  (2026-09-08 doğrulaması — eskiden hep 'hesaplanamaz'dı, bu GERÇEK bir
  fonksiyonel değişiklik, yalnız kozmetik değil).
- **KPI-27** CAGR — Sanayi-HARİÇ tüketim (%): kaynağı **İL BAZLI
  `fact_tuketim`, DEĞİŞMEDİ** (KPI-25'in taşınmasından etkilenmedi).
  Sanayi TÜM yıllardan açıkça çıkarılarak hesaplanır. KPI-25'İN YERİNE
  GEÇMEZ (resmi "toplam tüketim" tanımını karşılamaz). 2016→2025 (10
  tam yıl) için canlıda **+%3,8** hesaplanıyor (2026-09-08 doğrulaması).
  **Bu, önceki bir turda kaydedilen "2023→2025, +%6,9" rakamından FARKLI
  — kod DEĞİŞMEDİ; pencere genişledi çünkü 2016-2022'nin Word
  genişlemesi (bkz. §10, 2026-08-31→09-03) tamamlandığından bu 7 yıl da
  artık "tam yıl" (12/12 ay) şartını karşılıyor, seri 2023'ten değil
  2016'dan başlıyor.** Eski rakam `06_canli_veri_operasyon_gunlugu.md`'de
  (2026-09-02 tarihli, HISTORICAL) kendi anına özgü bir kayıt olarak
  duruyor, güncel değer İÇİN her zaman bu bölüme bakılmalı.
- **KPI-26** CAGR — yenilenebilir kurulu güç (%): STOK metriği (aylar
  TOPLANMAZ, yılın son ayı alınır). Yalnız Lisanslı verisi (T1) OLAN
  yıllar seriye girer — Word 2023-2025'te T1 yok (Karar 3), filtre
  olmasaydı sahte CAGR üretilirdi (AYNI kök neden eski KPI-25 ile).

**KPI-28 numara notu (2026-09-07, denetimde bulundu):** `05_kaynak_
dosya_sozlesmesi.md` ("Yıllık Rapor" bölümü), yıllık-aylık toplam sapması
için **KPI-28** numarasını ayırmış — ama bu **yalnız doküman satırı**,
`grep -rn "kpi_28\|KPI-28" worker/` sıfır sonuç verir: kodda hiç
implemente edilmedi. Yani KPI-28 **tanımlı ama uygulanmamış** bir slot.
Yeni bir KPI eklenecekse (örn. "Veri Kapsam Tamlığı") bu numarayla
**çakışmasın diye KPI-29'dan başlanmalı**; KPI-28 ileride gerçekten
implemente edilirse yukarıdaki tanım (yıllık toplam OD-4 ile otoriter,
aylık toplamla sapma → uyarı) esas alınmalı.

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

**C4 düzeltmesi (2026-09-07) — DISABLE bir istisnaydı, hiç karar olarak
yazılmamıştı:** Yukarıdaki `20260904_0002`/`0004`'ün "RLS DISABLE" çözümü
8 tabloyu (`dim_tarih`/`dim_il`/`dim_kaynak`/`dim_tuketici_grubu`/
`dim_lisans`/`sistem_parametre`/`kpi_esik`/`job_status`) `02_srs_ozet.md`'nin
"TÜM uygulama tablolarında RLS zorunlu, deny-by-default" P0 kuralının
**belgelenmemiş bir istisnası** yapmıştı. `20260907_0001_dim_config_job_
rls_restore.sql` bunu tersine çevirdi — RLS 8 tabloda da tekrar açıldı,
körlemesine `USING (true) FOR ALL` DEĞİL, gerçek erişim niyetini kodlayan
İKİ katmanlı politika ile: `SELECT` → viewer+data_operator+admin
(`USING (true)` — bu tablolar gerçekten satır filtresi gerektirmeyen
referans/config verisi, formalite değil), `INSERT/UPDATE/DELETE` →
yalnız admin. `02_srs_ozet.md`'ye DOKUNULMADI — kural zaten doğruydu,
yalnız gerçeklik ona uydurulmadı; artık uyuyor.

**Yeni, istisnasız bir tamlık kontrolü** eklendi
(`worker/validate_role_access.py:_test_tum_tablolarda_rls_ve_policy_var`)
— `worker/validate_rls_static.py`'nin metin taraması (yalnız 3 sabit
dosyaya bakar, hiçbir migration listesini KENDİLİĞİNDEN takip etmez) bu
tür bir eksikliği YAKALAYAMAZDI; yeni kontrol canlı/disposable DB'nin
gerçek `pg_class.relrowsecurity` + `pg_policies` durumuna bakar — hangi
migration'ın ne yaptığı önemsiz, yalnız SONUÇ durumu. İstisna listesi
YOK: `public` şemasındaki HER tablo RLS açık + ≥1 policy'e sahip olmak
zorunda.

**Doğrulama (canlıya uygulamadan ÖNCE, disposable postgres:16'da — WSL/
Docker, `ci.yml`'in `integration` job'ıyla BİREBİR aynı migration
sırasıyla):**
1. 26/26 migration uygulandı, `validate_rls_static.py` + yeni tamlık
   kontrolü geçti: **"19 tablonun TAMAMI RLS açık + en az 1 policy'e
   sahip"**.
2. **Negatif test — hem yerel drill'de hem GERÇEK CI'da:** politika/
   RLS'siz sahte bir tablo eklenip yeni kontrol tekrar çalıştırıldı —
   **gerçekten FAIL etti** (`AssertionError: ... sahte_test_tablosu_c4
   (RLS=KAPALI, 0 policy)`). Gerçek GitHub Actions koşusu (run
   34159900787): `integration` job'ının "Run role-based access
   verification" adımı X ile durdu, downstream adımlar (`ingest/
   pipeline/job_worker/analytics/fetch_weather_integration.py`,
   `Quality Gate`) atlandı — tam beklenen "sessizce geçme YOK" davranışı.
   Test dosyası bir sonraki commit'te geri alındı.
3. **Dashboard yolu ayrıca test edildi** (yalnız doğrudan `SET ROLE`
   değil) — `worker/auth.py:rol_baglantisi_ac()` gerçek fonksiyonu
   `app_dashboard_service` üzerinden çağrılarak: viewer/data_operator/
   admin'in üçü de `dim_il`'i (81 satır) SELECT edebildi; admin `dim_il`
   üzerinde gerçek bir UPDATE yapabildi (1 satır, rollback ile temiz);
   viewer aynı UPDATE'i deneyince `InsufficientPrivilege` ile reddedildi
   (beklenen — yalnız admin'e write GRANT'i var).
4. `worker/jobs/*.py`'nin `job_status`'a kendi yazması ETKİLENMEDİ —
   `DATABASE_URL` (postgres, service rolü) RLS'ten muaf: **CANLIDA
   doğrulandı** (`SELECT rolbypassrls FROM pg_roles` → `true`, varsayılmadı).

**Canlıya uygulandı (2026-09-07):** CI yeşil olduktan sonra migration
canlı Supabase'e uygulandı. Uygulama sırasında bir engel çıktı ve
çözüldü — **şeffaflık için kaydediliyor:** `job_status` üzerinde 3+
saattir "idle in transaction" durumda, `app_dashboard_service` rolüyle
(muhtemelen kapatılmamış eski bir Streamlit oturumu) açık kalmış salt-
okunur bir bağlantı, `ALTER TABLE job_status ENABLE ROW LEVEL SECURITY`
için gereken kilidi engelleyip `statement_timeout` ile migration'ı
durdurdu. Bağlantı `pg_terminate_backend()` ile sonlandırıldı (yalnız
`SELECT job_id, ... FROM job_status` çalıştırıyordu, veri kaybı riski
YOK — Streamlit basitçe yeniden bağlanır) ve migration ikinci denemede
sorunsuz uygulandı. Detay: `06_canli_veri_operasyon_gunlugu.md`
2026-09-07 kaydı.

**Canlıda TAM doğrulama (migration sonrası, gerçek `DATABASE_URL_
DASHBOARD` ile):**
- `pg_class`/`pg_policies`: **19/19 tablo** RLS açık + ≥1 policy (0 sorun).
- `rol_baglantisi_ac()` ile viewer/data_operator/admin'in üçü de
  `dim_il` (81 satır) ve `job_status`'u (8 satır) SELECT edebildi.
- admin `dim_il`'de gerçek bir UPDATE yapabildi (1 satır, rollback ile
  temiz); viewer aynı UPDATE'i deneyince `InsufficientPrivilege`.
- `postgres` rolünün (worker'ın `DATABASE_URL`'i) `rolbypassrls = true`
  olduğu doğrudan `pg_roles`'tan doğrulandı — job_status'a worker
  yazması kesinlikle etkilenmiyor.

Öncesinde (canlıya dokunmadan) `worker/scripts/backup.py` ile taze bir
yedek alındı (`11_yedekleme_runbook.md`'deki prosedür).

**Aynı olayın tekrarına karşı — `idle_in_transaction_session_timeout`
(2026-09-08, Aşama 1 kapanışı):** `20260908_0001_app_dashboard_service_
idle_timeout.sql`, `app_dashboard_service`'e `idle_in_transaction_
session_timeout = '30min'` set eder. **Kök neden SİSTEMATİK, tek
seferlik değil** — `app/dashboard.py` hiçbir yerde `conn.commit()`/
`rollback()` ya da `autocommit=True` kullanmıyor (psycopg varsayılanı
`autocommit=False`), bu yüzden HER dashboard oturumu ilk sorgusundan
itibaren kapanana kadar TEK bir açık işlem içinde kalıyor — Streamlit
sekmesi etkileşimsiz bırakıldığında bu otomatik olarak "idle in
transaction" hâline geliyor (yalnız 2026-09-07'deki tek olay değil, HER
terk edilmiş sekme için geçerli bir desen). Doğru parametre budur —
`idle_session_timeout` (PG14+, TAMAMEN boş oturumlar için) DEĞİL, çünkü
senaryo "açık işlem, sorgu yok" (PG9.6+'nın `idle_in_transaction_
session_timeout`'u).

**Test edildi, VARSAYILMADI:** kısa bir timeout (2s) ile gerçek bir
oturumda ikinci sorgu `psycopg.errors.IdleInTransactionSessionTimeout`
fırlattı. **Bilinen sınırlama:** `app/dashboard.py`'de bu hatayı yakalayıp
otomatik yeniden bağlanan bir mekanizma YOK — kullanıcı "Çıkış Yap" ile
elle yeniden giriş yapmalı (kod refactor'ü bu turun kapsamı dışı
bırakıldı). 30 dakikalık değer, aktif kullanımda (herhangi bir 30 dk
pencerede en az bir etkileşim, ki her etkileşim yeni bir sorgu çalıştırıp
sayacı sıfırlar) bu riski pratikte sıfıra indiriyor — yalnız gerçekten
terk edilmiş sekmeler etkilenir, ki asıl amaç zaten onları temizlemek.
Doğrulandı (disposable postgres:16, 27/27 migration): `pg_roles.
rolconfig` → `{idle_in_transaction_session_timeout=30min}`. **Canlıya
uygulandı (2026-09-08)** — CI yeşil olduktan sonra, `pg_stat_activity`'de
hiçbir "idle in transaction" bağlantı OLMADIĞI teyit edilerek. Canlıda
`rolconfig` doğrulandı; normal ardışık kullanım (aynı bağlantıda hemen
art arda 2 sorgu) sorunsuz çalıştı — 30 dakikalık timeout aktif kullanımı
etkilemiyor.

**Kök neden KOD SEVİYESİNDE de kapatıldı (2026-09-08, Aşama 2):**
`app/dashboard.py`'de `rol_baglantisi_ac()`'ın döndürdüğü bağlantı artık
`autocommit=True`'ya alınıyor — HER sorgu kendi başına commit edilir,
bağlantı HİÇBİR ZAMAN açık bir işlemde kalmıyor (yukarıdaki DB seviyesi
`idle_in_transaction_session_timeout` artık yalnız bir GÜVENLİK AĞI,
birincil savunma DEĞİL). **Canlıda GERÇEK bir testle kanıtlandı**
(varsayılmadı): `autocommit=True` ile bir sorgu çalıştırılıp 2 saniyelik
kısa bir `idle_in_transaction_session_timeout` konup 3 saniye
beklendiğinde İKİNCİ sorgu SORUNSUZ çalıştı (`IdleInTransactionSessionTimeout`
HİÇ fırlamadı) — `autocommit=False` ile AYNI test önceki turda hatayı
GERÇEKTEN üretmişti (bkz. yukarıdaki paragraf), fark BİREBİR bu
değişiklikten geliyor.

Ayrıca bağlantı yine de (ağ kopması, Supabase yeniden başlatma gibi BAŞKA
bir sebeple) ölürse artık kullanıcıya ham bir hata YANSIMAZ —
`_baglanti_saglikli_mi()` her `_baglanti_al()` çağrısında ucuz bir
`SELECT 1` ile sağlık kontrolü yapar; sağlıksızsa, giriş sırasında
saklanan JWT claim'iyle (`st.session_state["_jwt_claims_json"]`/`
["_rol"]`, Supabase Auth'a TEKRAR gidilmeden) sessizce yeni bir bağlantı
açılır. **Canlıda GERÇEK bir testle kanıtlandı:** bir bağlantı kasıtlı
kapatılıp `_baglanti_saglikli_mi()` doğru şekilde `False` döndü, saklanan
claim'le açılan yeni bağlantı sağlıklı çıktı ve gerçek bir sorgu
çalıştırdı.

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

### 8.5 Yedekleme (C1, 2026-09-07) — tam runbook: `11_yedekleme_runbook.md`
Bu proje **Supabase Free plan**'de — Supabase'in kendi otomatik günlük
yedeği **YOK** (yalnız Pro+'da var, bkz. runbook). Tüm sorumluluk elle
prosedürde: `worker/scripts/backup.py` (`pg_dump --schema=public
--data-only`, 6 seed tablosu — `dim_il`/`dim_kaynak`/`dim_lisans`/
`dim_tuketici_grubu`/`kpi_esik`/`sistem_parametre` — hariç, çünkü bunlar
zaten migration'larla yeniden oluşuyor). Şema geri yükleme için AYRICA
gerekmiyor — `supabase/migrations/`'ın kendisi zaten DDL kaynağı.

**GERÇEKTEN denendi (2026-09-07, tek seferlik disaster-recovery
drill'i):** disposable `postgres:17`'ye migration'lar uygulanıp
(`ci.yml`'in `integration` job'ıyla AYNI sıra) dump `pg_restore` ile geri
yüklendi — **19/19 tablo canlı Supabase'in `COUNT(*)` değerleriyle
BİREBİR eşleşti, 0 hata** (ilk denemede 6 seed tablosu dump'a dahildi ve
zararsız "duplicate key" hataları verdi — bu, `--exclude-table` eklenip
düzeltildi, ikinci deneme temizdi). Detaylı tablo + adım adım komutlar:
`11_yedekleme_runbook.md`.

**Otomatik hâle getirildi (2026-09-08, Aşama 1 kapanışı):**
`.github/workflows/scheduled-backup.yml` — her Pazar 03:00 UTC (+ elle
`workflow_dispatch`) `backup.py`'yi çalıştırıp dump'ı artifact olarak
saklar (`retention-days: 90`, açıkça belirtildi). İki kontrol ÖNCEDEN
yapıldı (varsayılmadı): repo **PUBLIC** (`gh repo view` doğrulandı —
artifact'lar repoyu görebilen herkese açık, bilinçli kabul edildi) ve
`audit_log` içeriği elle incelendi (e-posta/connection-string/yerel yol
YOK, yalnız zaten `git log`'da public olan operatör adı var) — dump
şifrelenmeden saklanıyor.

**Gerçek koşuyla UÇTAN UCA doğrulandı (2026-09-08, PAT'e `workflow`
izni eklendikten sonra):** İlk iki koşu GERÇEKTEN FAIL etti, gerçek
hatalarla düzeltildi — (1) `ubuntu-latest`'in `pg_dump 16.15`'i canlının
**PostgreSQL 17.6**'sından ESKİ olduğu için "server version mismatch"
ile reddetti → resmi PGDG apt deposundan `postgresql-client-17` kuruldu;
(2) kurulum sonrası jenerik `pg_dump` symlink'i hâlâ eski 16.15'i
gösteriyordu → `/usr/lib/postgresql/17/bin`, `$GITHUB_PATH` ile PATH'in
BAŞINA eklendi. Üçüncü koşu BAŞARILI: dump 1.61 MB. Artifact indirilip
`pg_restore --list` ile içeriği incelendi (beklenen TÜM tablolar TABLE
DATA olarak mevcut, 6 seed tablosu doğru şekilde YOK), disposable
`postgres:17`'ye GERÇEKTEN restore edildi (**canlı Supabase'in kendi
major sürümüyle BİREBİR aynı** — ilk denemede `postgres:16` hedef
kullanılmıştı, restore yine başarılıydı ama PG17'ye özgü `SET
transaction_timeout = 0;` için zararsız bir uyarı vermişti; hedef 17'ye
düzeltilip tekrar koşulunca o uyarı da ortadan kalktı) — **19/19 tablo
canlı Supabase'in `COUNT(*)` değerleriyle BİREBİR eşleşti**. 100 KB
eşiği de ayrıca test edildi (geçici 5 MB'a yükseltilip job'ın gerçek
dump'la GERÇEKTEN FAIL ettiği ve `upload-artifact`'in atlandığı
görüldü, sonra geri alındı). Detay: `11_yedekleme_runbook.md`.

---

## 9. CI/CD

Kaynak: `.github/workflows/{ci,security,deploy,scheduled-refresh,
scheduled-backup}.yml` (5 workflow dosyası — `scheduled-backup.yml`
2026-09-08'de eklendi, bkz. §8.5 — tam okundu).

### 9.1 `ci.yml` — 5 İş (Job)
| Job | İçerik |
|---|---|
| `worker` (Worker: lint · types · validation) | ruff check + format, mypy, `worker/validate_rls_static.py`, `worker/dogrula.py` (golden veri karşılaştırma), `pytest worker/tests -v` (bu job DATABASE_URL/DATABASE_URL_DASHBOARD hiç SET ETMEZ → `pytestmark skipif` ile TÜM 6 `*_integration.py` otomatik atlanır), `compileall` |
| `integration` (Schema validation + static RLS validation) | `worker`'a `needs` bağımlı. Disposable `postgres:16` servisi → `supabase/ci-only/01_roles_bootstrap.sql` (anon/authenticated/service_role taklit) → `0001_init_schema.sql` (roller) → `00_auth_stub.sql` (auth şema stub) → **kalan TÜM migration'lar glob ile sırayla** (`ON_ERROR_STOP=1`, uygulanan sayı `supabase/migrations/*.sql` sayısıyla karşılaştırılıp eşit değilse job FAIL eder — bkz. not) → `validate_rls_static.py` + `validate_role_access.py` (GERÇEK `SET ROLE`+sorgu ile RLS davranışı) + yalnız **5** `*_integration.py` dosyası isimle tek tek çağrılır (`test_ingest/pipeline/job_worker/analytics/fetch_weather_integration.py`) — **`test_auth_integration.py` bu listede YOK** (bkz. not) |

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

**Migration listesi artık GLOB, elle DEĞİL (2026-09-07 düzeltmesi, B2):**
2026-09-07'ye kadar `integration` job'ı her migration dosyasını TEK TEK,
isimle `psql -f` çağırıyordu — `deploy.yml`'in `migrate` job'ı ise HER
ZAMAN glob ile TÜMÜNÜ uyguluyordu (bkz. §9.3). Bu asimetri, yeni bir
migration ci.yml'in listesine eklenmeyi unutulursa **CI'da hiç test
edilmeden prod'a uygulanabileceği** anlamına geliyordu (defalarca
tekrarlanan bir gerçek disiplin sorunu, bkz. §10). Artık `integration`
job'ı da `deploy.yml` ile AYNI glob + sıralama mantığını kullanıyor, ARTI
uygulanan dosya sayısı `supabase/migrations/*.sql` sayısıyla karşılaştırılıp
eşit değilse job FAIL ediyor — "listeye eklemeyi unutma" riski yapısal
olarak ortadan kalktı. **Gerçek CI koşusuyla doğrulandı (run 34157349173,
2026-09-07):** hiçbir listeye eklenmeden bırakılan sahte bir migration
dosyası (`20260907_9999_b2_gecici_dogrulama_testi.sql`) glob'a otomatik
yakalandı — CI logunda `>> supabase/migrations/20260907_9999_...sql`
satırı ve dosyanın kendi `RAISE NOTICE` çıktısı ("bu migration glob ile
YAKALANDI") göründü, sayı doğrulaması `Uygulanan: 26 / Toplam dosya: 26`
ile geçti. Test dosyası bir sonraki commit'te geri alındı, canlıya hiç
uygulanmadı (deploy.yml'in `migrate` job'ı zaten devre dışı, bkz. §9.3).

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
  2026-09-07'den beri `ci.yml`'in `integration` job'ı da AYNI glob
  mantığını kullanıyor, bkz. §9.1), `deploy-ssh` (self-host,
  Coolify alternatifi yorumda), `smoke` job'ları `build-push`'a
  `needs` bağımlı olduğundan OTOMATİK skip ediliyor — yani bu job'lar şu
  an fiilen HİÇ ÇALIŞMIYOR, B2 düzeltmesi şu an için teorik bir riski
  kapatıyor (ama `build-push` aktive edildiğinde anında devreye girecek).
- **scheduled-refresh.yml**: her gün 04:00 UTC, `python -m worker.jobs.
  fetch_weather --incremental` (bir önceki tam ay). **Gerçek olay
  (2026-09-04/05):** bu adım aylarca "başarılı" görünüyordu çünkü
  `if: false` ile KAPALIYDI; gerçekten açılınca `PROD_DATABASE_URL`
  secret'inin repo'da hiç tanımlı olmadığı ortaya çıktı — kod hatası
  DEĞİL, eksik bir GitHub secret'tı (bkz. §10).
  **C3 düzeltmesi (2026-09-07):** aynı sessiz-başarısızlık deseninin
  tekrarını önlemek için iki katman eklendi — (1) `worker/jobs/
  fetch_weather.py:main()` artık 0 satır yazılırsa `SystemExit` ile
  job'ı FAIL ettiriyor (önceden yalnız log basıp sessizce çıkıyordu;
  pratikte `yazilan=0` yalnız `dim_il` boşsa mümkün, o da zaten ayrı bir
  `RuntimeError` fırlatıyor — bu, gelecekteki bir refactor'e karşı son
  savunma hattı), (2) `if: failure()` bir adım, başarısızlığı Actions
  özetinde (`$GITHUB_STEP_SUMMARY`) görünür kılıyor. GitHub'ın kendi
  scheduled-workflow e-posta bildirimi zamanlanmış cron'u OLUŞTURAN
  kullanıcıya gider (resmi GitHub dokümantasyonu doğrulandı) — bu proje
  için o kullanıcı `git log`'a göre repo sahibinin kendisi (2026-08-19'da
  oluşturdu); kişisel bildirim tercihinin (github.com/settings/
  notifications → Actions) açık olduğu KOD SEVİYESİNDE doğrulanamaz,
  elle teyit gerekir.

### 9.4 Test Stratejisi
25 dosya, **248 benzersiz `def test_*`** fonksiyonu (19 unit/regresyon +
**6** `*_integration.py`, bkz. §9.1 kutucuğu). Bunlar birden fazla
sayıyla raporlanır, hepsi doğru — ölçüm kapsamı farklı:
- **227**: pytest'in 19 unit/regresyon dosyasından TEK BAŞINA topladığı
  test ID sayısı (parametrize genişlemesiyle 199 def → 227 ID) —
  **doğrudan doğrulandı (2026-09-07):** temiz bir kabukta, `.env`
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

**Kod seviyesinde koruma (2026-09-07, denetim maddesi C2):** Yukarıdaki
kural artık yalnız dokümanda değil — `worker/tests/conftest.py`'nin
`pytest_configure` hook'u, `DATABASE_URL`/`DATABASE_URL_DASHBOARD` canlı
Supabase işareti (`supabase.co`/`supabase.com`/`pooler.supabase`)
taşıyorsa `pytest.exit(returncode=3)` ile paketi TOPLAMADAN durdurur.
`test_auth_integration.py`'nin bilinçli canlı-Auth akışını kırmamak için
`ALLOW_DESTRUCTIVE_TESTS=true` kaçış kapısı bırakıldı. Doğrulandı: sahte
bir `pooler.supabase.com` URL'i ile paket exit code 3 ile durdu; aynı URL
+ kaçış kapısıyla 276 test normal toplandı; DB env'siz durumda 227 test
sorunsuz koştu (regresyon yok).

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

### 11.2 KPI-25/27'nin `fact_tuketim_ulke_geneli`'yi Kullanıp Kullanmayacağı — KAPANDI (2026-09-08)
**Karar verildi ve uygulandı (Aşama 2/C5):** KPI-25 TAMAMEN
`fact_tuketim_ulke_geneli`'ye taşındı (tam yıl + 5/5 grup şartıyla),
KPI-27 il bazlı `fact_tuketim`'de KALDI (değişmedi) — KARIŞIK KAYNAK
tasarımından (aynı KPI içinde iki farklı grain'i toplama/birleştirme)
BİLİNÇLİ OLARAK kaçınıldı, her KPI TEK bir kaynağa bağlı. Detay: §7.5,
`worker/analytics.py:yillik_tuketim_serisi_getir()` docstring'i,
`dokumanlar/04_kpi_sozlesmeleri.md`.

### 11.3 2016-12 Tarımsal — Kalıcı Eksik
`fact_tuketim_ulke_geneli`'de 2016-12 yalnız 4/5 grupla aktif (Tarımsal
o ay ülke seviyesinde de negatif çıktığı için hiç yüklenmedi, kasıtlı —
bkz. §6.4). Dashboard'da bu ay/grup için "veri yok" görünmesi beklenir.
**2026-09-08'den beri AYRICA KPI-25'i de etkiliyor** (bu satır bu yüzden
oraya, tek başına yeterli olmadığı için, cross-reference edildi): 2016
"tam yıl + 5/5 grup" şartını karşılamadığından (59/60 satır) KPI-25'in
CAGR serisine hiç girmiyor — bu KASITLI, bir hata DEĞİL (bkz. §7.5).

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

**`prepare_threshold=None` — transaction-pooler ile ilişkili boşluk
(2026-09-07 denetiminde eklendi):** `DATABASE_URL`'nin transaction-mode
pooler'ı (pgbouncer, port 6543), her sorguyu farklı bir fiziksel bağlantıya
yönlendirebildiği için psycopg'nin varsayılan prepared-statement önbelleği
ile çakışıyordu — canlıda `psycopg.errors.DuplicatePreparedStatement`
hatasına yol açmıştı (bkz. `06_canli_veri_operasyon_gunlugu.md` satır
189-193). Kalıcı çözüm: `psycopg.connect(..., prepare_threshold=None)` —
bu, `worker/db.py:get_db_connection()`'daki tek merkezi noktadan başlayıp,
kendi bağlantısını açan HER script'e (auth.py, job_worker.py,
fetch_weather.py, backfill/onayla/mutabakat/word_20XX.py) tek tek
uygulandı. `DATABASE_URL_DASHBOARD` (session-mode) bu sorunu yaşamıyor
ama tutarlılık için orada da aynı parametre kullanılıyor.
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

1. **T8/T12 karışıklığı — bu maddenin İLK hâli (v1.0) YANLIŞTI, 2026-09-07
   denetiminde geri alındı:** Önceki bir özet notu "T12, T8 gibi parse
   edilmiyor" diyordu. v1.0 bunu, `05_kaynak_dosya_sozlesmesi.md` satır
   20'yi (dosyanın **hedef haritası**, yani plan — kod değil) kaynak
   göstererek "YANLIŞ, T8 gerçekten parse edilip `fact_tuketim`'i
   besliyor" diye "düzeltmişti". Bu düzeltmenin kendisi yanlıştı: aynı
   dosyanın satır 105'i ve `worker/parser.py`/`worker/pipeline.py`'nin
   kendisi, T8'in **hiç implemente edilmediğini** açıkça söylüyor —
   `grep -rn "T8" worker/parser.py worker/pipeline.py` bunu doğrudan
   doğruluyor. **Doğrusu orijinal nota daha yakın:** hem T8 hem T12,
   T11 ile redundant olduğu için parse edilmiyor (aralarındaki tek fark:
   T12'nin grain'i farklı — dağıtım şirketi — ama sonucu aynı). v1.0'ın
   hatası, dokümanın kendi yöntem kuralını ("çelişkide kod esas alınır")
   burada ihlal edip bir hedef/plan satırını kod sanmasıydı. Düzeltildi,
   bkz. §4.2/§4.3 (v1.1).
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
| KPI (Faz 0-3 production) | 20 | KPI-01..13, 23..27 (KPI-14..22 SRS'te tanımlı değil/bu repoda hiç geçmiyor; **KPI-28** `05_kaynak_dosya_sozlesmesi.md`'de tanımlı ama kodda implemente edilmemiş — bkz. §7.5, yeni KPI KPI-29'dan başlamalı) |

