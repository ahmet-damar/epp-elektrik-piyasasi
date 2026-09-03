# 09 — Proje Durumu (GÜNCEL, DB'den doğrulandı — 2026-09-03)

**Bu dosya, canlı Supabase'e karşı salt-okunur sorgularla ve `pytest`
çalıştırılarak DOĞRULANMIŞ bulgulara dayanır — tahmin/varsayım YOK.**
Önceki `SABAH_OZETI.md` (2026-09-03/05 gece-turu notları) bu turda
**SİLİNDİ** — bir kısmı güncelliğini yitirmişti (bkz. aşağıdaki "Tespit
edilen tutarsızlık" notu): T11/T10'un 2021 tam yıl + 2022 Ocak-Nisan için
"taksonomi kararı beklediği için hiç işlenmedi" dediği veri, gerçekte
**başka bir oturumda zaten işlenip aktive edilmiş** durumdaydı.

## TL;DR

- **T11 (fact_tuketim, tüketim):** 2016-01 → 2025-12 arası **120/120 ay
  aktif**, sıfır eksik, sıfır `running`/`failed` (2024-03'teki tek `failed`
  kayıt — batch_id=19 — bilinen, kasıtlı temizlenmiş bir mükerrer-batch
  izi; 2024-03'ün kendisi başka bir batch'le zaten aktif).
- **T10 (fact_abone, abone sayısı):** yalnız **2021-11'den itibaren**
  aktif oluyor (2016-2020 tam yıllar + 2021 Ocak-Ekim, kaynakta il×grup
  kırılımı YAPISAL OLARAK yok — `veri_kapsam_disi`'de 70 kayıtla açıkça
  işaretli). 2021-11 → 2025-12 arası **50/50 ay aktif**, eksik yok.
- **T4 (fact_uretim, lisanssız kurulu güç):** 120 aydan yalnız **2022-07
  eksik** (kaynağın kendi "İllere ve Kaynaklara Göre Dağılım" tablosu bir
  önceki tabloyla birebir kopya — kalıcı kaynak hatası, `veri_kapsam_disi`
  ile işaretli). **119/120 ay aktif.**
- **Taksonomi kararı ("Ticarethane"→"Kamu ve Özel Hizmetler",
  "Tarımsal Sulama"→"Tarımsal") UYGULANMIŞ ve etkilediği TÜM aylar (2020
  tam yıl + 2021 tam yıl + 2022 Ocak-Nisan) zaten aktive edilmiş.**
- **pytest** (`worker/tests`, 6 `*_integration.py` hariç): **164/164
  geçti**, 0 hata.
- **Açık kalan tek gerçek madde:** `word_2023.py`/`word_2024.py`/
  `word_2025.py` için hâlâ dedike pytest regresyon testi yok (yalnız
  script-içi assertion var).

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

Tüm "kaynakta yok" hücreleri `veri_kapsam_disi` tablosunda açık
sebep metniyle işaretli (DB'den doğrulandı: `fact_abone` 70 kayıt,
`fact_uretim` 85 kayıt [84×Lisanslı + 1×2022-07 Lisanssız],
`fact_serbest_tuketici` 84 kayıt — Karar 1/3 kapsamı).

## Tespit edilen tutarsızlık (silinen SABAH_OZETI.md ile)

`SABAH_OZETI.md`, 2021'in tamamı ve 2022 Ocak-Nisan'ın T11/T10 için
"taksonomi kararı beklediği için hiç işlenmedi, batch ID bile atanmadı"
dediği hâlde, DB sorgusu bu 16 ayın tamamının `batch_id 173-188`
aralığında **zaten `succeeded` + `is_active=true`** olduğunu gösterdi —
`_GRUP_TAKMA_ADLAR` alias'ları (daha önce başka bir oturumda eklenmiş)
kullanılarak işlenmiş. Kod/veri tarafında bir sorun yok — yalnızca
dokümantasyon güncel değildi, bu yüzden dosya değiştirildi.

## Bilinen açık maddeler

1. **2022 Temmuz T4 kaynak veri hatası — kalıcı, kod sorunu değil.**
   EPDK'nın kendi raporunda o ay için il×kaynak kırılımı hiç
   yayınlanmamış (kopyala-yapıştır hatası, önceki tabloyla birebir aynı).
   Mekanik olarak elde edilemez, `veri_kapsam_disi` ile işaretli — kapalı
   sayılabilir, veri kaynakta yok.
2. **2016-2020 — TAM işlendi ve aktif.** T11 ve T4 12/12 ay aktif; T10
   yapısal olarak kaynakta hiç yok (yukarıdaki tablo), bu bir eksiklik
   değil, kaynağın kendi raporlama sınırı.
3. **2023-2025 regresyon testi — hâlâ AÇIK.** `worker/tests/`'te
   `test_word_2016.py`'den `test_word_2022.py`'ye kadar (7 dosya) var,
   ama `word_2023.py`/`word_2024.py`/`word_2025.py` için dedike pytest
   yok — yalnız script-içi assertion'lara güveniliyor.

## Test durumu (2026-09-03, bu turda çalıştırıldı)

```
python -m pytest worker/tests -q  (6 *_integration.py HARİÇ — README Ek D kuralı)
164 passed in 9.01s
```

`*_integration.py` (6 dosya: `test_analytics_integration.py`,
`test_auth_integration.py`, `test_fetch_weather_integration.py`,
`test_ingest_integration.py`, `test_job_worker_integration.py`,
`test_pipeline_integration.py`) canlı Supabase'e karşı bilinçli
çalıştırılmadı (README'deki "Canlı Supabase'e Karşı Test Çalıştırma
Kuralı").

## Güvenilirlik notu

Bu dosyadaki TÜM sayılar bu turda canlı Supabase'e karşı çalıştırılan
salt-okunur SQL sorgularından (`ingestion_batch`/`source_asset`/
`fact_tuketim`/`fact_abone`/`fact_uretim`/`veri_kapsam_disi`) ve gerçek
bir `pytest` çalıştırmasından geliyor — hiçbir sayı önceki dokümanlardan
devralınmadı/varsayılmadı. Bu turda hiçbir batch aktive edilmedi, hiçbir
kod/şema değiştirilmedi.
