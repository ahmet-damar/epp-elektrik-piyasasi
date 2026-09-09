# 09 — Proje Durumu (GÜNCEL, DB'den doğrulandı — 2026-09-04, 2026-09-07'de
fact_tuketim_ulke_geneli eklemesiyle, 2026-09-08'de Aşama 1 kapanışıyla
güncellendi)

> **STATUS: LIVE (güncel durum)** — bu dosya ve `10_TEKNIK_MASTER_
> DOKUMAN.md`, değişen sayı/durumun YAŞADIĞI tek iki yerdir; diğer
> `dokumanlar/` dosyaları yalnız değişmeyen sözleşmeyi tutar (bkz.
> `10_TEKNIK_MASTER_DOKUMAN.md` → "Doküman Yönetim Kuralı" bölümü).

**Bu dosya, canlı Supabase'e karşı salt-okunur sorgularla ve `pytest`
çalıştırılarak bu turda TAZE DOĞRULANMIŞ bulgulara dayanır — önceki
(2026-09-03 tarihli) sürümün sayıları devralınmadı, hepsi yeniden
sorgulandı. Aradan geçen sürede tamamlanan iş kalemleri (regresyon
testleri, GRANT/RLS düzeltme zinciri, dashboard entegrasyonu) aşağıda
yansıtıldı.**

## TL;DR

- **T11 (fact_tuketim, tüketim):** 2016-01 → 2025-12 arası **120/120 ay
  aktif**, sıfır eksik.
- **T10 (fact_abone, abone sayısı):** yalnız **2021-11'den itibaren**
  aktif (2016-2020 tam yıllar + 2021 Ocak-Ekim, kaynakta il×grup kırılımı
  YAPISAL OLARAK yok). 2021-11 → 2025-12 arası **50/50 ay aktif**.
- **T4 (fact_uretim, lisanssız kurulu güç):** 120 aydan yalnız **2022-07
  eksik** (kalıcı kaynak hatası). **119/120 ay aktif.**
- **`veri_kapsam_disi` artık 2016-2025'in TAMAMINI kapsıyor** (önceki
  turda yalnız 2023-2025'ti) — `fact_serbest_tuketici` 120 kayıt (Karar 1,
  T13 hiçbir Word yılında yok), `fact_uretim` 121 kayıt (120×Lisanslı +
  1×2022-07 Lisanssız, Karar 3), `fact_abone` 70 kayıt (T10'un yapısal
  eksikliği).
- **Regresyon testleri — TAMAMLANDI (bugün kapandı).** `word_2016.py`'den
  `word_2025.py`'ye kadar **10 yılın 10'unda da** dedike pytest testi var
  (`worker/tests/test_word_2016.py` … `test_word_2025.py`) — önceki
  turda "2023-2025 eksik" denen açık madde bugün 36 yeni testle kapandı.
- **GRANT/RLS düzeltme zinciri — TAMAMLANDI.** `public` şemasındaki 18
  tablonun **hiçbiri artık grant'sız değil** (`viewer`/`data_operator`/
  `admin`), **hiçbir tabloda RLS-açık-ama-policy-yok deseni kalmadı**
  (4 migration: `20260904_0001`-`0004`) — panel artık admin/viewer
  girişiyle gerçekten çalışıyor (önceden `permission denied`/sessiz
  boş-sonuç veriyordu).
- **`veri_kapsam_disi` dashboard'a bağlandı** — seçili dönem için
  "kaynakta yok" işaretli veri varsa panel artık sessiz boşluk yerine
  açıklayıcı bir bilgi kutusu gösteriyor.
- **KPI-25/KPI-27 — TAMAMLANDI, kaynak kararı uygulandı (2026-09-08,
  Aşama 2/C5).** KPI-25 (resmi "toplam tüketim" CAGR) TAMAMEN
  `fact_tuketim_ulke_geneli`'ye taşındı (tam yıl + 5/5 grup şartı, il
  bazlı `fact_tuketim` ile ASLA karıştırılmıyor) — artık canlıda GERÇEK
  bir değer üretiyor: **+%3,1** (2017→2025, n=8; 2016 kasıtlı hariç —
  2016-12 Tarımsal kaynakta hiç yüklenmedi). Önceden sürekli
  'hesaplanamaz' dönüyordu, bu GERÇEK bir fonksiyonel iyileştirme. KPI-27
  (Sanayi-hariç, il bazlı `fact_tuketim`, DEĞİŞMEDİ) canlıda **+%3,8**
  (2016→2025, n=9). Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §7.5/§11.2.
- **pytest** (`worker/tests`, 6 `*_integration.py` hariç): temiz bir
  ortamda (`env -i`, DB env değişkeni yok) **227/227 geçti**, 0 hata —
  bkz. "Test durumu" bölümü ve `10_TEKNIK_MASTER_DOKUMAN.md` §9.4
  (v1.1'de 227 vs 230 karışıklığı çözüldü).
- **fact_tuketim_ulke_geneli — TAMAMLANDI (2026-09-07).** EPDK T11
  tablosunun kendi "Genel Toplam" satırından, il kırılımı olmayan,
  Sanayi DAHİL tüm grupların ülke geneli serisi. 2016-2025'in 120 ayının
  TAMAMI aktif (599 satır) — yalnız 2016-12 4/5 grupla (Tarımsal o ay
  kaynakta negatif çıktığı için hiç yüklenmedi, kullanıcı onayıyla kabul
  edildi). İlk backfill'de 39 ay mutabakat "uyumsuz" görünmüştü — kök
  neden bulundu (veri hatası DEĞİL, `dogrula_tuketim()`'in negatif değer
  reddi il vs ülke seviyesinde bağımsız uygulanmasının beklenen sonucu),
  `worker/scripts/mutabakat_ulke_geneli.py` ile kalıcı olarak düzeltildi.
  Detay: `06_canli_veri_operasyon_gunlugu.md` 2026-09-05/07 ve 2026-09-07
  kayıtları.
- **Sanayi'nin Word kaynağında neden T11'e girmediği sorusu — KAPANDI.**
  Cevap: T11'in kendi Genel Toplam satırı zaten Sanayi dahil tüm
  grupların ülke geneli değerini veriyor (yukarıdaki madde) — `07_word_
  parser_kapsam.md`'deki "ileride araştırılabilir" notu artık geçerli
  değil, kapatıldı.
- **Aşama 1 (operasyonel güvenlik, 2026-09-07) — TAMAMLANDI (C2/B2/C1/
  C3/C4).** Prod DB'ye karşı test guard'ı kod seviyesinde eklendi (C2),
  CI/deploy migration asimetrisi kapatıldı (B2, gerçek CI koşusuyla
  doğrulandı), yedekleme runbook'u GERÇEK bir restore drill'iyle
  doğrulandı (C1 — Supabase Free plan'de otomatik yedek YOK, bkz.
  `11_yedekleme_runbook.md`), scheduled-refresh sessiz başarısızlığa
  karşı iki katman savunma kazandı (C3), **8 tabloda RLS geri açıldı ve
  canlıya uygulandı** (C4 — `dim_*`×5 + `sistem_parametre`/`kpi_esik`/
  `job_status`; `02_srs_ozet.md`'nin "TÜM tablolarda RLS zorunlu" kuralı
  artık belgelenmemiş istisnasız gerçeğe uyuyor; istisnasız bir tamlık
  kontrolü — `worker/validate_role_access.py` — hem gerçek CI'da hem
  canlıda doğrulandı: 19/19 tablo RLS+policy). C4 uygulaması sırasında
  3+ saattir açık kalmış terk edilmiş bir Streamlit bağlantısı
  `pg_terminate_backend()` ile temizlendi (veri kaybı riski yoktu, salt-
  okunurdu) — detay `06_canli_veri_operasyon_gunlugu.md` 2026-09-07
  kaydı. Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §8.2/§8.5/§9.1/§9.3/§9.4,
  Sürüm Geçmişi v1.3-v1.7.
- **Kapsam dışı bırakılan (ayrı karar):** C5 (KPI-25/27'nin
  `fact_tuketim_ulke_geneli`'yi kullanıp kullanmayacağı) ve C6'daki diğer
  öneriler — Aşama 2'ye bırakıldı.
- **Aşama 1 kapanışı (2026-09-08) — C1'in eksik yarısı + C4'ün yan
  etkisi giderildi.** `.github/workflows/scheduled-backup.yml` eklendi
  (haftalık `pg_dump`, artifact `retention-days: 90`) — repo PUBLIC
  olduğu ve `audit_log`'da hassas veri OLMADIĞI doğrulanarak (bkz.
  `11_yedekleme_runbook.md`) şifrelemeden saklanmasına bilinçli karar
  verildi. `app_dashboard_service`'e `idle_in_transaction_session_
  timeout=30min` **canlıya uygulandı** (2026-09-07'deki 3+ saatlik kilit
  olayının TEKRARINA karşı) — gerçek bir kısa-timeout testiyle
  doğrulandı, normal kullanım etkilenmedi. (`app/dashboard.py`'nin bu
  hatayı otomatik yakalamadığı o turda bilinen bir sınırlama olarak not
  edilmişti — **2026-09-08'de Aşama 2'de KÖKÜNDEN düzeltildi, aşağıya
  bkz.**) **`scheduled-backup.yml` artık GERÇEK koşuyla UÇTAN UCA
  doğrulandı (2026-09-08, PAT'e `workflow` izni eklendikten sonra) — bu
  madde KAPANDI.** 2 gerçek CI hatası bulunup düzeltildi (pg_dump 16→17
  sürüm uyumsuzluğu, PATH sırası); üçüncü koşu başarılı oldu, artifact
  indirilip `pg_restore --list` ile içeriği incelendi, disposable
  postgres:17'ye (canlı Supabase'in kendi major sürümü) restore edilip
  **19/19 tablo canlı Supabase'in `COUNT(*)` değerleriyle birebir
  eşleşti**; 100 KB eşiği de ayrıca test edildi (gerçekten FAIL
  ettirildi, sonra geri alındı). Detay: `10_TEKNIK_MASTER_DOKUMAN.md`
  §8.2/§8.5/§9, Sürüm Geçmişi v1.8-v1.9.
- **Aşama 2 (2026-09-08) — TAMAMLANDI (C5).** KPI-25 TAMAMEN
  `fact_tuketim_ulke_geneli`'ye taşındı, KPI-27 il bazlı `fact_tuketim`'de
  kaldı (yukarıya bkz.) — karışık kaynak KPI'sı tasarımından bilinçli
  olarak kaçınıldı. `app/dashboard.py`'nin idle-in-transaction KÖK
  NEDENİ düzeltildi (`autocommit=True` + ölü bağlantıyı sessizce
  yeniden kuran `_baglanti_saglikli_mi()` mantığı) — canlıda GERÇEK
  testlerle kanıtlandı (2s timeout + 3s bekleme sonrası ikinci sorgu
  artık hata VERMİYOR; kasıtlı kapatılan bağlantı doğru tespit edilip
  saklanan JWT claim'iyle sessizce yeniden bağlandı). Yedekleme
  runbook'undaki restore hedefi `postgres:16`'dan canlı Supabase'in
  kendi sürümü `postgres:17`'ye düzeltildi, tatbikat yeniden koşuldu:
  19/19 tablo yine eşleşti, önceki turdaki tek zararsız uyarı (PG17
  `transaction_timeout` GUC'u) de ortadan kalktı. Detay:
  `10_TEKNIK_MASTER_DOKUMAN.md` §7.5/§8.2/§8.5/§11.2, Sürüm Geçmişi
  v1.10-v1.12.
- **Aşama 3 (boş KPI'ları açma) — ADIM 1-4'ün TAMAMI (kod + canlı)
  TAMAMLANDI (2026-09-08/09), Bulgu C/D kararları verilip uygulandı,
  ADIM 5 (KPI bağlama) HENÜZ BAŞLAMADI** (bkz. "Sonraki Oturum Devam
  Noktası" — tam liste orada). ADIM 1: Excel T11'in Genel Toplam satırı
  KÜMÜLATİF,
  6/6 ay (202601-202606) gerçek dosyaya karşı test edildi — de-kümülatif
  edilince T7 ile 4/6 ay birebir, 2/6 ay <%0,02 fark; **T7 değil T11
  seçildi** (2016-2025 Word ile TEK tanım). ADIM 2: `fact_tuketim_
  ulke_geneli` 2026-01..06'ya genişletildi (629 aktif satır — 599+30),
  gerçek bir de-kümülatif bug'ı bulunup düzeltildi (regresyon testiyle).
  **KPI-13 artık gerçek değer üretiyor:** 2026-06↔2025-06 için **+%7,1**
  (önceden hep 'hesaplanamaz'). ADIM 3 madde 1: ADIM 2'nin "en son
  batch'i al" düzeltmesi bile N-1'in SONRADAN değişmesine karşı sessiz
  kalıyordu — migration `20260908_0002` ile `kumulatif_tuketim_mwh`
  kolonu eklendi, yeni kalıcı script `tutarlilik_ulke_geneli_kumulatif.py`
  bu durumu AÇIKÇA yakalıyor (gerçek bir superseding senaryosuyla
  kanıtlandı). Canlıya uygulandı, mevcut 30 satır yeniden doğrulandı
  (`tuketim_mwh` değişmedi), mutabakat+tutarlılık canlıda YEŞİL. Detay:
  `10_TEKNIK_MASTER_DOKUMAN.md` §5.5-5.6, Sürüm Geçmişi v1.15-v1.16.
- **Yan olay (2026-09-08):** yukarıdaki doğrulama sırasında `worker/tests/
  conftest.py`'nin canlı-DB koruması 2026-09-02'deki İLE AYNI şekilde
  atlandı (`.env`'in kontrolden SONRA yüklenmesi) ve pytest paketi yine
  canlıya karşı çalışıp `tarih_id=209912` test kirliliği bıraktı — TESPİT
  EDİLDİ, TEMİZLENDİ (85 fact + 3 batch + 3 source_asset + 1 dim_tarih,
  audit_log korundu), koruma kalıcı düzeltilip canlıda reprodüksiyonla
  doğrulandı. Detay: `06_canli_veri_operasyon_gunlugu.md` 2026-09-08
  (devam) kaydı, Sürüm Geçmişi v1.17.

## Tablo — Yıl × Tablo Aktivasyon Durumu

| Yıl | T11 fact_tuketim | T10 fact_abone | T4 fact_uretim |
|---|---|---|---|
| 2016 | 12/12 aktif | 0/12 (kaynakta yok — tablo hiç basılmamış) | 12/12 aktif |
| 2017 | 12/12 aktif | 0/12 (kaynakta yok — il-only) | 12/12 aktif |
| 2018 | 12/12 aktif | 0/12 (kaynakta yok — il-only) | 12/12 aktif |
| 2019 | 12/12 aktif | 0/12 (kaynakta yok — il-only) | 12/12 aktif |
| 2020 | 12/12 aktif | 0/12 (kaynakta yok — il-only) | 12/12 aktif |
| 2021 | 12/12 aktif | 2/12 (yalnız Kas-Ara; Oca-Eki kaynakta yok) | 12/12 aktif |
| 2022 | 12/12 aktif | 12/12 aktif | 11/12 aktif (Temmuz kaynakta yok) |
| 2023 | 12/12 aktif | 12/12 aktif | 12/12 aktif |
| 2024 | 12/12 aktif | 12/12 aktif | 12/12 aktif |
| 2025 | 12/12 aktif | 12/12 aktif | 12/12 aktif |

Tüm "kaynakta yok" hücreleri `veri_kapsam_disi` tablosunda açık sebep
metniyle işaretli VE artık panelde (Aşama 7 entegrasyonu) kullanıcıya
görünür şekilde açıklanıyor.

## Regresyon testleri — tam liste (10/10 yıl)

| Dosya | Kapsam |
|---|---|
| `test_word_2016.py` … `test_word_2022.py` | Önceki oturumlarda yazıldı |
| `test_word_2023.py` (13 test) | Bugün eklendi — 4 "Kamu/Özel" varyantı, ADIYAMAN* dipnotu, HAKKÂRİ inceltme işareti |
| `test_word_2024.py` (11 test) | Bugün eklendi — tek şablon, Linyit dahil kaynak kolonları |
| `test_word_2025.py` (12 test) | Bugün eklendi — tek şablon, Nisan 2025 Aydınlatma deseni notu |

Hepsi `grup_esle_zorunlu`/`kaynak_esle_zorunlu`/`t11_oku`/`t10_oku`/
`t4_oku` düzeyinde, synthetic in-memory docx tablolarıyla, `DATABASE_URL`
bağımsız — CI'nin 'Worker' job'ında (canlı DB yok) da çalışır.

## GRANT/RLS düzeltme zinciri (2026-09-04, 4 migration)

`20260819_0002_rls_roles.sql`'in GRANT/RLS kapsamı baştan eksikti — canlı
kullanımda (Streamlit Cloud'da admin girişiyle) `permission denied for
table dim_tarih` ve ardından sessiz sıfır-satır sonuçları olarak ortaya
çıktı. 4 ayrı migration'la kapatıldı:
- `20260904_0001` — 5 `dim_*` tablosuna `data_operator`/`admin` için
  eksik `GRANT SELECT`.
- `20260904_0002` — aynı 5 tabloda policy'siz açık kalmış RLS `DISABLE`.
- `20260904_0003` — `sistem_parametre`/`kpi_esik`/`job_status` için
  (hiç grant almamışlardı) eksik GRANT'lar.
- `20260904_0004` — bu 3 tabloda da bulunan AYNI policy'siz-RLS deseni
  `DISABLE`.

Doğrulandı (bu turda yeniden sorgulandı): `public` şemasındaki 18
tablonun hiçbiri artık ne grant'sız ne RLS-açık-policy'siz. Detay:
`dokumanlar/06_canli_veri_operasyon_gunlugu.md`, 2026-09-04 girdisi.

## Test durumu (2026-09-07'de temiz bir kabukta yeniden doğrulandı)

```
env -i PATH=... HOME=/root python -m pytest worker/tests --collect-only -q
# 19 non-integration dosya TEK BAŞINA:
227 tests collected
```

**Not (bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §9.4/v1.1):** Bu oturumun daha
önceki bir WSL koşusunda görülen "230 passed" rakamı **yanlış değildi ama
genel bir sabit de değildi** — o koşuda `test_auth_integration.py`
(`DATABASE_URL_DASHBOARD` tanımlı olduğu için) yanlışlıkla dışlanmadan
gerçekten çalışmış ve 3/3 geçmişti (227 yerel + 3 gerçek Supabase Auth
çağrısı = 230). README Ek D kuralına göre **6** `*_integration.py`
dosyasının tamamı normal koşuda hariç tutulur; standart/ortam-bağımsız
rakam **227**'dir.

(2026-09-04'teki 205'ten artış: `test_word_ulke_geneli.py` (7),
`test_auth.py`'ye eklenen rate-limit testleri (6), ve aradaki diğer
turlarda eklenen testler — tam kırılım doğrulanmadı, yalnız toplam 227
`--collect-only` ile teyit edildi.)

## Sıradaki adımlar (teknik borç DEĞİL — ürün/kapsam kararları)

1. **2022 ve öncesi yıllara Word genişletmesi tamamlandı** — genişleme
   listesinde teknik olarak kalan bir yıl yok (2016-2025 hepsi aktif).
2. **Faz 4 (Tahminleme) / Faz 5 (EPİAŞ)** — daha önce ertelenmişti,
   artık 10 yıl gerçek veri var, karar gözden geçirilebilir.
3. **Sanayi'nin ülke geneli serisi — TAMAMEN TAMAMLANDI** (`fact_tuketim_
   ulke_geneli`, 120/120 ay aktif, yukarıya bkz.). KPI-25/27'nin bu
   tabloyu kullanıp kullanmayacağı kararı da **2026-09-08'de (Aşama
   2/C5) verildi ve uygulandı** — yukarıdaki TL;DR maddesine bkz., bu
   madde artık açık değil.
4. **Gerçek internete açık bir deploy** — Streamlit Cloud denemesi
   yapıldı (GRANT/RLS sorunları bu turda çözüldü), kalıcı/otomatik bir
   deploy akışı (`deploy.yml`'in şu an devre dışı `build-push` job'ı)
   hâlâ Docker/web iskeleti bekliyor.

## Güvenilirlik notu

Bu dosyadaki sayılar birden fazla turda canlı Supabase'e karşı
çalıştırılan salt-okunur SQL sorgularından (`fact_tuketim`/`fact_abone`/
`fact_uretim`/`veri_kapsam_disi`/`information_schema.role_table_grants`/
`pg_policies`) ve gerçek `pytest` çalıştırmalarından geliyor — hiçbir
sayı körlemesine önceki dokümandan devralınmadı, her turda yeniden
sorgulandı:

- **2026-09-04 turu:** GRANT/RLS düzeltme zinciri (4 migration) + 36 yeni
  regresyon testi (2016-2022 için) canlıda doğrulandı; bu turda hiçbir
  batch aktive edilmedi.
- **2026-09-05/07 turu:** `fact_tuketim_ulke_geneli` migration'ı canlıya
  uygulandı, 120 aylık backfill çalıştırıldı; ilk mutabakat kontrolünde
  81/120 ay aktive edilebildi, 39 ay `running` bırakılıp kullanıcıya
  rapor edildi (bkz. `06_canli_veri_operasyon_gunlugu.md` 2026-09-05/07
  kaydı) — bu, **geçici bir ara durumdu**, kalıcı sonuç değil.
- **2026-09-07 turu:** 39 aylık uyumsuzluğun kök nedeni bulundu (veri
  hatası değil — `dogrula_tuketim()`'in negatif değer reddinin il vs
  ülke seviyesinde bağımsız uygulanmasının beklenen sonucu), mutabakat
  sorgusu kalıcı olarak düzeltildi (`worker/scripts/mutabakat_ulke_
  geneli.py`), kalan 39 ay (2016-12 hariç 4/5 grupla) aktive edildi →
  **120/120 ay aktif, 599 satır**. RLS admin+viewer JWT ile yeniden
  doğrulandı. Ayrıca 13-dokümanlık dış denetim (Aşama 0) ve Aşama 1'in
  büyük kısmı (C2/B2/C1/C3/C4) bu günde tamamlandı.
- **2026-09-08 turu (son, GÜNCEL durum):** Aşama 1 kapatıldı — zamanlanmış
  yedek workflow'u + `app_dashboard_service` idle timeout canlıya
  uygulandı (yukarıya bkz.). Bu turda hiçbir fact/dim tablosu
  değişmedi, yalnız CI/CD + rol config'i.

---

## SONRAKİ OTURUM DEVAM NOKTASI

**Bu bölümü önce oku — bir sonraki oturum yalnız bunu okuyup kaldığı
yerden devam edebilmeli.**

### Bugün/bu gece (2026-09-07/08/09) ne kapandı — tek satır özet
13-dokümanlık dış denetimin **tamamı** kapandı (2026-09-07/08, Aşama 0/1/2
+ D kuralı). 2026-09-08 içinde Aşama 3 ADIM 1-2 + ADIM 3 madde 1 kapandı
(commit `1232cb3`, `df616e6`). 2026-09-09 gecesi (gözetimsiz çalışma)
ADIM 3'ün TAMAMI (madde 0-4, kod+disposable) + ADIM 5'in araştırma
hazırlığı kapandı (commit'ler `a230614`→`cf5c9a1`, `7b76e3c`). **Aynı gün
(2026-09-09) kullanıcı onayıyla ADIM 3 madde 2-4 CANLIYA UYGULANDI**
(migration `20260909_0001` + `backfill_uretim_excel.py`) ve **Bulgu C/D
kararları verilip uygulandı** (migration `20260909_0002` + `veri_
kapsam_disi` 48 satır + KPI-07 regresyon testi) — detay `10_TEKNIK_
MASTER_DOKUMAN.md` §5.11.

### Açık madde
Dış denetim listesinin (A/B/C bölümleri) hiçbir maddesi açık değil.
**Aşama 3 (boş KPI'ları açma) — ADIM 1-4'ün TAMAMI (kod + canlı) TAMAMLANDI,
ADIM 5 (KPI bağlama) HENÜZ BAŞLAMADI:**
- **ADIM 3 madde 1** (batch bağımlılığı düzeltmesi) — TAMAMLANDI, canlıda
  (2026-09-08, commit `df616e6`).
- **ADIM 3 madde 2** (`fact_uretim_kaynak_geneli`/`fact_uretim_il_geneli`
  migration'ı) — TAMAMLANDI, **canlıya UYGULANDI** (2026-09-09).
- **ADIM 3 madde 3** (`mutabakat_uretim.py`, aktivasyonu engelleyen
  `periyot_aktivasyona_uygun_mu()`) — TAMAMLANDI (commit `9c3c236`,
  güvenlik düzeltmesi `dbe610e`), canlıda 12/12 uyumlu doğrulandı.
- **ADIM 3 madde 4** (Excel backfill) — TAMAMLANDI, **canlıya UYGULANDI**
  (2026-09-09): 6/6 ay yüklendi, mutabakat 6/6 UYGUN, 6/6 aktive edildi
  (`fact_uretim_kaynak_geneli` 101 satır, `fact_uretim_il_geneli` 942
  satır, hepsi aktif — canlı sonuç disposable ile birebir eşleşti).
- **Bulgu C/D kararları — VERİLDİ VE UYGULANDI (2026-09-09):**
  - **Bulgu C:** Word'ün Lisanssız için sunduğu zengin il×kaynak veri
    **KULLANILMAYACAK** (Word-Excel sınırında tanım kırılması riski) —
    yalnız doküman kararı, kod/veri değişikliği yok.
  - **Bulgu D (Karar 4):** 2016-2017 Lisanssız üretim **KAPSAM DIŞI** —
    migration `20260909_0002` (`veri_kapsam_disi.fact_tablosu` CHECK
    genişletildi) + `pipeline.kapsam_disi_isaretle()` ile 48 satır
    (canlıda 48/48 doğrulandı). KPI-07 için ileriye dönük şart `04_kpi_
    sozlesmeleri.md`'ye yazıldı + `kpi_07_lisanssiz_pay()`'in boş/tüm-NaN
    girdide `None` döndüğü yeni bir regresyon testiyle SABİTLENDİ.
  Detay: `05_kaynak_dosya_sozlesmesi.md`, `12_word_uretim_envanteri.md`.
- **Yan bulgu (canlıya özgü, kod DEĞİŞTİRİLMEDİ):** `validate_role_
  access.py`'nin `SET ROLE` adımı canlıda "permission denied" verdi —
  `postgres` rolünün `viewer`/`data_operator`/`admin`/`app_dashboard_
  service`'e üyeliği `WITH INHERIT FALSE, SET FALSE` (PG16+ özelliği,
  Supabase'in native rolleri — anon/authenticated/service_role — `SET
  TRUE` ile granted, fark BURADA) — bu turun migration'larıyla İLGİSİZ,
  ÖNCEDEN VAR OLAN bir canlı-ortam karakteristiği (disposable'da AYNI
  script sorunsuz geçti). `validate_rls_static.py` (21/21) canlıda
  YEŞİL — dinamik SET ROLE testi ayrı bir araştırma konusu, kod/veri
  değişikliği GEREKTİRMEZ, sonraki bir oturumda değerlendirilebilir.
- **ADIM 5 (asıl KPI bağlama, KPI-02/03/06/07/05) — TAMAMLANDI (2026-09-09,
  ADIM 4'ten ÖNCE yapıldı, yalnız 2026 Excel verisiyle):**
  - `worker/analytics.py:uretim_kaynak_geneli_getir()` → KPI-02 (yalnız
    Lisanslı, formül gereği)/03/06/07 (kombine).
  - `worker/analytics.py:kapasite_faktoru_girdisi_getir()` → KPI-05, pay
    VE payda AYNI lisans (Lisanslı) filtresiyle — sessiz-hata riski
    testle sabitlendi (filtresiz/doğru yol GERÇEKTEN farklı çıktığı
    kanıtlandı, sonra doğru yol pinlendi).
  - Canlı 2026-01..06: KPI-02 23,9-31,3 TWh, KPI-03 %39,7-72,0, KPI-05
    %32,0-42,3 (makul aralık), HHI 0,175-0,246, KPI-07 %3,5-12,4.
  - `dashboard.py` kartlarına kaynak/kapsam notu eklendi. KPI-01/04
    BİLİNÇLİ dokunulmadı (kapsam dışı).
  - Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.13, Sürüm Geçmişi v1.27;
    `06_canli_veri_operasyon_gunlugu.md` 2026-09-09 (devam) kaydı.
- **ADIM 4 (orijinal numaralandırma — Word yılları backfill'i):** henüz
  başlamadı, `dokumanlar/12_word_uretim_envanteri.md`'deki envanterle
  hazır (Bulgu E/G hâlâ açık teknik sorular — ilk iş bunları çözmek).
  **ADIM 5'in wiring'i sırasında bulunan, ADIM 4'ü ucuzlatacak notlar:**
  - `lisans_id` çözümü: `worker/ingest.py:dim_lisans_id_bul()` GENEL bir
    yardımcı (Türkçe VEYA ASCII etiket kabul eder, `_LISANS_KODU` ile
    çevirip `dim_lisans.tur`'a bakar) — Excel T2/T5 parser'ları zaten
    bunu kullanıyor (`fact_uretim_kaynak_geneli_yukle()`). Kontrol
    edildi: `worker/scripts/word_ortak.py`'de ŞU AN hiç `lisans` alanı
    YOK (yalnız tüketim/T11 için yazılmış, üretim Word parser'ı henüz
    YAZILMADI) — ADIM 4'ün üretim Word parser'ı yazılırken tek gereken,
    Word Tablo 1.6/1.11 (Lisanslı/Lisanssız ayrı tablolar, bkz. `12_
    word_uretim_envanteri.md`) satırlarına aynı `dim_lisans_id_bul()`'u
    çağırmak — YENİ bir lisans-çözümleme mekanizması İCAT ETMEYE gerek
    yok, mevcut yardımcı doğrudan reuse edilebilir.
  - 2016-2017 KPI-07 'hesaplanamaz' geçişi: `fact_uretim_kaynak_geneli`
    o yıllar için (Bulgu D kararı gereği) HİÇ satır almayacak — bu
    turda `uretim_kaynak_geneli_getir()` zaten BOŞ DataFrame'i doğru
    şekilde işliyor (`kpi_07_lisanssiz_pay()` boş girdide `None`
    döner, testle pinli). Tek fark: bu turda boşluk "veri yok" (dönem
    hiç yüklenmemiş), ADIM 4 sonrası 2016-2017 için "hesaplanamaz"
    (kasıtlı kapsam-dışı) olması gerekecek — ayrım `veri_kapsam_disi`
    tablosundan (`analytics.kapsam_disi_getir()`, migration
    `20260909_0002` zaten bu iki tabloyu kapsıyor) okunarak
    dashboard'da metne yansıtılmalı; KOD DEĞİŞİKLİĞİ küçük (yalnız
    caption/etiket seçimi, hesap mantığı DEĞİŞMEZ).
  - `kapasite_faktoru_girdisi_getir()` Word yılları için de OLDUĞU GİBİ
    çalışır (SQL sorguları `tarih_id` parametrik, tabloya Word verisi
    hangi batch'ten gelirse gelsin AYNI filtre mantığı geçerli) — ADIM
    4'te KPI-05 için ayrı bir wiring GEREKMEZ, yalnız veri dolunca
    otomatik doğru değer üretir.

### ✅ Kapandı — `conftest.py` canlı-DB koruması artık kendi regresyon testine sahip (2026-09-09, gece çalışması MADDE 0)
Aynı koruma (`worker/tests/conftest.py:pytest_configure()`) daha önce
**iki kez** atlanmıştı: 2026-09-02'de ilk kez (koruma o zaman hiç yoktu)
ve 2026-09-08'de İKİNCİ kez (koruma VARDI ama `.env`'in `load_dotenv()`
ile kontrolden SONRA yüklenmesi yüzünden atlandı — bkz. `06_canli_veri_
operasyon_gunlugu.md` 2026-09-08 (devam) kaydı, düzeltme commit
`df616e6`). **2026-09-09'da `worker/tests/test_conftest_guard.py`
eklendi** (ayrı dosya, `conftest.py`'nin İÇİNE değil — kendini test
ederken kendini bypass etmesin diye): gerçek `conftest.py`'nin GÜNCEL
kaynağını izole bir sahte projeye kopyalayıp subprocess olarak çalıştırır,
3 senaryo doğrular — (1) `DATABASE_URL` doğrudan sahte-canlı bir URL'e
set edilince `exit code 3`, (2) 2026-09-08 bug'ının BİREBİR
reprodüksiyonu: `DATABASE_URL` kabukta YOK, yalnız `.env`'de var, yine de
`exit code 3` (bu senaryo eski/buggy koda karşı BİLİNÇLİ olarak
çalıştırılıp GERÇEKTEN yakaladığı kanıtlandı — geçici olarak eski koda
dönülüp test'in kırıldığı görüldü, sonra düzeltme geri alındı), (3)
`ALLOW_DESTRUCTIVE_TESTS=true` kaçış kapısı hâlâ çalışıyor. Üçüncü bir
sessiz atlama artık pytest seviyesinde kilitli.

### C6 — ertelenmiş/değerlendirilmiş küçük maddeler (yalnız referans, aksiyon BEKLEMİYOR)
- **MFA / merkezi rate-limit:** ertelendi (tek admin kullanıcı var).
- **Veri girişi UI'ı + admin rol-atama UI'ı:** ertelendi (2026-09-05
  kararı, `data_operator`'ın RLS altyapısı hazır ama UI'ı yok, yeni
  kullanıcı eklemek hâlâ elle/Supabase Dashboard'dan).
- **HDD/CDD çok noktalı il temsili:** Faz 4 öncesi bir kez ölçülüp
  karara bağlanacak, şimdi değil (tek nokta/il varsayımı şu an bilinçli
  bir metodolojik sınırlama olarak duruyor).
- **`deploy.yml`'in `build-push` job'ı:** hâlâ `if: false` ile devre
  dışı (`web/` klasörü ve Dockerfile'lar henüz yok) — `migrate`/
  `deploy-ssh`/`smoke` job'ları buna `needs` bağlı olduğundan fiilen hiç
  çalışmıyor.
- **Yeni bir KPI numarası gerekirse KPI-29'dan başla** — KPI-28 slotu
  `05_kaynak_dosya_sozlesmesi.md`'de zaten rezerve (tanımlı ama
  implemente edilmemiş), çakışma olmasın.
- Diğerleri (Strategy Pattern, `word_20XX.py` refactor'ü vb.) zaten
  REDDEDİLDİ/KAPANDI — yeniden açılmasın.

### Faz 4 (Tahminleme) — Aşama 3'ten SONRA, henüz başlamadı
Kapsam kararı bekliyor. **Öneri (karar verilmedi, yalnız öneri):**
Eskişehir pilotu + seasonal-naive baseline ile başla — küçük, tek-il
kapsamlı bir kanıt-of-concept, tam bir tahminleme motoruna atlamadan
önce. 10 yıl gerçek veri artık var (2016-2025), bu kararı gözden
geçirmek için önceki turlarda "erken" denen gerekçe artık geçerli değil.

### İlk çalışacak zamanlanmış yedek — bir sonraki oturumun İLK işi
`scheduled-backup.yml`'in cron'u (`0 3 * * 0`, her Pazar 03:00 UTC) ile
İLK gerçek otomatik koşusu **2026-09-13 Pazar 03:00 UTC**'de olacak
(bugüne kadarki koşular hep elle `workflow_dispatch` iledir). Bir sonraki
oturum önce bunu kontrol etmeli: `gh run list --workflow=scheduled-
backup.yml` ile o koşunun gerçekten tetiklendiğini ve başarılı olduğunu
doğrula (artifact oluştu mu, dump boyutu makul mü). GitHub'ın kendi
başarısızlık e-postası da açık (repo sahibi, "On GitHub + Email + yalnız
başarısız workflow'lar" — kullanıcı tarafından teyit edildi) — ama bu,
elle kontrolün YERİNE GEÇMEZ, yalnız bir ek güvenlik ağı.
