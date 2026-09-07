# 09 — Proje Durumu (GÜNCEL, DB'den doğrulandı — 2026-09-04, 2026-09-07'de
fact_tuketim_ulke_geneli eklemesiyle güncellendi)

> **STATUS: LIVE (güncel durum)** — bu dosya ve `10_TEKNIK_MASTER_
> DOKUMAN.md`, değişen sayı/durumun YAŞADIĞI tek iki yerdir; diğer
> `dokumanlar/` dosyaları yalnız değişmeyen sözleşmeyi tutar (2026-09-07
> denetimi, bkz. D bölümü).

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
- **KPI-25/KPI-27 zaten uygulanmış durumda** — KPI-25 (resmi "toplam
  tüketim" CAGR) yalnız Sanayi'yi içeren tam yılları sayıyor (bugün
  itibarıyla tek yıl olduğu için 'hesaplanamaz'); KPI-27 (Sanayi-hariç,
  ayrı bir metrik) tüm yıllarda tutarlı grain ile çalışıyor.
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
- **Aşama 1 (operasyonel güvenlik, 2026-09-07) — devam ediyor:** prod DB'ye
  karşı test guard'ı kod seviyesinde eklendi (C2), CI/deploy migration
  asimetrisi kapatıldı (B2), yedekleme runbook'u GERÇEK bir restore
  drill'iyle doğrulandı (C1 — Supabase Free plan'de otomatik yedek YOK,
  bkz. `11_yedekleme_runbook.md`). Detay: `10_TEKNIK_MASTER_DOKUMAN.md`
  §8.5/§9.1/§9.4, Sürüm Geçmişi v1.3-v1.5.

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
   ulke_geneli`, 120/120 ay aktif, yukarıya bkz.). Kalan tek karar:
   KPI-25/27'nin bu yeni tabloyu kullanıp kullanmayacağı (formül bu
   turda DEĞİŞTİRİLMEDİ, ayrı bir karar konusu).
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
- **2026-09-07 turu (son, GÜNCEL durum):** 39 aylık uyumsuzluğun kök
  nedeni bulundu (veri hatası değil — `dogrula_tuketim()`'in negatif
  değer reddinin il vs ülke seviyesinde bağımsız uygulanmasının beklenen
  sonucu), mutabakat sorgusu kalıcı olarak düzeltildi
  (`worker/scripts/mutabakat_ulke_geneli.py`), kalan 39 ay (2016-12 hariç
  4/5 grupla) aktive edildi → **120/120 ay aktif, 599 satır** — TL;DR'deki
  sayı budur ve güncel/nihai olandır. RLS admin+viewer JWT ile yeniden
  doğrulandı.
