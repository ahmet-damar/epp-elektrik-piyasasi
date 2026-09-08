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

**Bu bölümü önce oku.** 2026-09-07/08'de tamamlanan iş: 13-dokümanlık dış
denetim (Aşama 0), operasyonel güvenlik (Aşama 1: C2, B2, C1, C3, C4),
ve KPI sözleşmesi kapanışı (Aşama 2: C5 + dashboard idle-in-transaction
kök nedeni + yedekleme restore hedefi düzeltmesi) — **HEPSİ TAMAMLANDI**.
Dış denetim listesindeki A/B/C bölümlerinden **hiçbir açık madde
kalmadı**. Sırada denetimin kendisinin işaret ettiği bir sonraki adım
YOK — proje bir sonraki iş kalemi için (Faz 4/5/6, yeni bir özellik,
yeni bir denetim turu) açık.

### C6 — ertelenmiş/değerlendirilmiş küçük maddeler (yalnız referans, aksiyon gerektirmiyor)
- MFA/merkezi rate-limit: ertelendi (tek admin kullanıcı var).
- HDD/CDD çok noktalı model: Faz 4 öncesi bir kez ölçülüp karara
  bağlanacak, şimdi değil.
- Diğerleri (Strategy Pattern, veri girişi UI'ı vb.) zaten REDDEDİLDİ/
  KAPANDI — yeniden açılmasın.
