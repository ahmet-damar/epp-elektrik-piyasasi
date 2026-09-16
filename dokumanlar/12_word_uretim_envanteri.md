# EPP — Word (.docx) Üretim Tabloları Envanteri (2016-2025)

> **STATUS: ACTIVE** — sonraki oturumun Word üretim (T2/T3/T5/T6 eşdeğeri)
> parser işini ucuzlatmak için hazırlanan bir başvuru envanteridir; kod
> içermez. Aşama 3/ADIM 3 madde 4 (Excel üretim backfill'i) TAMAMLANDI
> (bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §5.10) — bu doküman ADIM 4'ün
> (Word yılları) hazırlığıdır.

**Tarih:** 2026-09-09 (gece çalışması, gözetimsiz, MADDE 5 — KOD YAZILMADI,
yalnız araştırma). **Yöntem:** `worker/scripts/word_ortak.py`'nin MEVCUT
`basliklari_topla()` yardımcısıyla, her yılın Haziran ayı (temsili örnek,
`MANIFEST_20XX[6]`) + üç yıl için (2018, 2021, 2023) ayrıca Ocak/Aralık
spot-check'i — gerçek `.docx` dosyalarına karşı, kod yazılmadan.

## Kapsam — Excel karşılığı

| Excel | Word'de arananlar |
|---|---|
| T2 (Lisanslı, kaynak bazında) | "...Lisanslı Elektrik Üretiminin Kaynak Bazında Dağılımı..." |
| T3 (Lisanslı, il bazında) | "...Lisanslı Elektrik Üretiminin İl Bazında Dağılımı (MWh)..." |
| T5 (Lisanssız, kaynak bazında) | "...Lisanssız Elektrik Üretimi[nin] ... Kaynaklara Göre Dağılımı..." |
| T6 (Lisanssız, il bazında) | "...Lisanssız Elektrik Üretiminin İllere Göre Dağılımı (MWh-%)..." |

## Bulgu A — Tablo numaralandırması yıl yıl (hatta bazı yıl İÇİNDE) kayıyor — METİN ARAMA ZORUNLU

Aynen `07_word_parser_kapsam.md` Bulgu 2/Bulgu 5'te T11/T10/T4 için
kanıtlanan ilke, üretim tabloları için de GEÇERLİ — hiçbir sabit tablo
numarasına güvenilemez:

| Yıl | Kaynak (Lisanslı) | İl (Lisanslı) | Kaynak (Lisanssız) | İl (Lisanssız) | İl×Kaynak (Lisanssız, bkz. Bulgu C) |
|---|---|---|---|---|---|
| 2016 | Tablo-1.4 | Tablo-1.5 | Tablo 1.9 | Tablo 1.10 | Tablo 1.11 |
| 2017 | Tablo-1.5 | Tablo-1.6 | Tablo 1.10 | Tablo 1.11 | Tablo 1.12 |
| 2018 | Tablo-1.5 | Tablo-1.7 | Tablo 1.11 | Tablo 1.12 | Tablo 1.13 |
| 2019 | Tablo-1.5 | Tablo-1.7 | Tablo 1.11 | Tablo 1.12 | Tablo 1.13 |
| 2020 | Tablo-1.6 | Tablo-1.7 | Tablo 1.11 | Tablo 1.12 | Tablo 1.13 |
| 2021 (Ocak) | **"Tablo ."** (numara boş) | "Tablo ." | "Tablo ." | "Tablo ." | "Tablo ." |
| 2021 (Aralık) | Tablo 1.6 | Tablo 1.7 | Tablo 1.11 | Tablo 1.12 | Tablo 1.13 |
| 2022 | Tablo 1.6 | Tablo 1.7 | Tablo 1.11 | Tablo 1.12 (yeniden adlandırılmış, bkz. Bulgu D) | Tablo 1.13 |
| 2023 (Ocak) | **"Tablo ."** | "Tablo ." | "Tablo ." | "Tablo ." | "Tablo ." |
| 2023 (Haziran/Aralık) | Tablo 1.6 | Tablo 1.7 | Tablo 1.11 | Tablo 1.12 (Haziran'da VAR, **Aralık'ta YOK** — bkz. Bulgu E) | Tablo 1.13 (Haziran'da VAR, **Aralık'ta YOK**) |
| 2024 | Tablo 1.6 | Tablo 1.7 | Tablo 1.10 | **bulunamadı (bkz. Bulgu E)** | **bulunamadı (bkz. Bulgu E)** |
| 2025 | Tablo 1.6 | Tablo 1.7 | Tablo 1.10 | **bulunamadı (bkz. Bulgu E)** | **bulunamadı (bkz. Bulgu E)** |

**Önemli:** numara-kaybı (field-code boş render) 2021 VE 2023'ün Ocak
ayında görüldü ama AYNI yılın başka bir ayında (2021 Aralık, 2023
Haziran/Aralık) numara SAĞLAM — yani numara kaybı yıl-bazlı bir sabit
DEĞİL, ay ay değişebiliyor (T11/T10 için zaten bilinen "Ocak 2025"
örneğiyle AYNI fenomen, şimdi üretim tablolarında da doğrulandı). Metin
arama (`tek_aday_bul`, başlık FRAZI üzerinden — "Kaynak Bazında Dağılımı"
gibi, numara değil) tek güvenilir yöntem; bu zaten `word_ortak.py`'nin
mevcut ilkesi, üretim tabloları için YENİ bir risk değil, YALNIZCA aynı
riskin burada da geçerli olduğunun doğrulanması.

## Bulgu B — Kaynak-bazında (Lisanslı) tablolar 2017'den itibaren "dönemler-arası-karşılaştırma" formatında

2016 tek-dönem (`['KAYNAK TÜRÜ', 'ÜRETİM (MWh)', 'ORAN (%)']`, 3 kolon).
**2017'den 2025'e kadar HEPSİ** iki dönem yan yana + değişim yüzdesi
formatında: `['KAYNAK TÜRÜ', '<önceki yıl aynı ay>', '<önceki yıl aynı
ay>', '<hedef yıl aynı ay>', '<hedef yıl aynı ay>', 'DEĞİŞİM (%)']` (6
kolon — her dönem için "Miktar" + "Pay" alt-kolonu). Hedef ayın DOĞRU
kolonunu bulmak `worker/scripts/word_ortak.py:hedef_donem_kolonu_bul()`
ile (T10-eşdeğerinde ZATEN kullanılan mekanizma) yapılmalı — sabit "ilk
dönem kolonu" varsayımı YANLIŞ sonuç verir (2016-08-31'de T11/T10 için
zaten bulunan "yanlış (eski) sütun okunursa değer 1 yıl kaydırılır" riski
— bkz. `07_word_parser_kapsam.md` en alt paragraf — burada da AYNEN
geçerli).

**İl-bazında tablolar (Lisanslı VE Lisanssız, HER YIL) tek-dönem** —
karşılaştırma YOK, doğrudan o ayın kendi değeri.

## Bulgu C — Lisanssız için Word'de GERÇEK bir il×kaynak JOINT matris VAR (Excel'de YOK)

**Önemli, potansiyel karar gerektiren bulgu:** Aşama 3/ADIM 1
araştırması "EPDK hiçbir formatta il×kaynak joint üretim kırılımı
vermiyor" sonucuna varmıştı — bu sonuç **Excel (2026+) için hâlâ doğru**,
ama **Word yıllarında (2016-2023 doğrulandı) Lisanssız üretim için GERÇEK
bir il×kaynak matris tablosu var**: "...İllere ve Kaynaklara Göre
Dağılımı (MWh)..." — satırlar il, kolonlar kaynak türü (Biyokütle/Güneş/
Hidrolik/Rüzgar, +bazı yıllarda Doğalgaz), son kolon "Toplam". 2017
örneğinde doğrulanan başlık satırı: `['İLLER', 'Biyokütle', 'Güneş
(Fotovoltaik)', 'Hidrolik', 'Rüzgar', 'Toplam']`.

**Bu, Lisanslı için YOK** — Lisanslı hâlâ yalnız iki AYRI marjinal tablo
(kaynak-only + il-only), Excel'deki (ve Word'ün kurulu-güç tarafındaki
Bulgu 5) asimetriyle TUTARLI.

**✅ KARAR (2026-09-09, Ahmet):** Word'ün Lisanssız için sunduğu bu daha
ZENGİN il×kaynak veri **KULLANILMAYACAK**. Gerekçe: 2016-2023 (zengin,
il×kaynak) ile 2024+ (yalnız marjinal) arasında tanım/grain farkı olurdu
— Word-Excel sınırında davranış değiştiren bir KPI üretir, projenin
baştan beri kaçındığı grain karışımıdır (bkz. §5.5 T7/T11 dikişi kararı
— AYNI ilke). `fact_uretim.uretim_mwh`'yi Word yılları için doldurmak da
AYNI nedenle YAPILMAYACAK (2016-2023 dolu / 2024+ NULL bir kolon sınırda
kırılır). Serinin TAMAMI (2016-2026) TEK bir basitleştirilmiş
marjinal-only tanımda kalıyor — `fact_uretim_kaynak_geneli`/`fact_uretim_
il_geneli`'nin ADIM 3'te kurulan mimarisiyle DOĞRUDAN uyumlu, YENİ bir
tablo/grain kararı GEREKMEDİ. **İleride il×kaynak kırılımlı bir üretim
KPI'sı tanımlanırsa bu bulgu YENİDEN değerlendirilebilir** — Word
kaynağının bu veriyi taşıdığı GERÇEĞİ (yukarıdaki bulgu) hâlâ geçerli,
yalnız BİLİNÇLİ OLARAK kullanılmıyor. Detay: `05_kaynak_dosya_
sozlesmesi.md` "Word yılları — üretim kararları" bölümü.

## Bulgu D — 2016-2017'de "Brüt Lisanssız Üretim Miktarı" kolonu YOK (tanım kayması riski)

Kullanıcının önceden işaretlediği "Tablo 1.11'in 'Brüt Lisanssız Üretim
Miktarı' çapası" riski GERÇEK ve DOĞRULANDI — ama yalnız **2018'den
itibaren**:

- **2016-2017:** Lisanssız kaynak-bazında tablonun TEK değer kolonu
  `"İhtiyaç fazlası satın alınan enerji miktarı (MWh)"` — bu, şebekeye
  SATILAN fazla enerji (net bir alt-küme), TOPLAM brüt üretim DEĞİL.
- **2018'den itibaren (2018-2025 doğrulandı):** AYNI tabloda **AYRICA**
  `"Brüt Lisanssız Üretim Miktarı (MWh)"` kolonu VAR — Excel'in T5'iyle
  (`worker/parser.py:tablo5_lisanssiz_uretim_kaynak_oku`, "Brüt
  Lisanssız...") TANIM OLARAK EŞLEŞEN kolon budur, `"İhtiyaç fazlası..."`
  DEĞİL.

**✅ KARAR (2026-09-09, Ahmet — Karar 4):** 2016-2017 Lisanssız üretim
**KAPSAM DIŞI** sayılıyor (seçenek b) — bu iki yıl için "şebekeye satılan
fazla enerji" gibi dar bir metriği, Excel'in "Brüt Lisanssız Üretim"
tanımıyla aynı seriye karıştırmak sahte değer üretirdi (T7/T11 dikişinde
verilen kararla AYNI ilke — bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §5.5).
Lisanslı üretim ETKİLENMEZ. **Uygulandı (2026-09-09, canlıya):** migration
`20260909_0002` `veri_kapsam_disi.fact_tablosu` CHECK kısıtını
`fact_uretim_kaynak_geneli`/`fact_uretim_il_geneli` için genişletti;
`pipeline.kapsam_disi_isaretle()` ile 48 satır eklendi (2 tablo × 24 ay,
2016-01..2017-12, `nitelik='lisans_durumu=Lisanssız'`, `karar_referansi=
'Karar 4 (2026-09-09, Bulgu D)'`) — canlıda doğrulandı (48/48).

## Bulgu E — Bazı ay/yıllarda İl-bazında (Lisanssız) VE İl×Kaynak tabloları HİÇ bulunamadı

2023 Aralık taramasında (Haziran'da HER İKİSİ de vardı) ve 2024/2025
Haziran taramasında, "...Lisanssız Elektrik Üretiminin İllere Göre
Dağılımı..." VE "...İllere ve Kaynaklara Göre Dağılımı..." başlıklı
tablolar **bulunamadı** — tarama yalnız Tablo 1.10 (kaynaklara göre,
Brüt kolonu dahil) sonrasında doğrudan YEKDEM tablosuna atlıyor.

**Bu turda AÇIKLIĞA KAVUŞTURULMADI (araştırma kapsamı dışı bırakıldı,
kod yazılmadığı için tam metin taraması yapılmadı):** üç olası açıklama
var — (1) tablo gerçekten o ay/yıllarda BASILMADI (kaynakta yok), (2)
başlık metni bu turun anahtar kelime filtresinden (`"retim"` alt-dizisi)
KAÇACAK şekilde yeniden yazıldı, (3) tablo başka bir tabloyla
BİRLEŞTİRİLDİ. **ADIM 4'ün kod turunda İLK iş bu olmalı** — 2024/2025 ve
2023-Aralık dosyalarının TAM tablo listesi (yalnız "üretim" filtresi
OLMADAN) elle/`basliklari_topla()` ile tekrar taranmalı.

## Bulgu F — İl-bazında tablolar HER YIL iki-sütunlu sayfa düzeninde (kullanıcının önceden işaretlediği risk DOĞRULANDI)

Hem Lisanslı hem Lisanssız il-bazında tablolarda, TEK bir Word tablosu
İÇİNDE İL listesi ikiye bölünüp YAN YANA iki blok olarak basılıyor —
başlık satırı `['İLLER', 'ÜRETİM (MWh)', 'ORAN (%)', 'İLLER', 'ÜRETİM
(MWh)', 'ORAN (%)']` (6 kolon, 3+3 tekrar). Bu, kullanıcının "Tablo
1.12'nin iki-sütunlu sayfa düzeni" olarak önceden işaretlediği riskin
TAM olarak GENELLEŞTİRİLMİŞ hâli — yalnız belirli bir "Tablo 1.12" değil,
İL-BAZINDA HER TABLO (Lisanslı da Lisanssız da, HER YIL) bu düzende.
`worker/scripts/word_ortak.py`'de bu düzeni okuyacak (sol blok + sağ
bloğu ayrı ayrı, il_kodu_bul ile eşleyip BİRLEŞTİREN) bir yardımcı
fonksiyon HENÜZ YOK — ADIM 4'te yazılması gerekecek yeni bir parça.

## Bulgu G — Satır sayısı (il sayısı) yıl/ay bağımsız SABİT DEĞİL

T4-eşdeğeri için zaten bilinen "79-81 il" değişkenliği (Bulgu 5,
`07_word_parser_kapsam.md`) burada da gözlendi — il-bazında tablo satır
sayısı 36-42 arası değişti (iki-sütunlu düzende toplam ~72-84 il
hücresi). **Katı "81 il" assertion'ı burada da uygulanamaz** —
Genel Toplam/Toplam ile aritmetik tutarlılık kontrolü (T4-eşdeğerinde
zaten kullanılan yöntem) tercih edilmeli. **Not:** bu turda hiçbir
tablonun kendi "Genel Toplam"/"Toplam" satırının varlığı/konumu TEYİT
EDİLMEDİ (yalnız ilk satır — başlık satırı — okundu, tarama derinliği
kasıtlı sığ tutuldu) — ADIM 4'ün kod turunda erken bir adım bu olmalı.

## Bulgu H — T5/T6 (Lisanssız) 10 yılın TAMAMI için tam taranmış envanteri (2026-09-13)

> **⚠️ GÜNCELLEME (Bulgu L, aynı gün):** Aşağıdaki tablonun "VAR" sütunu
> T6'nın satır olarak VARLIĞINI doğru raporluyor ama "kullanılabilir"
> ANLAMINA GELMİYOR — ölçümle kanıtlandı ki T6, var olduğu HER yılda
> "Brüt Üretim" DEĞİL, "İhtiyaç Fazlası Satın Alınan" ölçüyor (bkz. Bulgu
> L). Nihai karar: T6 var olduğu her yıl (2016-2023 Haziran) KAPSAM DIŞI.

Bulgu E'nin (2024/2025 için tek-yıl bulgusu) sonucu, TÜM 10 yıl (2016-2025,
120 ay, filtre olmadan tam tablo listesi) için genelleştirildi — bu tur
öncesi Bulgu A'nın Haziran-ağırlıklı spot-check'inin (bazı yıllarda yalnız
1 ay) yerini alır:

| Yıl | T5 (Lisanssız, kaynak) | T6 (Lisanssız, il) |
|---|---|---|
| 2016 | VAR (12/12) | VAR (12/12) — "...Üretiminin İllere Göre Dağılımı" |
| 2017 | VAR (12/12) | VAR (12/12) — aynı başlık |
| 2018 | VAR (12/12), "Brüt Lisanssız Üretim Miktarı" kolonu VAR | VAR (12/12) |
| 2019 | VAR (12/12) | VAR (12/12) |
| 2020 | VAR (12/12) | VAR (12/12) |
| 2021 | VAR (12/12) | VAR (12/12) |
| 2022 | VAR (12/12) | VAR (12/12) **ama Haziran'dan itibaren yeniden adlandırıldı**: Ocak-Mayıs "...Üretiminin İllere Göre Dağılımı", Haziran-Aralık "...İHTİYAÇ FAZLASI SATIN ALINAN Lisanssız Elektrik Üretiminin İllere Göre Dağılımı" — Bulgu D'nin kaynak-seviyesi tanım sorununun İL seviyesinde bir tekrarı |
| 2023 | VAR (12/12) | VAR yalnız Ocak-Haziran (eski başlığa DÖNDÜ — "İhtiyaç Fazlası" değil), **Temmuz-Aralık'ta YOK** (6/12) |
| 2024 | VAR (12/12) | **YOK (0/12)** |
| 2025 | VAR (12/12) | **YOK (0/12)** |

**Not — 2016-2017 zaten kapsam dışı (Bulgu D/Karar 4):** bu iki yılın
T6'sı yapısal olarak VAR ama Karar 4 zaten bu yılların Lisanssız verisini
(kaynak seviyesindeki "Brüt Üretim" kolonu eksikliği yüzünden) kapsam dışı
bırakmıştı — T6'nın varlığı bu kararı değiştirmez, yalnız gerekçeyi
güçlendirir (aynı yıllarda hem kaynak HEM il tarafı zaten sorunlu).

**Sonuç — desen KARIŞIK (ne "hep var" ne "hiç yok"):** 2016-2022 (7 yıl)
T6 yapısal olarak var (2022 Haziran'dan itibaren tanım riski VAR), 2023
yıl-içi bölünmüş (H1 var, H2 yok), 2024-2025 tamamen yok. Bu, kullanıcı
kararı gereği "yıl yıl (gerekirse ay ay) `veri_kapsam_disi` kaydı"
gerektiren KARIŞIK durumdur — ne "2025 istisna" ne "hiçbir yılda yok"
basit kuralı uygulanamaz.

**✅ KARAR (2026-09-13, Ahmet):** Karışık desen doğrulandı — yıl/ay
bazında `veri_kapsam_disi` kaydı uygulanacak, mutabakat kontrolüne
İSTİSNA EKLENMEYECEK (yokluk zaten ilgili periyot için hiç veri
YÜKLENMEYEREK ifade edilir — mutabakat'ın karşılaştıracağı bir şey
kalmaz). T6 hiçbir yılda tamamen yok DEĞİL, bu yüzden KPI-07'nin Word
yıllarının TAMAMINDA dışlanması GEREKMİYOR — yalnız T6'nın gerçekten
YOK/şüpheli olduğu spesifik dönemlerde (2025 tümü, 2024 tümü, 2023
Temmuz-Aralık, ve 2022 Haziran-2023 Haziran'ın tanım-riskli aralığı
gelecek turlarda değerlendirilecek) hem `fact_uretim_kaynak_geneli` HEM
`fact_uretim_il_geneli`'nde Lisanssız simetrik olarak kapsam dışı
bırakılıyor (2016-2017 Karar 4 ile AYNI ilke — bir taraf yüklenip diğeri
yüklenmeyen asimetrik bir durum YARATILMIYOR).

## Bulgu I — 2024 T2'de üç-satırlık bölünmüş başlık (Mayıs/Kasım/Aralık)

2024'ün T2 (Lisanslı, kaynak bazında) tablosu, çoğu ayda 2025 ile AYNI
2-satırlık başlık yapısında (`donem_satiri` + `ÜRETİM/ORAN alt-başlığı`),
ama **Mayıs, Kasım ve Aralık 2024'te** Word'ün birleştirilmiş-hücre kaydı
"ORAN (%)" etiketini İKİYE bölmüş — 3. satır da hâlâ `'KAYNAK TÜRÜ'`
etiketini taşıyor, gerçek kaynak verisi 4. satırdan (index 3) başlıyor.
`t2_oku()`'da katı `tbl.rows[2:]` varsayımı YERİNE, ilk hücresi
`'KAYNAK TÜRÜ'` olan TÜM baştaki satırlar dinamik olarak atlanacak
şekilde düzeltildi (kaç satır olursa olsun) — regresyon testiyle
sabitlendi (`test_word_2024.py::test_t2_oku_uc_satirlik_bolunmus_
baslikla_da_calisir`).

## Bulgu J — 2024-02'nin T3 tablosu GERÇEKTEN hatalı (EPDK kaynak verisi, kod hatası DEĞİL)

`mutabakat_uretim.py` (T2↔T3 çapraz kontrolü) Şubat 2024 için **%11,45
fark** buldu — araştırıldı, ZORLA GEÇİRİLMEDİ:

- Şubat 2024 dosyasının T3 tablosu (`Tablo 1.7 Şubat 2024 Döneminde
  Lisanslı Elektrik Üretiminin İl Bazında Dağılımı`) **başlığı doğru
  ayı gösteriyor** ama İÇERİĞİ (satır satır, ÇANAKKALE'den başlayarak)
  **Ocak 2024'ün T3 tablosuyla ondalık basamağa kadar BİREBİR AYNI**
  (kendi Genel Toplam'ı da 28.549.038,63 — Ocak'ın 28.549.038,81'ine
  neredeyse eşit).
- Dosya bütünlüğü doğrulandı: Ocak ve Şubat 2024 dosyaları FARKLI
  dosyalar (farklı boyut, farklı SHA-256/MD5 hash) — bir manifest/
  dosya-kopyalama hatası DEĞİL.
- Şubat'ın T2 (kaynak bazında) tablosu ise GERÇEKTEN farklı/doğru veri
  taşıyor (Ocak'tan bariz farklı toplam ve kaynak dağılımı) — yalnız T3
  (il bazında) EPDK'nın kendi yayımladığı belgede STALE/kopyalanmış.
- **Sonuç: bu EPDK'nın kendi kaynak belgesindeki gerçek bir veri
  hatası** — `mutabakat_uretim.py`'nin TASARLANDIĞI GİBİ çalışıp
  yakaladığı bir örnek (T2 (kaynak) 6/7. bulgudaki parser bug'ından
  FARKLI olarak, burada BİZİM koddan değil KAYNAK belgeden kaynaklanan
  bir tutarsızlık). Zorla geçirilmedi — 202402 (Lisanslı) `mutabakat_
  uretim.py` çıktısında UYUMSUZ olarak işaretli kalıyor, disposable'da
  aktive edilmedi. Canlı backfill öncesi kullanıcı kararı gerekecek
  (T3'ü olduğu gibi mi kabul et, yoksa EPDK'nın olası bir düzeltme/
  yayımını mı bekle).

## Bulgu K — 2023'te yeni bir kaynak türü ('LPG'), Motorin zaten çözülmüştü

2023'ün T2 (Lisanslı, kaynak bazında) tablosunda Ağustos-Aralık aylarında
`'LPG'` adında, `worker/parser.py:KAYNAK_ESLEME`'de HİÇ karşılığı olmayan
bir satır bulundu. İncelendi:

- **LPG:** 12 ayın TAMAMINDA 2023'ün KENDİ üretim değeri (hedef_kolon,
  yani hedef ayın gerçek sütunu) her zaman `0,00` MWh — yalnız 2022
  karşılaştırma kolonunda küçük bir kalıntı var (Ağustos: 152,72 MWh,
  Aralık: 309,99 MWh gibi), "DEĞİŞİM %" sütunu hepsinde `-100,00` (yani
  2023'e gelindiğinde tamamen durmuş bir üretim). `worker/parser.py`'ye
  dokunulmadı (mimari karar) — `word_2023.py:_KAYNAK_ATLA_ETIKETLERI`'ne
  eklendi (kaynak_esle_zorunlu() bu etiketi 'atla' sayıyor). Güvence:
  `t2_oku()`'nun kendi Genel Toplam kontrolü, LPG'nin gelecekte
  sıfır-olmayan bir değer taşıdığı bir ay olursa bunu OTOMATİK yakalar
  (toplam tutmaz, ValueError) — regresyon testiyle bu güvence AYRICA
  kanıtlandı (kasıtlı sıfır-olmayan bir LPG değeriyle kurulan sentetik
  tabloda satırın GERÇEKTEN atlandığı, sessizce toplama karışmadığı
  doğrulandı).
- **Motorin (aynı tabloda, Kasım/Aralık 2023'te GERÇEK, sıfır olmayan
  üretim — 473,77 / 1.833,41 MWh):** araştırıldı ve YENİ bir değişiklik
  GEREKMEDİĞİ bulundu — `worker/parser.py:KAYNAK_ESLEME`'nin "Motorin"
  alias'ı zaten 2026-08-19'dan beri var, `dim_kaynak`'ta da zaten
  seed edilmiş (migration `20260819_0007_dim_kaynak_motorin_nafta.sql`,
  2026 Ocak Excel'inde bulunmuştu). Word 2023 verisi mevcut altyapıyla
  sorunsuz yüklendi.

**Sonuç:** disposable postgres:17'de 12/12 ay yüklendi, `mutabakat_
uretim.py` **12/12 uyumlu** (2023'te 2024'ün Bulgu J'sine benzer bir
kaynak-belge hatası GÖRÜLMEDİ).

## Bulgu L — T6 (il bazında Lisanssız) HİÇBİR ZAMAN "Brüt Üretim" değilmiş — Bulgu H'yi düzeltir (2026-09-13)

**Soru (kullanıcı talimatı):** 2022 Haziran'da T6'nın başlığı "Lisanssız
Elektrik Üretiminin İllere Göre Dağılımı"ndan "İhtiyaç Fazlası Satın
Alınan Lisanssız Elektrik Üretiminin İllere Göre Dağılımı"na değişiyor —
bu yalnızca bir yeniden adlandırma mı, yoksa gerçek bir tanım değişikliği
mi? **Başlığa bakıp varsayılmadı, sayıyla ölçüldü.**

**Yöntem:** Mart-Ağustos 2022 (rename sınırının her iki yanı) için hem
T6'nın (il) kendi toplamı HEM T5'in (kaynak) İKİ kolonu (İhtiyaç Fazlası
Satın Alınan / Brüt Lisanssız Üretim) ayrı ayrı hesaplandı, üç seri
karşılaştırıldı. Ek doğrulama: 2020 Ocak/Haziran (rename'den 2 yıl önce,
hâlâ eski/generic başlıkla) AYNI karşılaştırma tekrarlandı.

**Sonuç — rename sınırında yapısal bir SIÇRAMA YOK, ama daha büyük bir
gerçek ortaya çıktı:**

| Ay | T6 (il) toplamı | Kaynak: İhtiyaç Fazlası | Kaynak: Brüt Üretim |
|---|---|---|---|
| 2022-03 | 888.156,30 | 888.156,28 | 893.552,01 |
| 2022-04 | 1.166.160,66 | 1.166.160,68 | 1.200.804,97 |
| 2022-05 | 1.305.964,33 | 1.305.964,34 | 1.339.669,14 |
| 2022-06 (yeniden adlandırıldı) | 1.287.641,13 | 1.287.641,12 | 1.308.722,34 |
| 2022-07 (yeniden adlandırıldı) | 1.545.064,55 | 1.545.064,61 | 1.716.220,82 |
| 2022-08 (yeniden adlandırıldı) | 1.320.213,74 | 1.320.213,73 | 1.319.705,95 |
| 2020-01 (eski/generic başlık) | 551.436,09 | 551.436,09 | 563.604,23 |
| 2020-06 (eski/generic başlık) | 1.165.766,89 | 1.165.766,89 | 1.177.433,44 |

**T6'nın kendi il-toplamı, HER TEK AYDA (rename'den ÖNCE, SONRA, ve
rename'den 2 yıl önce fark etmeksizin) kaynak tablosunun "İhtiyaç
Fazlası Satın Alınan" kolonuyla ONDALIK BASAMAĞA KADAR BİREBİR eşleşiyor
— "Brüt Lisanssız Üretim Miktarı" kolonuyla DEĞİL** (fark her ayda
%0,04-%13 arası, rastgele/mevsimsel — sistematik bir "aynı tanım, küçük
yuvarlama" örüntüsü DEĞİL, iki FARKLI metrik).

**Yorum:** 2022 Haziran'daki başlık değişikliği bir TANIM DEĞİŞİKLİĞİ
DEĞİL — EPDK'nın başlığı, tablonun HER ZAMAN gerçekte ölçtüğü şeyi
(İhtiyaç Fazlası Satın Alınan) daha doğru yansıtacak şekilde
GÜNCELLENMESİ. Yani 2020'nin (ve muhtemelen tablo var olduğu HER yılın)
"generic" başlıklı T6'sı da ZATEN İhtiyaç Fazlası'ydı — yalnız başlığı
bunu SÖYLEMİYORDU.

**✅ KARAR (2026-09-13, Ahmet — ölçümle, tahmin YOK): Bulgu H'nin "2022
Haziran'dan itibaren tanım riski" ifadesi YETERSİZ KALDI — risk rename
ANINDA başlamıyor, T6 VAR OLDUĞU HER YIL boyunca (en azından 2020'den
2023 Haziran'a kadar ölçülen aralıkta) GEÇERLİ.** Bulgu D'nin ilkesiyle
BİREBİR tutarlı (2016-2017'nin kaynak tablosunda da "İhtiyaç Fazlası"
tek kolon olması AYNI şekilde kapsam dışı bırakılmıştı): **T6 (il
bazında Lisanssız), VAR OLDUĞU HER YIL (2016'dan 2023 Haziran'a kadar)
KAPSAM DIŞI** — Excel'in/T5'in "Brüt Lisanssız Üretim" tanımıyla HİÇBİR
ZAMAN eşleşmiyor. Bu, Bulgu H'nin tablosundaki "VAR" sütununu YANLIŞ
YAPMAZ (tablo GERÇEKTEN var, satır olarak) ama "kullanılabilir" anlamına
GELMEDİĞİNİ netleştirir — pratik sonuç: **fact_uretim_il_geneli'nin
Lisanssız kolonu artık TÜM Word yılları (2016-2025) için kapsam dışı**,
tek bir istisna kalmadan. T5 (kaynak, Brüt Üretim, 2018'den itibaren
sağlam) bu karardan ETKİLENMEZ — yalnız fact_uretim_il_geneli'nin karşı
tarafı olmadığından SİMETRİ için (2016-2017/2023-2025 ile AYNI ilke)
yüklenmeye devam etmiyor.

Detay/güncelleme: `dokumanlar/05_kaynak_dosya_sozlesmesi.md` "Word
yılları — üretim kararları" bölümüne Karar (Bulgu L) olarak eklendi.

## Bulgu M — 2021 Nisan'ın T2'sinde "RÜZGÂR" (inceltmeli, tüm-büyük) etiketi (2026-09-13)

2021'in T2 (Lisanslı, kaynak bazında) tablosu 12 ayın 11'inde â'sız
`"Rüzgar"` yazıyor (T4'ün her ayında olduğu gibi); yalnız **Nisan 2021**
`"RÜZGÂR"` (inceltme işaretli â, tüm-büyük) kullanıyor. Bu, daha önce
2025'in T5'inde (titlecase `"Rüzgâr"`) ve 2023'te (dokumanlar/08) görülen
AYNI sınıf yazım-varyansı — `worker/parser.py`'nin `_TR_SADE` çeviri
tablosu â/Â'yı ASCII'ye katlamadığı için her yeni görülen tam-eşleşme
kendi yılının `_KAYNAK_TAKMA_ADLAR`'ına eklenmek zorunda (mimari karar:
`worker/parser.py`'ye dokunulmuyor). 2021'in daha önce boş olan
`_KAYNAK_TAKMA_ADLAR`'ına `{"RÜZGÂR": "Rüzgar"}` eklendi. Bu ay dışında
(2021'in diğer 11 ayı + tüm T4) format sürprizi YOK.

**Sonuç:** disposable postgres:17'de 12/12 ay yüklendi, `mutabakat_
uretim.py` **12/12 uyumlu**. +6 yeni regresyon testi (`test_word_2021.py`:
RÜZGÂR alias, `t2_oku`/`t3_oku` normal+Genel-Toplam-uyuşmazlığı senaryoları).

**2020 (T2+T3 Lisanslı) tamamlandı (2026-09-13):** 12 ayın TAMAMI dry-run
ile ÖNCEDEN tarandı — Bulgu I/M sınıfı bir format sürprizi (bölünmüş
başlık, â/Â kaynak varyantı) YOK, hepsi düz 2-satırlı T2 + 2-sütunlu T3.
Kaynak etiketleri tüm-büyük ama tümü zaten tanınıyor (DOĞAL GAZ, İTHAL
KÖMÜR, HİDROLİK, RÜZGAR [â'sız], GÜNEŞ, JEOTERMAL, BİYOKÜTLE, LİNYİT,
ASFALTİT, TAŞ KÖMÜRÜ, MOTORİN — hiçbiri yeni bir `_KAYNAK_TAKMA_ADLAR`
girdisi gerektirmedi). Lisanssız (T5/T6) Bulgu L kararıyla (2020 zaten
Bulgu L'nin ÖLÇÜM aralığının bir parçasıydı — Ocak/Haziran doğrudan
kontrol edilmişti) TÜM yıl kapsam dışı. Disposable postgres:17'de 12/12
ay yüklendi, `mutabakat_uretim.py` **12/12 uyumlu**. +4 yeni regresyon
testi (`test_word_2020.py`: `t2_oku`/`t3_oku` normal+Genel-Toplam-
uyuşmazlığı senaryoları).

## Bulgu N — 2019 T2'de Hidrolik "AKARSU"+"BARAJLI HİDROLİK" diye İKİ satıra bölünmüş (2026-09-13)

2019'un T2 (Lisanslı, kaynak bazında) tablosu **Ocak-Kasım'da** Hidrolik'i
tek satır olarak DEĞİL, `"AKARSU"` + `"BARAJLI HİDROLİK"` diye İKİ AYRI
satır olarak veriyor (**Aralık'ta tek `"HİDROLİK"` satırı** — established
tekleşme, diğer yılların hepsindeki gibi). `worker/parser.py:KAYNAK_
ESLEME`'de zaten `(["Akarsu", "Barajlı", "Hidrolik"], "Hidrolik", True)`
girdisi var ve modül notu ("Akarsu+Barajlı→Hidrolik ... toplanmalı, ayrı
satır üretilmez") bu iki alt-kategorinin TOPLANMASI gerektiğini baştan
söylüyor — ama eşleme TAM METİN karşılaştırması (`_sade_anahtar`) olduğu
için `"AKARSU"` tek başına eşleşirken `"BARAJLI HİDROLİK"` (iki kelime
BİRLEŞİK) eşleşmiyor.

Bu, T2'nin (uzun/dikey format) diğer yıllarda hiç karşılaşmadığı YENİ bir
durum: aynı ay içinde İKİ FARKLI satırın AYNI kanonik kaynağa eşlenmesi.
Önceki yıllarda bu durum yalnız T4'ün (matris format, "Güneş
(Fotovoltaik)"+"Güneş (Yoğunlş.)" — 2019'un kendi T4'ünde de var, zaten
çözülmüştü) YATAY (kolon) versiyonunda görülmüştü. **Ölçülmeden geçilip
zorla yüklenirse:** `fact_uretim_kaynak_geneli`'nin `UNIQUE(tarih_id,
kaynak_id, lisans_id, ingestion_batch_id)` kısıtı İKİNCİ "Hidrolik"
satırının eklenmesini REDDEDER (batch hata verirdi) — kod yazılmadan önce
tam T2 tablosu dökümü alınarak bu ÖNCEDEN tespit edildi, canlıda/
disposable'da hataya düşülmeden.

**Karar (kod, T4'ün established "TOPLA" ilkesiyle AYNI):** `word_2019.py`
`_KAYNAK_TAKMA_ADLAR`'ına `{"BARAJLI HİDROLİK": "Hidrolik"}` eklendi
("AKARSU" zaten `worker/parser.py`'nin kendi alias'ıyla "Hidrolik"e
eşleniyor); `t2_oku()` artık satırları doğrudan DataFrame'e eklemek
yerine `dict[kaynak, toplam]` biriktiricisiyle TOPLUYOR, tek "Hidrolik"
satırı üretiyor. Aritmetik (Genel Toplam) etkilenmez — toplama işlemi
toplamı korur, yalnız satır sayısını azaltır. Diğer 11 kaynak türü
etkilenmedi.

**Sonuç:** disposable postgres:17'de 12/12 ay yüklendi (Ocak-Kasım'ın
her biri Hidrolik'i başarıyla TEK satıra indirdi, UNIQUE ihlali YOK),
`mutabakat_uretim.py` **12/12 uyumlu**. +3 yeni regresyon testi
(`test_word_2019.py`: alias eşlemesi + `t2_oku`'nun toplama davranışı +
Genel-Toplam-uyuşmazlığı).

**2018 (T2+T3 Lisanslı) tamamlandı (2026-09-13):** kod yazmadan ÖNCE tam
T2/T3 dökümüyle 12 ay tarandı — İKİ desen zaten bilinen sınıflardan:
(1) **Bulgu I sınıfı** — Temmuz-Aralık'ın T2'si 3-satırlık BÖLÜNMÜŞ
başlık kullanıyor ("ORAN (%)" iki satıra ayrılmış, 2024'ün Bulgu I'iyle
AYNI desen), dinamik `veri_baslangic` while-loop'u (2020-2025'ten
taşınan established mekanizma) sorunsuz atladı; (2) **Bulgu N** —
2019'dan FARKLI olarak 12 ayın TAMAMINDA (Aralık DAHİL, 2019'da Aralık
tekleşiyordu) Hidrolik "AKARSU"+"BARAJLI HİDROLİK" diye ikiye bölünmüş,
AYNI `dict` biriktirici çözümü kullanıldı. T3'ün il sayısı ay ay
değişiyor (Ocak 78, çoğu ay 79, Kasım 80 — established Bulgu G, kod
değişikliği GEREKTİRMEDİ, `t3_oku()` zaten hiçbir sabit sayı
varsaymıyor). Lisanssız (T5/T6) Bulgu L kararıyla TÜM yıl kapsam dışı.
Disposable postgres:17'de (fresh, tek başına) 12/12 ay yüklendi,
`mutabakat_uretim.py` **12/12 uyumlu**. +4 yeni regresyon testi
(`test_word_2018.py`: alias eşlemesi, `t2_oku`'nun toplama davranışı,
3-satırlık bölünmüş başlık, Genel-Toplam-uyuşmazlığı).

## Bulgu O — 2016-2017 GENİŞLETİLMİŞ dry-run taraması (2026-09-13, KOD YAZILMADI)

ADIM 4'ün "Excel'e en yakın 8 yıl" (2018-2025) fazı bittikten sonra,
2016-2017 için — bu iki yıl önceki Word genişletmesinde (T4/T10/T11,
dokumanlar/08) EN ZORLU olarak işaretlendiği için — kod yazılmadan
ÖNCE GENİŞLETİLMİŞ bir tarama yapıldı: 24 ayın (2016: 12, 2017: 12)
TAMAMI için T2/T3'ün varlığı, tam başlık metni, satır/kolon yapısı, il
sayısı ve TÜM kaynak etiketleri tek tek dökümlendi. **Aşağıdaki
bulguların HİÇBİRİ için kod yazılmadı — bu bölüm yalnız envanterdir,
sıradaki turda karar+uygulama yapılacak.**

### 1. Görünüşte "tablo yok" olan 4 ay — İKİSİ DE GERÇEK YOKLUK DEĞİL

İlk taramada basit bir başlık-metni arama (2018-2025'in kullandığı
`icerir=["Lisanslı Elektrik Üretiminin Kaynak/İl Bazında Dağılımı"]`)
şu 4 ayda "BULUNAMADI" sonucu verdi: **2016 Ocak/Şubat** (T2 VE T3
ikisi de) ve **2017 Kasım/Aralık** (yalnız T2). Tam tablo başlığı
dökümü alınarak İKİSİ de araştırıldı, İKİSİ de GERÇEK YOKLUK
DEĞİL — arama metni yetersiz kaldığı için "bulunamadı" görünmüş:

- **2016 Ocak/Şubat:** Tablo GERÇEKTEN var (`Tablo-1.4 Ocak 2016
  Döneminde Elektrik Üretiminin Kaynak Bazında Dağılımı (MWh)`) — ama
  başlıkta **"Lisanslı" kelimesi YOK** (Mart 2016'dan itibaren "...
  Döneminde **Lisanslı** Elektrik Üretiminin..." diye değişiyor). Aynı
  durum T3'ün karşılığı için de geçerli (`Tablo-1.5 ... Elektrik
  Üretiminin İl Bazında Dağılımı`). İçerik doğrudan dökümlendi: Ocak
  2016'nın T2'si `['Kaynak Türü', 'Üretim Miktarı (MWh)', 'Oran (%)']`
  başlıklı, T3'ü `['İL', 'Üretim Miktarı (MWh)', 'Oran (%)', 'İL', ...]`
  (Şubat'ta "İLLER" — tekil/çoğul da ay ay değişiyor) — yani YAPI Mart-
  Aralık ile AYNI, yalnız İKİ AYIN başlık metni "Lisanslı"sız.
- **2017 Kasım/Aralık:** Tablo GERÇEKTEN var (`Tablo-1.5 Kasım 2017
  Döneminde Lisanslı Elektrik Üretiminin Kaynak Bazında Dağılımı Ve
  2016 Yılı Kasım Ayı Değeriyle Karşılaştırılması`) — ama bu iki ayda
  EPDK AYRICA bir **YILLIK KÜMÜLATİF karşılaştırma tablosu** ekliyor
  (`Tablo-1.6 Ocak-Kasım 2017 Döneminde Lisanslı Elektrik Üretiminin
  Kaynak Bazında Dağılımı Ve 2016 Yılı Ocak-Kasım Dönemi Değeriyle
  Karşılaştırılması`) — bu YENİ tablo da AYNI arama alt-dizisini
  ("Lisanslı Elektrik Üretiminin Kaynak Bazında Dağılımı") taşıdığından
  `tek_aday_bul()` İKİ ADAY bulup belirsizlik hatası fırlatıyor (kod
  bunu "BULUNAMADI" gibi YUTMUŞ, gerçek hatayı GÖSTERMEMİŞ — dry-run
  script'inin kendi kusuru, `word_20XX.py`'nin DEĞİL). T3'ün karşılığı
  (`Tablo-1.7`) BU İKİ AYDA sorunsuz TEK ADAY olarak bulundu (kümülatif
  bir il-bazlı tablo EKLENMEMİŞ, yalnız kaynak-bazlı YTD tablosu var).

**Sonuç:** 24 ayın TAMAMINDA T2 VE T3 GERÇEKTEN mevcut — "tamamen yokluk"
sınıfında (2016'nın T10'u gibi) HİÇBİR ay yok. Gelecek turda: 2016
Ocak/Şubat için arama metninden "Lisanslı" çıkarılmalı (`icermez=
["Lisanssız"]` ile T5-eşdeğerine karışması önlenerek); 2017 Kasım/Aralık
için arama metnine `icermez=["Ocak-"]` (ya da benzeri YTD-dışlayan bir
filtre) eklenmeli.

### 2. 2016'nın T2'si TÜM DİĞER YILLARDAN YAPISAL OLARAK FARKLI — EN ÖNEMLİ BULGU

**2017-2025'in T2'si HEP dönemler-arası-karşılaştırma formatında** (6
kolon: önceki yıl ÜRETİM+ORAN, hedef yıl ÜRETİM+ORAN, DEĞİŞİM — bkz.
Bulgu B), bu yüzden `hedef_donem_kolonu_bul()` ile "doğru dönem
kolonunu seç" mantığı GEREKİYORDU. **2016'nın T2'si (TÜM 12 ay, Ocak-
Aralık) YALNIZ 3 KOLONLU TEK-DÖNEM formatında**: `Kaynak Türü | Üretim
Miktarı (MWh) | Oran (%)` — önceki yılla karşılaştırma YOK, seçilecek
"hedef dönem kolonu" da YOK, tablonun TAMAMI zaten hedef ayın verisi.
**Bu, `hedef_donem_kolonu_bul()`'ün 2017-2025'te KULLANILAMAYACAĞI
anlamına geliyor** — 2016'nın gelecekteki `t2_oku()`'sü BAŞTAN FARKLI
yazılmalı (kolon seçimi YOK, doğrudan sabit kolon indeksinden okuma;
veri satırları `tbl.rows[1:]`'den başlıyor, `tbl.rows[2:]` DEĞİL). T3'ün
YAPISI (iki-sütunlu il bloğu, `iki_blokta_il_degerlerini_oku()`) 2016'da
da AYNI kalıyor (yalnız başlık hücre metinleri "İL"/"İLLER" arası
salınıyor — `iki_blokta_il_degerlerini_oku()` zaten başlık metnine
bakmıyor, POZİSYONA güveniyor, bu yüzden ETKİLENMEZ).

### 3. Bulgu N (Hidrolik ikiye bölünmüş) HER İKİ YILDA DA VAR — farklı etiketle

**2017:** `"AKARSU"` + `"BARAJLI HİDROLİK"` (2018/2019 ile AYNI etiket) —
`"BARAJLI HİDROLİK"` `TANINMIYOR` (worker/parser.py'nin "Barajlı" alias'ı
TEK kelime, "Barajlı Hidrolik" birleşik metinle eşleşmiyor) — Bulgu N'in
AYNI çözümü (alias + `dict` toplama) uygulanabilir.

**2016:** Etiket FARKLI — yalnız `"BARAJLI"` (Hidrolik'siz, "BARAJLI
HİDROLİK" DEĞİL) — bu zaten `worker/parser.py:KAYNAK_ESLEME`'nin kendi
`"Barajlı"` girdisiyle **TANINIYOR**, YENİ bir alias GEREKMİYOR. Ama
**AYNI TOPLAMA sorunu yine de var**: Mart 2016'nın T2 dökümünde
`AKARSU` (satır 1) VE `BARAJLI` (satır 3) AYRI satırlar olarak
görünüyor, ikisi de `"Hidrolik"`e eşleniyor — zorla yüklenirse AYNI
UNIQUE kısıt ihlaliyle karşılaşılır. **Sonuç: 2016'nın `t2_oku()`'sü de
Bulgu N'in `dict`-biriktirici deseniyle yazılmalı, yalnız YENİ bir
`_KAYNAK_TAKMA_ADLAR` girdisi gerekmiyor.**

### 4. Bulgu I sınıfı (bölünmüş başlık) — yalnız 2017 Ekim'de görüldü

2017'nin T2'si Ocak-Eylül'de düz 2-satırlık başlık, **Ekim'de** 3-
satırlık bölünmüş başlık ("ORAN" satır 1'de, "(%)" satır 2'de — 2018/
2024 ile AYNI desen) kullanıyor. Established dinamik `veri_baslangic`
while-loop'u ek kod gerekmeden çözer. 2016'da bu desen HİÇ görülmedi
(zaten tek-satırlık başlık formatı kullanıyor — bkz. madde 2).

### 5. Kaynak etiketleri — YENİ/tanınmayan bir tür YOK (Bulgu N hariç)

2016 ve 2017'nin TÜM T2 kaynak etiketleri (`AKARSU, ASFALTİT/ASFALTİT
KÖMÜR, BARAJLI/BARAJLI HİDROLİK, BİYOKÜTLE, DOĞAL GAZ, FUEL OİL, GÜNEŞ,
JEOTERMAL, LNG, LİNYİT, MOTORİN, NAFTA (yalnız 2016), RÜZGAR, TAŞ KÖMÜR/
TAŞ KÖMÜRÜ, İTHAL KÖMÜR`) `worker/parser.py:KAYNAK_ESLEME`'de ZATEN
tanınıyor — Bulgu N'in "Barajlı Hidrolik" birleşik-metin istisnası
DIŞINDA yeni bir `_KAYNAK_TAKMA_ADLAR` girdisi GEREKMEDİ. **Uyarı:** bu
tarama yalnız `tbl.rows[2:]`'yi topladı (2016 için `tbl.rows[1:]`
OLMALIYDI, madde 2'deki yapısal farktan dolayı) — üretim turunda TAM
12 ayın TAM satır listesi yeniden, doğru offset'le taranmalı (bu tarama
ÖNGÖRÜCÜ, KESİN DEĞİL).

### 6. T3'ün il sayısı — established Bulgu G deseniyle tutarlı, kod değişikliği gerekmiyor

2016: 77-80 il/ay (42→80, 41→78-79, 40→76-77 satır/il oranı korunuyor).
2017: 76-80 il/ay. İkisi de 2018-2019'un 78-81 aralığıyla AYNI sınıfta
— `t3_oku()`'nun eksik-il-sıfırlama + Genel-Toplam-doğrulama tasarımı
zaten HİÇBİR sabit sayı varsaymadığından bu KOD DEĞİŞİKLİĞİ GEREKTİRMEZ.

### 7. Lisanssız (T5/T6) — Bulgu D zaten kapsıyor, yeni inceleme gerekmedi

Ocak 2016'nın başlık listesi doğrulandı: `Tablo 1.9 ... Lisanssız
Elektrik Üretiminin Kaynaklara Dağılımı` (T5-eşdeğeri) ve `Tablo 1.10
... Lisanssız Elektrik Üretiminin İllere Göre Dağılımı` (T6-eşdeğeri)
İKİSİ de MEVCUT — Bulgu D'nin zaten belgelediği "Brüt Lisanssız Üretim
Miktarı kolonu YOK" kararı (Karar 4) bu iki yıl için GEÇERLİLİĞİNİ
KORUYOR, yeniden ölçüm gerekmedi (kullanıcının önceden verdiği kural).

### Özet — 2016-2017 uygulaması İÇİN gereken ek işler (karar DEĞİL, yalnız envanter)

| Konu | 2016 | 2017 |
|---|---|---|
| T2 formatı | **BAŞKA** (tek-dönem, 3 kolon) — bespoke `t2_oku()` gerekir | Standart (2018-2025 ile AYNI, 6 kolon) |
| Ocak/Şubat (2016) veya Kasım/Aralık (2017) arama metni | "Lisanslı" çıkarılmalı | `icermez=["Ocak-"]` (YTD tablosu dışlanmalı) |
| Bulgu N (Hidrolik toplama) | GEREKİYOR, yeni alias GEREKMİYOR | GEREKİYOR, `"BARAJLI HİDROLİK"` alias'ı gerekiyor |
| Bulgu I sınıfı (bölünmüş başlık) | Görülmedi | Yalnız Ekim'de var, established çözüm yeterli |
| T3 il sayısı değişimi | Var (77-80), established desen | Var (76-80), established desen |
| Lisanssız (T5/T6) | Bulgu D ile zaten kapsam dışı | Bulgu D ile zaten kapsam dışı |

**2017 (T2+T3 Lisanslı) tamamlandı (2026-09-16):** Bulgu O'nun öngörüleri
BİREBİR doğrulandı, YENİ bir sürpriz çıkmadı. `_KAYNAK_TAKMA_ADLAR`'a
`{"BARAJLI HİDROLİK": "Hidrolik"}` eklendi (Bulgu N, 12 ayın TAMAMINDA
`dict`-biriktiricisiyle toplanıyor — 2018 ile AYNI, Aralık'ta bile
tekleşmiyor). Ekim'in 3-satırlık bölünmüş başlığı (Bulgu I sınıfı)
established dinamik `veri_baslangic` while-loop'uyla sorunsuz geçti.
Kasım/Aralık'ın T2/T3 arama ambiguity'si `icermez=["Ocak-"]` ile
çözüldü (YTD kümülatif tablo dışlandı, Ocak'ın kendi ayı yanlışlıkla
dışlanmadı — doğrulandı). Disposable postgres:17'de 12/12 ay yüklendi,
`mutabakat_uretim.py` **12/12 uyumlu**. +5 yeni regresyon testi
(`test_word_2017.py`: alias eşlemesi, `t2_oku`'nun toplama davranışı,
3-satırlık bölünmüş başlık, Genel-Toplam-uyuşmazlığı × 2).

## Özet — ADIM 4 (Word üretim backfill'i) için önerilen sıra (öneri, karar DEĞİL)

1. Bulgu E'yi çöz: 2023-Aralık + 2024/2025'in TAM tablo listesini (filtre
   olmadan) tara, il-bazında/il×kaynak Lisanssız tablolarının GERÇEKTEN
   yok mu yoksa yeniden adlandırılmış mı olduğunu netleştir.
   Her tablonun kendi Genel Toplam/Toplam satırının varlığını/konumunu
   doğrula (Bulgu G).
2. ~~Bulgu D'nin kararını al~~ **YAPILDI (2026-09-09) — KAPSAM DIŞI,
   Karar 4, `veri_kapsam_disi`'ye 48 satır eklendi.**
3. ~~Bulgu C'nin kararını al~~ **YAPILDI (2026-09-09) — KULLANILMAYACAK,
   marjinal-only tutarlılık tercih edildi.**
4. İki yeni `word_ortak.py` yardımcısı yaz: (a) iki-sütunlu il tablosu
   okuyucu (Bulgu F), (b) `hedef_donem_kolonu_bul()`'ün kaynak-bazında
   tablolara uygulanması (zaten var olan fonksiyon, yeni bir çağıran
   gerekiyor yalnız).
5. Her yıl için (2016-2025, T4/T11/T10 desenindeki gibi) AYRI bir tarif
   (`word_20XX.py`'ye eklenecek `t2_oku()`/`t3_oku()`/`t5_oku()`/
   `t6_oku()` fonksiyonları) — TEK bir "genel algılama motoru" DEĞİL
   (proje disiplini, bkz. `07_word_parser_kapsam.md` "Mimari Kapsam
   Netliği").
6. Her yıl kendi regresyon testiyle KAPATILSIN (T4/T11/T10 deseniyle
   AYNI) — bu envanterdeki 12 aylık spot-check YETERLİ DEĞİL, her yılın
   TÜM 12 ayı gerçek dosyaya karşı doğrulanmalı (Bulgu A'nın "numara
   kaybı ay ay değişebiliyor" bulgusunun gösterdiği gibi tek bir ayın
   testi yıl için temsili sayılamaz).
