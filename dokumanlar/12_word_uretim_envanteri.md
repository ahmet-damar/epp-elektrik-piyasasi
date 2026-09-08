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

**⚠️ Karar gerektiren açık soru (BU TURDA ÇÖZÜLMEDİ):** Word'ün Lisanssız
için sunduğu bu daha ZENGİN veri kullanılsın mı (gerçek il×kaynak grain'i
`fact_uretim`'e yazılabilir — yalnız Lisanssız için, yalnız Word
yıllarında), yoksa serinin TAMAMI (2016-2026) TEK bir basitleştirilmiş
marjinal-only tanımda mı tutulsun (Excel ile simetri, `fact_uretim_
kaynak_geneli`/`fact_uretim_il_geneli`'nin şu anki AYRI-marjinal
tasarımıyla tutarlı)? İkinci seçenek daha basit ve ADIM 3'ün zaten kurulu
mimarisiyle (2026-09-09 gecesi tamamlanan) doğrudan uyumlu; birincisi
daha fazla bilgi taşır ama YENİ bir tablo/grain kararı gerektirir (`fact_
uretim`'in kendi il×kaynak grain'ine mi yazılır, yoksa üçüncü bir tabloya
mı?). **Ahmet'in kararı bekliyor — bu doküman yalnız bulguyu kaydediyor.**

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

**Sonuç: 2016-2017 için Excel'in T5/T6 tanımıyla (Brüt üretim) BİREBİR
eşleşen bir Word kaynağı YOK** — yalnız "şebekeye satılan fazla enerji"
gibi DAHA DAR bir metrik var. Bu iki yıl için ya (a) bu daha dar metrik
FARKLI bir tanım olarak AÇIKÇA işaretlenip ayrı tutulmalı (Karar 1/3
mekanzimasındaki gibi `veri_kapsam_disi`'ye not düşülebilir), ya da (b)
Lisanssız üretim serisi 2018'den başlatılmalı (2016-2017 için "kaynakta
yok" sayılmalı). **Karar bu turda VERİLMEDİ** — ADIM 4'ün (Word backfill)
kod turunda çözülecek.

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

## Özet — ADIM 4 (Word üretim backfill'i) için önerilen sıra (öneri, karar DEĞİL)

1. Bulgu E'yi çöz: 2023-Aralık + 2024/2025'in TAM tablo listesini (filtre
   olmadan) tara, il-bazında/il×kaynak Lisanssız tablolarının GERÇEKTEN
   yok mu yoksa yeniden adlandırılmış mı olduğunu netleştir.
   Her tablonun kendi Genel Toplam/Toplam satırının varlığını/konumunu
   doğrula (Bulgu G).
2. Bulgu D'nin kararını (2016-2017 Lisanssız kapsam dışı mı, yoksa dar
   tanımla mı işaretlenip dahil edilecek) Ahmet'ten al.
3. Bulgu C'nin kararını (Lisanssız için zengin il×kaynak verisi
   kullanılsın mı, yoksa marjinal-only tutarlılık mı tercih edilsin) al.
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
