# ADR-7 — Sunum Katmanı: Streamlit (Faz 2), Next.js Ertelendi

**Tarih:** 2026-08-30 · **Durum:** Kabul edildi

## Bağlam
dokumanlar/01_kavramsal_tasarim.md §3 (Mimari), sunum katmanını
"Next.js + TypeScript (app/)" olarak tanımlıyordu. Ancak proje halihazırda
çalışan bir `app/dashboard.py` (Streamlit) ile ilerliyordu ve Faz 2
(Dashboard) kapsamı netleştirilirken bilinçli olarak Next.js'e GEÇİLMEDİ,
mevcut Streamlit paneli büyütüldü. Bu ADR, dokümanla gerçek durum
arasındaki bu farkı ve gerekçesini kayıt altına alır.

## Karar
Faz 2'de sunum katmanı **Streamlit** (`app/dashboard.py`) olarak kalır ve
gerçek `worker/analytics.py` sorgularıyla büyütülür. **Next.js + TypeScript'e
geçiş iptal edilmedi** — `dokumanlar/01_kavramsal_tasarim.md` §7'deki
**"Son Faz" (LinkedIn yayını)** öncesine bilinçli olarak ertelendi.

## Gerekçe
- **Hız:** Faz 0/1'de kurulan worker/ katmanı (parser, kpi, ingest, pipeline,
  job_worker) zaten Python. Streamlit aynı süreçte, ek bir API katmanı
  (FastAPI + REST/GraphQL sözleşmesi) veya ayrı bir frontend build zinciri
  kurmadan `worker/*.py` fonksiyonlarını doğrudan çağırabiliyor — Next.js
  bu ayrımı zorunlu kılardı (worker Python, sunum TypeScript; aralarında
  bir API katmanı gerekir).
- **Kapsam eşleşmesi:** Faz 2'nin hedefi "Dashboard (KPI görselleştirme)" —
  çok kullanıcılı, marka kimlikli bir web uygulaması değil, veri
  ekibinin/paydaşların KPI'ları görebileceği tek bir iç panel. Streamlit
  bunun için yeterli ve fazla mühendisliksiz.
- **Erteleme, iptal değil:** Next.js'in asıl gerekçesi (marka kimlikli,
  SEO'lu, halka açık bir dashboard) yalnız **"Son Faz"** (LinkedIn yayını,
  §7) civarında gerçekten gerekli olur — o zamana kadar erteleme, gereksiz
  erken yatırımdan kaçınır.

## Sonuçlar
- `app/dashboard.py` büyümeye devam eder; DB bağlıysa `worker/analytics.py`
  üzerinden gerçek sorgu, yoksa `data/tr_ocak2026.py` statik yedek.
- `worker/` katmanı framework-agnostik kalmalı (Streamlit'e bağımlı kod
  yalnız `app/` içinde) — ileride Next.js'e geçilirse `worker/*.py`
  (parser/kpi/ingest/pipeline/analytics) DEĞİŞMEDEN bir FastAPI katmanının
  arkasına konabilir.
- **RLS notu:** `worker/analytics.py`, `DATABASE_URL` üzerinden doğrudan
  psycopg ile bağlanır — bu genelde RLS'ten muaf bir rol demektir
  (service_role/postgres, bkz. `supabase/migrations/20260819_0002_rls_roles.sql`).
  Faz 2 tek-kullanıcılı geliştirme/iç panel kapsamında bu kabul edilebilir;
  **çok kullanıcılı erişime geçildiğinde** (kullanıcı bazlı auth, dışa açık
  dashboard) `analytics.py`'nin doğrudan `DATABASE_URL` yerine bir Supabase
  `authenticated` istemcisine (kullanıcının oturumuna bağlı, RLS politikaları
  uygulanan) geçmesi gerekir — bu, bu ADR'nin ve Faz 2'nin kapsamı DIŞINDA
  bırakılmıştır, ileride sürpriz olmaması için burada not edilir.
- **RLS notu, ek bulgu (2026-09-03):** Yukarıdaki geçişi karmaşıklaştıran
  somut bir kısıt bulundu — bu projenin `viewer`/`data_operator`/`admin`
  rol-değiştirme modeli (RLS politikaları `TO viewer` vb.), `DATABASE_URL`'in
  geçtiği Supabase transaction-mode connection pooler'ıyla (Supavisor)
  UYUMSUZ olabilir: canlı Supabase'e karşı `postgres` kullanıcısıyla (bu
  rollerin GERÇEK üyesi olduğu `pg_auth_members`'la doğrulandı) `SET ROLE
  viewer` denendi, "permission denied to set role" ile reddedildi —
  transaction-mode pooler'ların SET ROLE gibi session-durumu değiştiren
  komutları (bağlantı havuzda paylaşıldığından, bir istemcinin rol
  değişikliği başka bir istemciye sızmasın diye) kısıtlaması bilinen bir
  davranıştır. **Şu an SORUN DEĞİL** — Faz 2 dashboard'u tek-kullanıcılı,
  yalnız `DATABASE_URL` (RLS'ten muaf bağlantı) yolunu kullanıyor,
  yukarıdaki `authenticated`/RLS yolu hiç tetiklenmiyor. **Ama çok-kullanıcılı
  erişim inşa edilmeden ÖNCE** bu çözülmeli — ya PostgREST/Supabase'in
  `anon`/`authenticated` gibi kendi yönettiği rollerine (pooler'ın zaten
  desteklediği, `db-role-claim-key` mekanizmasıyla) geçilmeli, ya da
  connection pooling'i bypass eden DOĞRUDAN (session-mode) bir bağlantı
  kullanılmalı. Detay/tekrar üretme adımları: `dokumanlar/
  06_canli_veri_operasyon_gunlugu.md` (2026-09-02, "auth schema USAGE"
  bölümü).
- **RLS notu, KESİN KÖK NEDEN bulundu (2026-09-05, yalnız TEST — kod/şema
  değişikliği YAPILMADI):** Yukarıdaki "transaction-mode pooler kısıtlıyor"
  hipotezi **YANLIŞ ÇIKTI** — session-mode bir bağlantıyla (aynı Supavisor
  pooler host'u, port 5432, transaction-mode'un 6543'ünden farklı; bkz.
  `.env`'deki `DATABASE_URL_DIRECT`) `postgres` kullanıcısıyla `SET ROLE
  viewer` **AYNI hatayla** ("permission denied to set role") reddedildi —
  yani sorun pooler modu DEĞİL, aşağıdaki gerçek neden:

  **Gerçek kök neden — PostgreSQL 17'nin (canlı DB'nin sürümü, `SHOW
  server_version` ile doğrulandı) ayrık `SET` yetkisi:** `pg_auth_members`
  (PG16+'da üç ayrı sütun taşıyor: `admin_option`, `inherit_option`,
  `set_option`) sorgulandığında, `postgres`'in `viewer`/`data_operator`/
  `admin`'e üyeliği **`admin_option=true` ama `inherit_option=false` VE
  `set_option=false`** — buna karşılık `authenticated`/`service_role`
  üyelikleri **`inherit_option=true` VE `set_option=true`** (Supabase'in
  kendi yönettiği roller, farklı grantlanmış). `SET ROLE`/`SET SESSION
  AUTHORIZATION` PG16+'da AÇIKÇA `set_option=true` gerektirir — üyelik
  (`pg_has_role(...,'MEMBER')`) VARLIĞI tek başına YETMİYOR. Bu proje
  `20260819_0002_rls_roles.sql`'de `viewer`/`data_operator`/`admin`
  rollerini muhtemelen düz `GRANT role TO grantee;` (varsayılan `SET`
  seçeneği grantee'nin KENDİ `rolinherit`'inden BAĞIMSIZ, PG'nin kendi
  varsayılanına göre `false` kalabiliyor) ile grantlamış — bu satır
  `WITH SET TRUE` içermiyor.

  **JWT/`current_app_role()` mekanizmasının KENDİSİ ÇALIŞIYOR** (bu kısım
  test edildi ve BAŞARILI): `auth.jwt()`'nin gerçek tanımı sorgulandı
  (varsayılmadı) — `coalesce(current_setting('request.jwt.claim',true),
  current_setting('request.jwt.claims',true))::jsonb` okuyor. Aynı
  session'da `SET request.jwt.claims = '{"app_metadata":{"role":
  "viewer"}}';` çalıştırılıp `SELECT public.current_app_role();` çağrıldı
  — **`'viewer'` DÖNDÜ, doğru çalıştı.**

  **Yapısal ek bulgu:** RLS politikaları `FOR SELECT TO viewer USING
  (current_app_role()='viewer' AND ...)` şeklinde **ÇİFT kapılı** — hem
  PostgreSQL'in FİZİKSEL rol hedeflemesi (`TO viewer`, oturumun GERÇEKTEN
  `viewer` rolüne geçmiş/onu miras almış olmasını gerektirir) HEM
  `current_app_role()`'ün (JWT claim okuyan) doğru değeri döndürmesi
  gerekiyor. Standart bir Supabase Auth oturumu `authenticated` rolüyle
  bağlanır — bu politikaların GERÇEKTEN tetiklenmesi için ya backend'in
  elle `SET ROLE viewer` yapması ya da PostgREST'in `db-role-claim-key`
  mekanizmasının (JWT claim'ine göre örtük `SET ROLE` yapar) devrede
  olması gerekir — İKİSİ de AYNI eksik `set_option=true` grantına takılır.

  **Sonuç — Faz B'yi planlarken:** Engel connection-mode/pooler DEĞİL,
  TEK bir migration'lık bir grant eksikliği: `viewer`/`data_operator`/
  `admin` rollerinin ilgili tarafa (muhtemelen `authenticated`, karar
  Ahmet'e ait) `WITH SET TRUE` (muhtemelen `WITH INHERIT TRUE, SET TRUE`)
  granti verilmesi gerekiyor. **Bu görevde UYGULANMADI** (kod/şema
  değişikliği bu görevin kapsamı dışıydı) — yalnız teşhis edildi. Test
  scripti (`worker/scripts/gecici_rol_testi.py`) GEÇİCİYDİ, iş bitince
  silindi, commit'lenmedi. Hiçbir gerçek kullanıcı/rol/`auth.users` satırı
  oluşturulmadı; yalnız `SELECT`/session-yerel `SET` çalıştırıldı, hepsi
  `ROLLBACK` edildi.

- **Faz B adım 1 UYGULANDI (2026-09-05) — özel servis rolü + 3 BAĞIMSIZ ek
  bulgu, hepsi çözüldü, `viewer` uçtan uca DOĞRULANDI:**

  **1) Migration `20260819_0016`:** `postgres` YERİNE dar yetkili
  `app_dashboard_service WITH LOGIN` oluşturuldu; `viewer`/`data_operator`/
  `admin`'e `WITH INHERIT FALSE, SET TRUE` grantlandı (yukarıdaki kök
  nedeni doğrudan çözer — en az ayrıcalık: varsayılan hiçbir tablo
  erişimi yok, yalnız açık `SET ROLE` ile). Şifre migration dosyasında
  DEĞİL — canlıya doğrudan `ALTER ROLE ... PASSWORD` ile ayrıca verildi,
  `.env`'e yeni `DATABASE_URL_DASHBOARD` olarak eklendi (gitignored).
  **Doğrulandı:** `SET ROLE viewer/data_operator/admin` artık hatasız.

  **2) BAĞIMSIZ bulgu — Migration `20260819_0017`:** `SET ROLE` çalışır
  hale gelince YENİ bir hata çıktı: `SELECT ... FROM fact_tuketim`
  "permission denied for table". Kök neden: `20260819_0003_fix_grants.
  sql`'in `REVOKE ALL PRIVILEGES ON ALL TABLES ... FROM viewer,
  data_operator, admin;` satırı, `0002_rls_roles.sql`'in bu üç role
  verdiği TÜM tablo grant'larını (dim_*, fact_tuketim, fact_uretim,
  fact_abone, fact_serbest_tuketici, fact_hava_aylik, source_asset,
  ingestion_batch, audit_log) 2026-08-19'dan beri SİLMİŞ — yalnız
  `veri_kapsam_disi` (0012/0013) ve `fact_hava_aylik_log` (0009) dar
  istisnalarla geri verilmiş, geri kalan HİÇ restore edilmemiş.
  `worker/validate_role_access.py`'nin CI testi yalnız `veri_kapsam_disi`'yi
  test ettiğinden bu boşluk hiç yakalanmamıştı. 0017, 0002'nin orijinal
  grant'larını birebir geri veriyor.

  **3) BAĞIMSIZ bulgu — auth şemasına ASLA GRANT verilemiyor, migration
  `20260819_0018`:** 0017'den sonra bu kez `current_app_role()` içindeki
  `auth.jwt()` çağrısı "permission denied for schema auth" ile
  reddedildi — `20260819_0015`'in `GRANT USAGE ON SCHEMA auth TO viewer,
  data_operator, admin;` ifadesi canlı Supabase'de HİÇ etkili olmamış
  (hatasız çalışıyor GÖRÜNÜYOR ama `has_schema_privilege(...)` işlem
  İÇİNDE bile false dönüyor). Kök neden: `auth` şeması `supabase_admin`'e
  ait; `postgres` üzerinde USAGE var ama **WITH GRANT OPTION YOK**
  (`has_schema_privilege('postgres','auth','USAGE WITH GRANT OPTION')` =
  false) — Supabase'in yönetilen platformu `postgres`'in bu izni BAŞKA
  rollere devretmesini sessizce engelliyor. **Çözüm — `auth` şemasına
  DOĞRUDAN erişim vermek YERİNE**, zaten `postgres` sahipliğindeki
  `public.current_app_role()`'ü **`SECURITY DEFINER`** yapmak (0018):
  fonksiyon artık ÇAĞIRANIN değil SAHİBİNİN (`postgres`, kendi `auth.
  jwt()` erişimi VAR) yetkisiyle çalışıyor — çağıranın `auth` şema
  erişimine hiç ihtiyaç kalmıyor. Güvenlik notu: fonksiyon yalnız
  çağıranın KENDİ oturumunun JWT'sini okuyup filtrelenmiş bir rol string'i
  döndürüyor, ek bir yetki yükseltmesi YAPMIYOR.

  **UÇTAN UCA DOĞRULAMA (canlı Supabase, `app_dashboard_service` ile,
  2026-09-05):** `viewer` artık TAM beklenen gibi çalışıyor — JWT claim'i
  YOKKEN `current_app_role()` NULL, `fact_tuketim` sorgusu **0 satır**;
  DOĞRU JWT claim'iyle `current_app_role()`='viewer', sorgu **41.547
  satır** (is_active=true kesiti) döndürüyor.

  **4) `admin`/`data_operator` bypass politikaları — ÇÖZÜLDÜ (2026-09-05,
  migration `20260819_0019`):** Bir önceki turda `admin`/`data_operator`
  için, JWT claim'i OLMADAN BİLE `fact_tuketim` sorgusunun TÜM satırlarını
  (44.458) döndürdüğü bulunmuştu — `current_app_role()` kontrolünü
  ATLIYORLARDI. Kaynak: `pg_policy`'de, HİÇBİR migration dosyasında
  olmayan 14 politika — her fact/source tablosunda (`fact_tuketim`,
  `fact_abone`, `fact_uretim`, `fact_serbest_tuketici`, `fact_hava_
  aylik`, `source_asset`, `ingestion_batch`) `admin_<tablo>_manage` ve
  `data_operator_<tablo>_manage` adında, **`USING (true)` — KOŞULSUZ**
  politikalar.

  **Adli inceleme (2026-09-05) KAYNAĞI KESİN OLARAK belirledi** — tahmin
  değil, doğrudan git kanıtı: `git stash list` BOŞ (stash yok, hipotez
  orada değil) — ama `git log --all -S"admin_fact_manage"` ile bu tam
  isimlerin `db/schema.sql`'in EN İLK taslağında (commit `453a2d4`,
  "Agent host session aa19b6d3-a4a3-4226-9d42-acb526deab0b - turn 1",
  2026-08-19 00:53) BİREBİR olduğu bulundu. `git merge-base --is-ancestor
  453a2d4 HEAD` **false** döndü — yani bu commit (ve aynı oturumun turn
  2/turn 3'ü) `main` dalının atası DEĞİL: aynı erken oturumun SONRAKİ
  adımında (turn 3, commit `5f7b173`) BU politikalar ÇOKTAN daha güvenli,
  `current_app_role()`-tabanlı isimlerle (`admin_fact_tuketim_all` vb.)
  DEĞİŞTİRİLMİŞ, ve o güvenli hâli `main`'e (PR #6, commit `b674592`)
  birleştirilmiş — `ADR-8`'in bahsettiği `0004_fix_rls_policies.sql`/
  `0005_harden_service_role_grants.sql` isimleriyle DOĞRUDAN eşleşme
  YOK (farklı bir taslak/oturum), ama AYNI kalıp: erken bir taslak canlı
  DB'ye uygulanmış, `main`'e hiç girmeden terk edilmiş. En olası açıklama:
  ilk taslak (turn 1) aynı erken oturumda doğrudan canlı Supabase'e
  uygulanmış; `main`'deki güvenli sürüm (AYNI dosya adı `0002_rls_roles.
  sql`, FARKLI/daha dar içerik) sonradan AYRICA uygulanınca yeni
  politikalar EKLENDİ ama eskiler hiç `DROP` edilmedi (migration'lar
  yalnız `CREATE POLICY` yapar, adı farklı eski politikaları otomatik
  temizlemez) — iki nesil politika CANLIDA YAN YANA kaldı.

  **Bağımsız güvenlik teyidi (RLS'nin "şu an işlevsel risk yok" iddiası
  DEVRALINMADI, ayrıca doğrulandı):** `worker/` ve `app/` içinde `grep`
  ile tarandı — `admin`/`data_operator`'a `SET ROLE` yapan HİÇBİR
  ÇALIŞTIRILABİLİR kod yolu YOK (yalnız `worker/validate_role_access.py`
  `anon`/`viewer`'ı test ediyor — `admin`/`data_operator`'ı hiç
  kapsamıyor; `app/dashboard.py`'deki eşleşmeler yalnız açıklayıcı YORUM
  METNİ, çalıştırılabilir kod DEĞİL).

  **Kaldırma:** `20260819_0019_drop_undocumented_bypass_policies.sql` —
  14 politikanın HER BİRİ için AYRI, AÇIK `DROP POLICY IF EXISTS <ad> ON
  <tablo>;` satırı (wildcard/dinamik silme yok). Canlı Supabase'e
  uygulandı, doğrulandı: `SELECT count(*) FROM pg_policies WHERE
  policyname LIKE '%_manage'` → **0**.

  **Uçtan uca YENİDEN doğrulama (canlı, `app_dashboard_service` ile,
  kaldırma SONRASI):**
  - `viewer` DEĞİŞMEDİ (regresyon yok): JWT'siz 0, doğru JWT ile 41.547.
  - `admin` artık DOĞRU şekilde gated: JWT'siz **0**, doğru JWT ile
    **44.458** (`admin_fact_tuketim_all` politikası artık TEK başına
    karar veriyor).
  - `data_operator`: JWT'siz VE doğru JWT ile İKİSİNDE de **0** — bu
    BEKLENEN davranış, regresyon DEĞİL: `0002_rls_roles.sql`'in orijinal
    tasarımında `data_operator`'ın `fact_tuketim` üzerinde yalnız
    `INSERT`/`UPDATE` politikası var, `SELECT`/`ALL` politikası HİÇ YOK
    — düz bir `SELECT` sorgusu bu yüzden 0 satır görür (tasarım gereği,
    veri operatörü yükler/günceller, `viewer` gibi taramaz).

  **`app/dashboard.py`'de `st.session_state`'e geçiş:** `@st.cache_
  resource` (parametresiz, TÜM kullanıcılar arasında TEK paylaşımlı
  bağlantı) kaldırıldı — her Streamlit oturumu artık KENDİ bağlantısını
  açıyor (`st.session_state`).

- **Faz B — TAMAMLANDI (2026-09-05): gerçek giriş ekranı + Ahmet'in admin
  hesabı.** Panel artık uçtan uca kimlik doğrulamalı — mekanizma:

  1. **`worker/auth.py`** (framework-agnostik, ADR-7 ilkesi): `giris_yap
     (email, sifre)` Supabase Auth'a (`sign_in_with_password`) karşı
     doğrular, başarılı oturumun GERÇEK JWT'sini çözüp `app_metadata.
     role`'ü okur (rol bilinen üçlüden [viewer/data_operator/admin]
     biri DEĞİLSE erişim reddedilir, sessizce `viewer` VARSAYILMAZ).
     `rol_baglantisi_ac(jwt_claims_json, rol)` `DATABASE_URL_DASHBOARD`
     (`app_dashboard_service`) ile YENİ bir bağlantı açar, `request.
     jwt.claims`'i gerçek JWT ile set eder, `SET ROLE <rol>` yapar —
     `rol` HER ZAMAN whitelist'e karşı doğrulanır (whitelist dışıysa
     `SET ROLE`'e hiç ulaşmadan `ValueError`; ayrıca `psycopg.sql.
     Identifier`/`Literal` kullanılır, ham string birleştirme YOK).
  2. **`app/dashboard.py`:** `DATABASE_URL_DASHBOARD` yapılandırılmışsa
     panel HER ZAMAN bir giriş ekranı (`st.form`, e-posta+şifre) gösterir
     — eski, girişsiz `DATABASE_URL` yolu ARTIK KULLANILMAZ (yoksa giriş
     ekranı dekoratif kalırdı). `DATABASE_URL_DASHBOARD` hiç
     yapılandırılmamışsa (yerel/offline geliştirme) eski davranış AYNEN
     korunur, giriş ekranı da hiç gösterilmez. Başarısız girişte GENEL
     bir hata ("E-posta veya şifre hatalı") — hesabın var olup olmadığı
     SIZDIRILMAZ. Sidebar'da "Çıkış Yap" butonu (bağlantıyı kapatır,
     `session_state`'i temizler, `st.rerun()`).
  3. **Ahmet'in hesabı** — Supabase Admin API (`auth.admin.create_user()`,
     GERÇEK `service_role` key ile — `.env`'deki `SUPABASE_SERVICE_ROLE_
     KEY` başlangıçta yanlışlıkla anon key'in kopyasıydı, Ahmet'in
     dashboard'dan aldığı gerçek değerle düzeltildi) ile oluşturuldu:
     `a.damar61@windowslive.com`, `app_metadata.role="admin"`,
     `email_confirm=true`, rastgele üretilmiş güçlü bir şifre (yalnız
     terminalde Ahmet'e gösterildi — hiçbir commit/log/PR'a yazılmadı).
     Oluşturma script'i GEÇİCİYDİ (repo dışında, scratchpad'de
     çalıştırıldı), iş bitince silindi.

  **Uçtan uca CANLI doğrulama (2026-09-05):** Ahmet'in gerçek hesabıyla
  `giris_yap()` çağrıldı → `rol='admin'` doğru okundu →
  `rol_baglantisi_ac()` ile açılan bağlantıda `current_app_role()`→
  `'admin'`, `fact_tuketim`→**44.458** satır, `fact_abone`→**25.110**
  satır erişilebilir (migration 0019'un kaldırdığı 14 bypass
  politikasından SONRAKİ, DOĞRU `current_app_role()`-gated erişimle).
  Yanlış şifre VE var olmayan e-posta — İKİSİ de `giris_yap()`'tan
  `None` döndü (aynı, ayırt edilemeyen sonuç — hangi durumun
  gerçekleştiği sızdırılmadı). `worker/validate_role_access.py` CI'da
  hâlâ geçiyor (bu turda hiçbir migration/politika değişmedi).

  **Yeni kullanıcı eklemek (script silindiği için — adımlar, kod DEĞİL):**
  1. Supabase dashboard → Authentication → Users → **Add user** (ya da
     Admin API'den `auth.admin.create_user()` — `email`, güçlü bir geçici
     şifre, `Auto Confirm User` işaretli).
  2. Kullanıcı oluşunca, **User Management** panelinde o kullanıcıyı aç →
     **User Metadata** DEĞİL, **App Metadata**'ya şunu ekle:
     `{"role": "viewer"}` (ya da `"data_operator"`/`"admin"` — YALNIZ bu
     üç değer geçerli, `worker/auth.py:GECERLI_ROLLER`).
  3. Kullanıcıya geçici şifreyi güvenli bir kanaldan ilet — panelin kendi
     "şifre sıfırlama" akışı henüz yok, ilk girişte Supabase dashboard'dan
     elle bir yeni şifre atanabilir (**Reset password**).
  4. Kod değişikliği/deploy GEREKMEZ — `worker/auth.py` `app_metadata.
     role`'ü DİNAMİK okur, yeni kullanıcı bir sonraki girişinde otomatik
     çalışır.

## Değerlendirilen Alternatifler
- **Next.js + TypeScript (şimdi):** Reddedildi — Faz 2 kapsamına göre erken;
  worker/ ile arasına bir API katmanı (FastAPI) kurmayı da gerektirirdi,
  bu da ayrı bir ADR/iş kalemi olurdu.
- **FastAPI + basit HTML/Jinja:** Değerlendirilmedi — Streamlit zaten
  çalışıyordu ve pandas/DataFrame tabanlı KPI gösterimine Jinja'dan daha
  uygun.
