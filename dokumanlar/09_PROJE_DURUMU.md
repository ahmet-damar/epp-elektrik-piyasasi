# 09 — Proje Durumu (GÜNCEL, DB'den doğrulandı — 2026-09-04)

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
- **pytest** (`worker/tests`, 6 `*_integration.py` hariç): **205/205
  geçti**, 0 hata (bu turda çalıştırıldı).
- **Gerçek, açık kalan bir teknik madde YOK.** Kalan tek şey Sanayi'nin
  Word kaynağında neden T11'e girmediğine dair "ileride araştırılabilir"
  notu (`07_word_parser_kapsam.md`) — bu bir hata/eksik değil, bilinçli
  bir P0 tasarım kararının (Karar 2) belgelenmiş gerekçesi. Sıradaki
  adımlar artık teknik borç değil, **ürün/kapsam kararları** (aşağıya
  bkz.).

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

## Test durumu (2026-09-04, bu turda çalıştırıldı)

```
python -m pytest worker/tests -q  (6 *_integration.py HARİÇ — README Ek D kuralı)
205 passed in 16.56s
```

`*_integration.py` (6 dosya) canlı Supabase'e karşı bilinçli
çalıştırılmadı (README'deki "Canlı Supabase'e Karşı Test Çalıştırma
Kuralı").

## Sıradaki adımlar (teknik borç DEĞİL — ürün/kapsam kararları)

1. **2022 ve öncesi yıllara Word genişletmesi tamamlandı** — genişleme
   listesinde teknik olarak kalan bir yıl yok (2016-2025 hepsi aktif).
2. **Faz 4 (Tahminleme) / Faz 5 (EPİAŞ)** — daha önce ertelenmişti,
   artık 10 yıl gerçek veri var, karar gözden geçirilebilir.
3. **Sanayi'nin T7 (ülke-geneli mutabakat tablosu) üzerinden kısmen
   kurtarılıp kurtarılamayacağı** — araştırılmadı, ayrı bir oturumun
   konusu (`07_word_parser_kapsam.md`'de işaretli).
4. **Gerçek internete açık bir deploy** — Streamlit Cloud denemesi
   yapıldı (GRANT/RLS sorunları bu turda çözüldü), kalıcı/otomatik bir
   deploy akışı (`deploy.yml`'in şu an devre dışı `build-push` job'ı)
   hâlâ Docker/web iskeleti bekliyor.

## Güvenilirlik notu

Bu dosyadaki TÜM sayılar bu turda (2026-09-04) canlı Supabase'e karşı
çalıştırılan salt-okunur SQL sorgularından (`fact_tuketim`/`fact_abone`/
`fact_uretim`/`veri_kapsam_disi`/`information_schema.role_table_grants`/
`pg_policies`) ve gerçek bir `pytest` çalıştırmasından geliyor — hiçbir
sayı önceki dokümandan devralınmadı. Bu turda hiçbir batch aktive
edilmedi, hiçbir kod/şema değiştirilmedi (yalnız bu doküman güncellendi).
