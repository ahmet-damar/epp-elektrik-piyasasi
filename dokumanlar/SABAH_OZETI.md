# SABAH ÖZETİ — 2016-2022 Word Aktarımı (2026-09-03/04, beş tur)

> **Ortam engeli ÇÖZÜLDÜ (2026-09-04).** Akıllı Uygulama Denetimi
> (Değerlendirme modu) pip/PyPI kaynaklı `pandas`'ı engelliyordu —
> Miniconda (`C:\Users\adama\miniconda3`, `epp` ortamı, conda-forge
> kanalı) admin GEREKMEDEN kuruldu, imzalı derlemeler kabul ediliyor.
> **Tüm sonraki dry-run/test/yükleme komutları `C:\Users\adama\
> miniconda3\envs\epp\python.exe` ile çalıştırılmalı** (sistem Python'ı
> DEĞİL). Akıllı Uygulama Denetimi KAPATILMADI. Küçük not: conda-forge'un
> `mypy`'si de AYRI olarak engellendi (SAC dosya bazında karar veriyor) —
> `ruff`/`pytest` yeterli, mypy'siz devam ediliyor. Taksonomi kararı hâlâ
> ÇÖZÜLDÜ (RENAME) — tekrar sorulmamalı. **2019, 2018 ve 2017 TAMAMLANDI**,
> sıradaki adım (SON YIL) 2016.

**Bu dosya tek başına okunduğunda durum tam anlaşılsın diye yazıldı.**
Detaylı teşhis/bulgular için `dokumanlar/08_word_2016_2022_kapsam.md`.
Bu, ilk turun (2021/2022 kısmi + taksonomi AÇIK) devamı — taksonomi kararı
verildi, 2021/2022 tam açıldı, 2020 eklendi.

## TL;DR

- **Taksonomi kararı VERİLDİ ve UYGULANDI** — mevsimsellik doğrulaması
  (2023-2025'in kanonik "Tarımsal" grubu, gerçek veri) RENAME kararını
  DESTEKLEDİ. "Ticarethane"→"Kamu ve Özel Hizmetler",
  "Tarımsal Sulama"→"Tarımsal" artık `_GRUP_TAKMA_ADLAR`'da.
- **2020, 2021, 2022 — T11 (tüketim) artık TAMAMI (36/36 ay) yüklü.**
- **T10 (abone) YAPISAL bir engelle karşılaştı** (taksonomiden AYRI bir
  sorun) — 2020 tüm yıl + 2021 Ocak-Ekim'de kaynakta GERÇEKTEN yok
  (il×grup kırılımı hiç yayınlanmamış). Uydurulmadı, `veri_kapsam_disi`
  ile işaretlendi.
- **T4 (lisanssız kurulu güç) — 34/36 ay yüklü** (2022 Temmuz hariç, kaynak
  raporlama hatası — açıklama aşağıda).
- **2019, 2018 ve 2017 TAMAMLANDI** — üçü de T11 12/12, T10 0/12 (tüm yıl
  yapısal olarak kaynakta yok), T4 12/12. Her yılda 1-3 yeni format
  sürprizi bulundu, hepsi mekanik çözüldü (aşağıya bkz.).
- **2016 SIRADAKİ ADIM (SON YIL)** — envanter + 07'de kısmi teşhis var,
  T11/T10/T4 yapısı henüz kontrol edilmedi. 2016 bitince 2016-2022'nin
  TAMAMI (84 ay) T11/T4 için işlenmiş olacak.
- **0 batch aktive edildi** (DB'den doğrulandı) — hiçbir fact tablosunda
  2017/2018/2019/2020/2021/2022 için `is_active=true` satır yok.
  Aktivasyon kararı sana ait.

## Hangi yıllar ne durumda

| Yıl | T11 (tüketim) | T10 (abone) | T4 (lisanssız kurulu güç) |
|---|---|---|---|
| 2022 | **12/12 ay** | **12/12 ay** | **11/12 ay** (Temmuz hariç — kaynak hatası) |
| 2021 | **12/12 ay** | **2/12 ay** (Kasım-Aralık; Ocak-Ekim kaynakta yok, yapısal) | **12/12 ay** |
| 2020 | **12/12 ay** | **0/12 ay** (TÜM yıl kaynakta yok, yapısal) | **12/12 ay** |
| 2019 | **12/12 ay** | **0/12 ay** (TÜM yıl kaynakta yok, yapısal) | **12/12 ay** |
| 2018 | **12/12 ay** | **0/12 ay** (TÜM yıl kaynakta yok, yapısal) | **12/12 ay** |
| 2017 | **12/12 ay** | **0/12 ay** (TÜM yıl kaynakta yok, yapısal) | **12/12 ay** |
| 2016 | İŞLENMEDİ (envanter + 07'de kısmi teşhis var) — SIRADAKİ ADIM | — | — |

**2019'a özgü 2 YENİ format sürprizi (mekanik çözüldü, word_2019.py'de
belgelendi):**
1. T4'te "Güneş" tek kolon değil — "Güneş (Fotovoltaik)" ve
   "**Güneş (Yoğunlş.)**" ayrı iki kolon, ikisi AYNI kanonik "Güneş"e
   TOPLANIYOR (`t4_oku()` kolon-bazlı değil il-başına-kaynak-toplamı
   mantığıyla yeniden yazıldı).
2. Ekim 2019'da hücre içi satır kırılmaları (örn. "DÜZC\nE",
   "Güneş \n(Yoğunlş.)") — yalnız `\n\r\t` kaldırılıyor, gerçek boşluklar
   ("Genel Toplam" gibi) korunuyor.

**2018'e özgü 1 YENİ format sürprizi (mekanik çözüldü, word_2018.py'de
belgelendi):** Ağustos+Eylül 2018'in T4 tablosunda EPDK'nın kendi
kaynağında "**BOŞ-VERİ-ŞEHİR**" adlı, hiçbir gerçek il_kodu'na
eşlenemeyen FAZLADAN bir satır var (81 gerçek ilin YANINDA — o ayın
gerçek ili de AYRICA mevcut). Küçük bir gerçek değer taşıyor (~3,3 MW)
ama hangi ile ait olduğu belirlenemiyor — TAHMİN EDİLMEDİ, satır AÇIKÇA
atlandı (Genel Toplam'ın kendi toleransı bu farkı zaten kapsıyor).

**2017'ye özgü 3 YENİ format sürprizi (mekanik çözüldü, word_2017.py'de
belgelendi):**
1. Ocak 2017'nin T11 başlığı "Tüketici" önekini bile kaybetmiş ("Türü
   Bazında Dağılımı (MWh)") — arama metni önek olmadan kısaltıldı.
2. Ocak/Mart 2017'de T11 VE T4 tabloları bir SAYFA SONUNA denk geldiğinden
   başlık satırını ("İller"/"İLLER") tablonun İÇİNDE İKİNCİ KEZ taşıyor —
   "GENEL TOPLAM" ile AYNI şekilde AÇIKÇA atlanıyor.
3. Bazı kolon başlıkları iç satır-sonu taşıyor ("Genel \nToplam",
   "Payı\n (%)") — `grup_esle_zorunlu()` artık iç boşluk/satır sonlarını
   normalize ediyor.

**2016 için implementasyon/yükleme henüz yapılmadı** — sıradaki adım (SON
YIL).

**Batch ID aralıkları:**

| Yıl | T11/T10 batch | T4 batch |
|---|---|---|
| 2022 | 142-149 (Mayıs-Aralık, ilk tur) + 185-188 (Ocak-Nisan, ikinci tur) | 150-160 |
| 2021 | 173-184 | 161-172 |
| 2020 | 189-200 | 201-212 |
| 2019 | 213-224 | 225-236 |
| 2018 | 237-248 | 249-260 |
| 2017 | 261-272 | 273-284 |

**Hiçbir batch `onayla.py`/`pipeline.batch_onayla()` ile aktive edilmedi** —
tümü `running` durumda, DB'den doğrulandı (`fact_tuketim`/`fact_abone`/
`fact_uretim`'de 2017-2022 için `is_active=true` satır sayısı: **0**).

## Taksonomi kararı — VERİLDİ (artık açık değil)

**Soru neydi:** 2021'in tümü + 2022 Ocak-Nisan + 2020'nin tümü, tüketici
grubu etiketlerinde "**Ticarethane**" ve "**Tarımsal Sulama**" kullanıyordu
— kanonik küme (`worker/parser.py:GRUP_ESLEME`) bunları tanımıyordu.

**Doğrulama:** 2023-2025'in KANONİK "Tarımsal" grubu (taksonomi belirsizliği
hiç olmayan, zaten yüklü gerçek veri) Mart→Mayıs aralığında ay-ay
sorgulandı:

| Yıl | Mart→Mayıs oranı |
|---|---|
| 2023 | 3,24× |
| 2024 | 4,17× |
| 2025 | 2,79× |
| *(karşılaştırma) 2021→2022 taksonomi sorgusu* | 2,82× |

2021→2022'nin "artışı" gerçek, taksonomi hiç değişmeyen yıllarda AYNI
takvim aralığında görülen NORMAL (hatta bazen daha büyük) mevsimsel
oynaklığın içinde — kapsam değişikliği değil. EPDK'nın kendi karşılaştırma
tablosunun 2021'i bile yeni etiketlerle göstermesiyle (RENAME kanıtı)
birleşince **karar: RENAME olarak kabul edildi.**

**Uygulama:** `word_2020/2021/2022.py`'nin `_GRUP_TAKMA_ADLAR`'ına
"Ticarethane"→"Kamu ve Özel Hizmetler", "Tarımsal Sulama"→"Tarımsal"
eklendi. `worker/parser.py:GRUP_ESLEME` DEĞİŞMEDİ (mimari karar).

## T10'un yapısal engeli — taksonomiden TAMAMEN AYRI bir sorun

Taksonomi açılınca T10'da (tüketici SAYISI tablosu, `fact_abone`) GERÇEK
bir yapısal sorun ortaya çıktı: **bazı ay/yıllarda kaynak tablosunun
kendisinde tüketici-türü/grup KIRILIMI hiç yok** — yalnız il başına TOPLAM
tüketici sayısı var, 5 gruba (Aydınlatma/Mesken/Sanayi/Tarımsal/Kamu ve
Özel) bölünmüyor. Bu, koddan çözülebilecek bir şey DEĞİL — kaynakta
gerçekten yok. `isle_ay()` bunu tespit edip (`t10_oku()` ValueError
fırlatınca) T10'u o ay için `pipeline.kapsam_disi_isaretle(fact_abone)`
ile işaretliyor, **T11 (tüketim) bundan HİÇ etkilenmiyor** (ayrı okunuyor).

- **2020:** TÜM 12 ay il-only (Ocak VE Aralık ikisi de kontrol edildi).
- **2021:** Ocak-Ekim il-only, **Kasım'dan itibaren** il×grup (kesin sınır
  bulundu).
- **2022:** TÜMÜ il×grup (yalnız başlık METNİ Ocak-Nisan'da "İl Bazında"
  yazıyordu, gövde hep il×grup'tu — ayrı bir konu, madde altta).

**Toplam etki:** 36 aylık (2020-2022) pencerede T10 yalnız **14/36 ay**
(2022'nin 12'si + 2021'in 2'si) yüklenebildi, **22/36 ay** kaynakta
gerçekten yok.

## Diğer teknik bulgular (kod zaten düzeltti, bilgi amaçlı)

- **2022 Ocak-Nisan'da T10'un 3 başlık satırı vardı** (Mayıs-Aralık 2
  satır) — `t10_oku()` artık "Tüketici Türü" içeren satırı dinamik buluyor.
- **"Küthahya" yazım hatası** (Kütahya, fazladan bir 'h') 2021
  Kasım/Aralık VE 2022 Ocak/Şubat'ta tekrarladı — `_IL_ADI_DUZELT` ile
  düzeltildi.
- **"AFYONK."/"K.MARAŞ"/"HAKKÂRİ"** il-adı kısaltmaları/eski yazımları
  2021'de bulundu, düzeltildi.
- **Nisan 2022'nin T11 tablosu yanlış etiketli** (kendi başlığı "Mart
  2022" diyor, veri gerçekten Nisan'a ait) — `_BILINEN_ETIKET_HATALARI`
  ile belgelenip geçildi.
- **Temmuz 2022 T4 — gerçek bir EPDK raporlama hatası, kalıcı olarak
  elde edilemez:** o ayın "İllere ve Kaynaklara Göre Dağılım" tablosu bir
  önceki tablonun (il-only) BİREBİR kopyası. `veri_kapsam_disi`'ye
  işaretlendi (`fact_uretim`, hem Lisanssız hem Lisanslı kesiti).
- **2020'nin ay/yıl doğrulama çapası farklı:** T11 başlığı "{Ay} {Yıl}
  Döneminde" içermiyor, kapak paragrafından ("{Yıl} Yılı {Ay} Ayı ...
  Genel Görünümü") doğrulanıyor.

## Senin vereceğin kararlar

### 1. Aktivasyon — batch 142-212 (71 batch)

Hepsi `running`/`is_active=false`. Gözden geçirip
`worker/scripts/onayla.py --batch-id <id>` ile (ya da toplu) aktive etmek
sana kalmış. `otomatik_onaya_uygun()` çıktıları script loglarında var
(çoğu `True`, birkaçında 1-2 kırmızı satır — negatif "Tarımsal" değerleri,
`kpi.dogrula_tuketim()`'in bilinen davranışı).

### 2. 2016 — sıradaki adım (SON YIL, ortam engeli ÇÖZÜLDÜ)

**Komutlar için:** `C:\Users\adama\miniconda3\envs\epp\python.exe`
kullan, sistem `py`/`python` DEĞİL (o hâlâ pandas'ı bloklu).

**2016:** envanter var + 07'de kısmi teşhis var (T4'ün 2-satırlı başlık
istisnası — 2016 Ocak'ta gerçek kaynak adları satır 0 değil satır 1'de,
"Lisanslı" kelimesinin Ocak'ta yokluğu — hâlâ geçerli). 2017-2020'nin
taşıdığı desenler (kapak-paragrafı ay/yıl çapası, T10 il-only, T4
Güneş-ayrımı, hücre-içi satır kırılması, sayfa-sonu başlık tekrarı,
"BOŞ-VERİ-ŞEHİR" tarzı anomali satırlar) hepsi MÜMKÜN, hiçbiri
doğrulanmadı — `word_2017.py` şablon olarak denenebilir ama önce
Ocak/Aralık örnekleriyle kısa bir kontrol yapılmalı (2017'de yapıldığı
gibi). En eski/en farklı yıl olduğundan diğerlerinden daha temkinli
yaklaşılmalı. 2016 bitince 2016-2022'nin TAMAMI (84 ay) T11/T4 için
işlenmiş olacak.

### 3. T10'un 46/60 ay eksik olması KPI'ları nasıl etkiliyor

`fact_abone`'a dayanan KPI'lar (örn. KPI-10) 2017-2022 (72 ay) için
yalnız **14/72 ay** gerçek veriyle çalışacak (2022'nin 12'si + 2021
Kasım-Aralık'ın 2'si) — bu durumun dashboard'da nasıl yansıtılacağı
(örn. `veri_kapsam_disi` tablosunun UI'ya bağlanması, henüz yapılmadı,
bkz. `07_word_parser_kapsam.md`'nin açık kalanlar listesi) ayrı bir karar.

## Test/kalite durumu

- `worker/tests/test_word_2017.py` (11 test) + `test_word_2018.py` (9
  test) + `test_word_2019.py` (8 test) + `test_word_2020.py` (8 test) +
  `test_word_2021.py` (9 test) + `test_word_2022.py` (13 test) — hepsi
  geçiyor, DATABASE_URL'e bağımlı DEĞİL (synthetic docx tabloları), CI'nin
  'Worker' job'ında da çalışıyor.
- `ruff check`/`ruff format --check` temiz. **`mypy` bu makinede
  conda-forge'dan da bloklanıyor** (SAC dosya bazında karar veriyor) —
  CI'de sorun yok (GitHub'ın temiz runner'ı etkilenmiyor), yalnız bu
  makinede yerel mypy çalıştırılamıyor.
- **07'nin "Açık kalanlar" madde 1'i (regresyon testi eksikliği)** 2017/
  2018/2019/2020/2021/2022 için kapatıldı — **2023/2024/2025 hâlâ
  testsiz.**

## Commit'ler (hepsi ayrı, CI doğrulandı — sırayla)

1. `ee5a14f` — README Ek D'ye güvenlik kuralı. CI ✅
2. `3cea052` — 2022 tarifi (kısmi, ilk tur): T11/T10 batch 142-149, T4
   batch 150-160. CI ✅
3. `7637c83` — 2021 tarifi (yalnız T4): T4 batch 161-172. CI ✅
4. `da5b90d` — SABAH_OZETI (ilk tur). CI ✅
5. `89c6e80` — Taksonomi kararı UYGULANDI: 2021 T11 tam + T10 kısmi (batch
   173-184), 2022 Ocak-Nisan T11/T10 (batch 185-188). CI ✅
6. `307752a` — 2020 tarifi: T11/T10 batch 189-200, T4 batch 201-212. CI ✅
7. `ae125f1` — 2016-2019 envanter + kısmi teşhis, implementasyon ortam
   engeliyle DURDU (o an). CI ✅
8. `b786538` — Ortam engeli Miniconda ile ÇÖZÜLDÜ + 2019 tarifi: T11/T10
   batch 213-224, T4 batch 225-236. CI ✅
9. `fd89146` — 2018 tarifi: T11/T10 batch 237-248, T4 batch 249-260
   ("BOŞ-VERİ-ŞEHİR" anomali-satır atlaması dahil).
10. *(bu commit)* — 2017 tarifi: T11/T10 batch 261-272, T4 batch 273-284
    (kısaltılmış T11 arama metni, grup-etiketi iç-boşluk normalizasyonu,
    sayfa-sonu başlık tekrarı atlaması dahil).

## Kesin kurallara uyum — doğrulama

- ✅ `onayla.py`/`pipeline.batch_onayla()` HİÇ çağrılmadı (DB'den
  doğrulandı: 0 aktif satır, 2017-2022'nin TAMAMI için).
- ✅ Tam pytest paketi canlıya karşı çalıştırılmadı — yalnız hedefli
  `-k`/dosya bazlı testler kullanıldı, tam paket yalnız CI'nin
  postgres:16'sında koştu.
- ✅ Şema değişikliği yapılmadı (migration yok, `dim_grup`'a dokunulmadı).
- ✅ T10'un yapısal engeline takılan aylar (2017/2018/2019/2020 tümü,
  2021 Ocak-Ekim) BEKLEMEDE/kapsam_disi bırakıldı, uydurma yapılmadı,
  döngüye girilmedi. T4'ün "BOŞ-VERİ-ŞEHİR" anomalisi de aynı disiplinle
  (tahmin etmeden, açıkça atlanarak) çözüldü.
- ✅ Her mantıksal adım sonunda ayrı commit + push + CI doğrulaması yapıldı.
