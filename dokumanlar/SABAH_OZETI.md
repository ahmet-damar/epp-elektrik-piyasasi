# SABAH ÖZETİ — 2016-2022 Word Aktarımı, Gece Turu (2026-09-03)

**Bu dosya tek başına okunduğunda durum tam anlaşılsın diye yazıldı.**
Detaylı teşhis/bulgular için `dokumanlar/08_word_2016_2022_kapsam.md`.

## TL;DR

- **2022** ve **2021** için kod yazıldı, gerçek Supabase'e yüklendi
  (`is_active=false`, hiçbir batch aktive EDİLMEDİ — kural tam uyumlu).
- **2016-2020** bu turda İŞLENMEDİ — zaman/kapsam nedeniyle 2021-2022'ye
  odaklanıldı. Aşağıdaki "Sıradaki adım" bölümünde net bir öneri var.
- **1 açık karar seni bekliyor** (taksonomi — aşağıda), onsuz 2016-2022
  aralığının T11/T10 (tüketim/abone) kısmı hiç açılamaz.
- **0 batch aktive edildi** (DB'den doğrulandı) — hiçbir fact tablosunda
  2021/2022 için `is_active=true` satır yok. Aktivasyon kararı tamamen sana ait.

## Hangi yıllar ne durumda

| Yıl | T11/T10 (tüketim/abone) | T4 (lisanssız kurulu güç) | Batch ID |
|---|---|---|---|
| 2022 | **8/12 ay YÜKLENDİ** (Mayıs-Aralık), 4/12 (Ocak-Nisan) BEKLEMEDE (taksonomi) | **11/12 ay YÜKLENDİ**, 1/12 (Temmuz) BEKLEMEDE (kaynak veri hatası) | T11/T10: 142-149 · T4: 150-160 |
| 2021 | **0/12 — TÜM YIL BEKLEMEDE** (taksonomi, tüm yıl eski taksonomi) | **12/12 ay YÜKLENDİ** | T4: 161-172 |
| 2016-2020 | İŞLENMEDİ (bu turda kod yazılmadı) | İŞLENMEDİ | — |

**Hiçbir batch `onayla.py`/`pipeline.batch_onayla()` ile aktive edilmedi** —
tümü `running` durumda, DB'den doğrulandı (`fact_tuketim`/`fact_abone`/
`fact_uretim`'de 2021 ve 2022 için `is_active=true` satır sayısı: **0**).

## Senin vereceğin kararlar (sırayla, en önemliden)

### 1. Taksonomi kararı — EN ÖNEMLİSİ, çoğu kalan işi açar

**Soru:** 2016-2022'nin büyük bölümünde (2022 Ocak-Nisan + 2021'in TÜMÜ +
muhtemelen 2016-2020'nin tamamı) tüketici grubu etiketleri farklı:
"**Ticarethane**" ve "**Tarımsal Sulama**" — bugünkü kanonik küme
(`worker/parser.py:GRUP_ESLEME`) bunları TANIMIYOR, onun yerine "Kamu ve
Özel Hizmetler" ve "Tarımsal" var.

**Araştırdım (madde 0), kesin cevap bulamadım — ama güçlü bir ipucu var:**
EPDK'nın kendi "Dönemler Arası Karşılaştırma" tablosu (Mayıs 2022 dosyası)
**2021 Mayıs verisini bile GERİYE DÖNÜK olarak YENİ etiketlerle
gösteriyor** ("Tarımsal Faaliyetler", "Kamu ve Özel Hizmetler Sektörü ile
Diğer") — yani EPDK'nın kendisi bunları doğrudan karşılaştırılabilir/
eşdeğer sayıyor, iki ayrı kavram gibi değil. Grup SAYISI da değişmiyor
(5→5, yalnız 2 isim değişiyor, Aydınlatma/Mesken/Sanayi aynen kalıyor) —
bu bir MERGE/SPLIT'ten çok RENAME (yeniden adlandırma) izlenimi veriyor.

**Ama tam kesin değil:** "Ticarethane"→"Kamu ve Özel Hizmetler" büyüklük
olarak yakın kaldı (aynı yılın komşu aylarını karşılaştırınca +%3,6), ama
"Tarımsal Sulama"→"Tarımsal Faaliyetler" ~3 KAT arttı — bu mevsimsel
olabilir (sulama sezonu başlangıcı) ya da gerçek bir kapsam genişlemesi
olabilir, tek başına belirleyici değil.

**3 seçenek (04_kpi_sözleşmeleri tarzı, öneri değil, sana bırakıyorum):**
- **(a) Alias'la** — "Ticarethane"→"Kamu ve Özel Hizmetler",
  "Tarımsal Sulama"→"Tarımsal" (`worker/scripts/word_2021.py` ve
  `word_2022.py`'deki `_GRUP_TAKMA_ADLAR`'a eklenir). En hızlı, ama
  "Tarımsal Sulama" için büyüklük sıçraması riski taşıyor.
- **(b) Yeni bir kanonik grup ekle** ("Ticarethane" için) — şema/KPI
  değişikliği gerektirir, daha büyük bir iş kalemi, ama en doğru olabilir.
- **(c) Bu yılları da "kaynakta yok" say** (Karar 2'deki Sanayi
  mantığıyla) — en güvenli ama en az veri.

**Karar verirsen ne olur:** `worker/scripts/word_2021.py` ve
`word_2022.py`'nin `_GRUP_TAKMA_ADLAR`'ına 2 satır eklenir (seçenek a
ise), kod BAŞKA HİÇBİR ŞEY değişmeden 2021'in 12 ayı + 2022'nin 4 ayı
(toplam 16 ay) T11/T10 için hemen yüklenebilir hale gelir — script zaten
hazır, yalnız bu 2 satır bekliyor.

### 2. Aktivasyon — batch 142-172 (31 batch)

Hepsi `running`/`is_active=false`. Gözden geçirip
`worker/scripts/onayla.py --batch-id <id>` ile (ya da toplu) aktive etmek
sana kalmış. `otomatik_onaya_uygun()` çıktıları script loglarında var
(çoğu `True`, birkaçında 1-2 kırmızı satır — negatif "Tarımsal" değerleri,
`kpi.dogrula_tuketim()`'in bilinen davranışı, detay için
`08_word_2016_2022_kapsam.md`'deki "2022 tarifi" bölümüne bak).

### 3. Temmuz 2022 T4 — kaynak veri hatası, "kaynakta yok" sayılabilir

O ayın Word raporunda "İllere ve Kaynaklara Göre Dağılım" tablosu
YANLIŞLIKLA bir önceki tablonun (il-only) kopyası — EPDK'nın kendi
raporlama hatası, kod sorunu değil (detay: 08, "2022 tarifi" bölümü).
Kalıcı olarak elde edilemez; `veri_kapsam_disi`'ye eklenip eklenmeyeceği
sana kalmış.

### 4. 2016-2020 — sıradaki adım

Bu turda işlenmedi. **Beklenti (doğrulanmadı, tahmin):** 2021'in aynısı —
muhtemelen tamamı eski taksonomi, T4 muhtemelen sorunsuz yüklenir, T11/T10
madde 1'deki karara kadar bekler. Sıradaki oturum `word_2020.py`'den
başlayıp geriye gidebilir (`word_2021.py` doğrudan şablon).

## Bu turda bulunan, kod-dışı ilginç şeyler

- **T10'un yapısal geçişi taksonomi geçişinden AYRI:** tüketici-grubu
  isim değişikliği 2022 Nisan/Mayıs'ta oldu, ama T10 tablosunun YAPISI
  (il-only → il×grup) 2021 Ekim/Kasım'da ZATEN değişmişti — iki ayrı
  EPDK format kararı, aynı anda değil. Şu an pratik önemi yok (T11
  taksonomi yüzünden zaten her ay önce durduruyor) ama taksonomi kararı
  verilirse bu da ayrıca çözülmeli.
- **"Küthahya" yazım hatası tekrarlayan bir kaynak hatası:** 2021
  Kasım/Aralık VE 2022 Ocak/Şubat'ta "Kütahya" yerine yazılmış (fazladan
  bir 'h'). Kod seviyesinde düzeltildi (`_IL_ADI_DUZELT`), ama EPDK'nın
  kendi verisinde gerçek bir hata olduğu için not düşülüyor.
- **Nisan 2022'nin T11 tablosu yanlış etiketli:** kendi başlığı "Mart
  2022" diyor ama veri gerçekten Nisan'a ait (Genel Toplam'lar farklı,
  duplikasyon değil) — muhtemelen EPDK'nın kopyala-yapıştır kalıntısı.
  `_BILINEN_ETIKET_HATALARI` ile belgelenip geçildi.

## Test/kalite durumu

- `worker/tests/test_word_2021.py` (6 test) + `test_word_2022.py` (12
  test) — hepsi geçiyor, DATABASE_URL'e bağımlı DEĞİL (synthetic docx
  tabloları), CI'nin 'Worker' job'ında da çalışıyor.
- `ruff check`/`ruff format --check`/`mypy` temiz (30+ dosya).
- **07'nin "Açık kalanlar" madde 1'i (regresyon testi eksikliği)** yalnız
  2021/2022 için kapatıldı — **2023/2024/2025 hâlâ testsiz.**

## Commit'ler (hepsi ayrı, CI doğrulandı)

1. `ee5a14f` — README Ek D'ye "tam pytest paketini canlıya karşı
   çalıştırma" güvenlik kuralı. CI ✅
2. `3cea052` — 2022 tarifi (kısmi): T11/T10 batch 142-149, T4 batch
   150-160, 12 test. CI ✅
3. `7637c83` — 2021 tarifi (yalnız T4): T4 batch 161-172, 6 test. CI ✅

## Kesin kurallara uyum — doğrulama

- ✅ `onayla.py`/`pipeline.batch_onayla()` HİÇ çağrılmadı (DB'den
  doğrulandı: 0 aktif satır).
- ✅ Tam pytest paketi canlıya karşı çalıştırılmadı — yalnız hedefli
  `-k`/dosya bazlı testler kullanıldı, tam paket yalnız CI'nin
  postgres:16'sında koştu.
- ✅ Şema değişikliği yapılmadı (migration yok, `dim_grup`'a dokunulmadı).
- ✅ Taksonomi kararına takılan aylar BEKLEMEDE bırakıldı, döngüye
  girilmedi — 2021'in TÜMÜNÜN bloke olduğu HIZLICA (tek bir mekanik
  taramayla) tespit edildi, 12 ay tek tek denenmedi.
- ✅ Her yıl bitince ayrı commit + push yapıldı.
