# EPP — Word (.docx) EPDK Raporları: Teşhis + Kapsam Kararları

**Tarih:** 2026-08-31 · **Durum:** Teşhis tamamlandı, kod YAZILMADI — uygulama
ayrı bir oturumda başlayacak. Bu dosya, o oturumun başlangıç noktasıdır.

## Bağlam

SRS v1.4 Bölüm 2.1, MVP kapsamını "2026+ Excel, öncesi Word" olarak tanımlıyor
— bu, projede daha önce hiç kodlanmamıştı (yalnız `worker/parser.py`'nin
Excel/openpyxl yolu var). Bu tur, eski yılların Word formatındaki aylık
"Elektrik Piyasası Sektör Raporu" dosyalarını (Kapasite Projeksiyonu/Gelişim
Raporu PDF'leri KAPSAM DIŞI) parse etmenin fizibilitesini ve gerçek kapsamını
teşhis etti. **Strateji: yakından uzağa** — 2023-2025 önce, format
doğrulanınca geriye (2016-2022) genişlet.

**İncelenen örnek dosyalar** (`C:\Users\adama\Downloads\EPDK Verileri\`):
Ocak 2025, Mart 2024, Şubat 2023 — üçü de gerçek `.docx` (ZIP/OOXML,
`python-docx` ile açılabiliyor; `requirements.txt`'de deklare edilmemiş
olsa da ortamda kurulu — **bulgu**: bağımlılığı deklare etmeyi unutmayalım,
uygulama turunda `requirements.txt`'ye eklenmeli).

## Mimari Kapsam Netliği — Tek Seferlik Aktarım, Kalıcı Pipeline Bileşeni Değil

(2026-08-31, kullanıcı netleştirdi.) Bu docx parser'ı **KALICI bir pipeline
bileşeni DEĞİL, TEK SEFERLİK bir tarihsel veri aktarımı**. Eski Word
dosyaları bir kere içeri alınacak, sonra hiç tekrar çalışmayacak —
gelecekteki tüm yeni veriler zaten güncel Excel parser'ıyla
(`worker/parser.py`) işlenmeye devam edecek. Bu, tasarımı iki yönden
değiştiriyor:

**1) Konum — `worker/parser.py`'a kalıcı bir "docx dalı" EKLENMEYECEK.**
Onun yerine ayrı, tek-seferlik bir script/modül: `worker/scripts/
gecmis_veri_aktarimi.py` (isim örnektir, uygulama turunda kesinleşir) —
`worker/scripts/backfill.py`/`onayla.py` ile aynı konvansiyon (CLI script,
kalıcı bir API yüzeyi değil, kullanılıp bırakılacak). `worker/parser.py`
uzun vadede bakımını üstlenmemiz gereken, HER ZAMAN çalışan bir modül;
docx kodu onun bir parçası OLMAMALI — ileride birisi `worker/parser.py`'yi
okuyup "docx dalı neden hâlâ burada, kim kullanıyor" diye sormasın.

**2) Genellik/esneklik seviyesi — "her formatı otomatik anlayan tek genel
parser" YAZILMAYACAK.** Format setini (2010-2025 arası kaç farklı şablon
varsa) BİR KERE, elle/yarı-elle keşfedip **her yıl (ya da her şablon
varyasyonu) için AYRI, açık bir eşleme tarifi (mapping recipe)** yazmak
tercih edilir — genel bir "otomatik algıla" motoruna göre daha az riskli
ve muhtemelen daha hızlı, çünkü kod ASLA gelecekte görmediği bir formatla
karşılaşmayacak (kalıcı bir pipeline'daki "her zaman sağlam kalmalı"
baskısı yok, tersine her yıl için KODU BİR KERE GEÇİRİP kapatacağız).
Aşağıdaki Bulgu 2'deki "sabit index değil, metin arama" ilkesi hâlâ
geçerli (TEK bir yıl İÇİNDE bile ay ay küçük kaymalar olabilir, bkz.
Excel'deki Mart 2026 T13 örneği, `06_canli_veri_operasyon_gunlugu.md`) —
ama bu, HER YIL için AYRI YAZILAN bir tarifin İÇİNDE uygulanacak bir
sağlamlık önlemi; "tüm yılları TEK kod yolunda otomatik ayırt et" hedefi
DEĞİL.

**3) Disiplin DEĞİŞMİYOR.** Veri DB'ye nasıl girerse girsin
`ingestion_batch`/`audit_log`/`is_active` bütünlük kuralı AYNI kalır (bkz.
`worker/pipeline.py`, `worker/ingest.py`). Tek seferlik script bu
primitifleri (`ingest.kaynak_asset_olustur`, `ingest.batch_olustur`,
`ingest.fact_*_yukle`, `pipeline.batch_onayla`, otomatik `audit_log`
yazımı) DOĞRUDAN çağırmalı — kendi paralel bir yazma yolu İCAT ETMEMELİ.

## Bulgu 1 — Tablo yapısı Excel'den kökten farklı

Excel'de her "Tablo N" ayrı bir çalışma sayfası; Word'de **27-28 tablo, TEK
`document.xml` içinde**, sırayla paragraf başlıklarıyla ayrılmış. python-docx
resmi API'si (`document.tables`) paragraf↔tablo sırasını VERMİYOR — hangi
paragrafın hangi tablonun başlığı olduğunu bulmak için `document.element.
body.iterchildren()` ile XML seviyesinde manuel gezinme gerekti (paragraf ve
tablo elemanlarını orijinal doküman sırasında karışık dolaşan bir yardımcı
fonksiyon yazıldı, teşhis sırasında doğrulandı — uygulama turunda tek-seferlik
aktarım script'inin (`worker/scripts/`, bkz. yukarıdaki "Mimari Kapsam
Netliği") bir yardımcı fonksiyonu olarak taşınacak, `worker/parser.py`'a
DEĞİL).

## Bulgu 2 — "Yakından uzağa" stratejisinin düzeltilmiş hali: SABİT İNDEKS DEĞİL, METİN ARAMA

Word'ün kendi "Tablo N.M" numaralandırması bir **field-code** (otomatik
alan). **En yeni dosyada (Ocak 2025) bu numaralandırma KAYBOLMUŞ** ("Tablo .
2025 Yılı..." — sayı boş render edilmiş), Mart 2024 ve Şubat 2023'te sağlam
("Tablo 2.6 ...", "Tablo 5.1 ..."). Yani **"yakın = daha güvenilir" varsayımı
burada TERSİNE dönüyor** — en yeni dosya, numaralandırma açısından en kırılgan
olanı.

Ayrıca dosyalar arası toplam tablo sayısı bile sabit değil (Ocak 2025: 27,
Mart 2024/Şubat 2023: 28) — bir tablonun eklenmiş/birleştirilmiş olması
muhtemel. **Sonuç: parser sabit tablo index'ine ASLA güvenmemeli** — Excel
tarafındaki `bul_capa()` ile aynı ilkeyi (başlık metnini ARA, bulduğun yerden
oku) Word tarafında da paragraf metni üzerinden uygulamak ZORUNLU. Bu,
stratejinin kendisini (yakından uzağa genişletme) GEÇERSİZ KILMIYOR — yalnız
"yakın dosya = index'e güvenilir" alt-varsayımını düzeltiyor.

## Bulgu 3 — Tablo eşleştirmesi (Mart 2024 üzerinden doğrulandı)

| Excel karşılığı | Word tablosu (gerçek başlık) | Durum |
|---|---|---|
| **T11 (fact_tuketim)** | "Tablo 2.6 ... Faturalanan Elektrik Tüketiminin İl ve Tüketici Türü Bazında Dağılımı (MWh)" — İl×[Aydınlatma/Kamu ve Özel Hizmetler Sektörü ile Diğer/Mesken/**Sanayi**/Tarımsal Faaliyetler/Genel Toplam/Pay], TEK ay, wide format, 83 satır (81 il + başlık + Genel Toplam) | **VAR, ama eksik grain** — Sanayi-DAĞITIM/Sanayi-İLETİM ayrımı YOK, tek "Sanayi" sütunu. |
| **T10 (fact_abone)** | "Tablo 5.2 ... Tüketici Sayısının İl ve Tüketici Türü Bazında Dağılımının Dönemler Arası Karşılaştırılması" — 489 satır, UZUN format (İl Adı, Tüketici Türü, [yıl-1] Miktar+Pay, [yıl] Miktar+Pay, Değişim%) | **VAR, yapısal olarak uygun** — il×grup grain'i doğru, format Excel'den farklı (dönemler-arası-karşılaştırmalı, uzun) ama tek dönemin değeri çıkarılabilir. |
| **T9 (mutabakat)** | "Tablo 2.5 ... Tüketici Sayısının Dağıtım Bölgesi Bazında..." | Farklı kırılım (21 dağıtım şirketi ünvanı, İL DEĞİL) — doğrudan mutabakat için kullanılamaz, T9'un doğrudan karşılığı yok. |
| **T13 (fact_serbest_tuketici)** | **YOK.** Tüm paragraflar "serbest" için tarandı — yalnız "serbest ÜRETİM şirketleri" (T1/T4 bağlamında, farklı kavram) geçiyor. "Serbest Tüketici" tablosu bu rapor türünde hiç bulunmuyor. | **Kaynak yok.** |
| T1/T4 (kurulu güç) | Muhtemelen var (Tablo[5]-[16] arası "Kaynak Türü"/"İLLER" başlıklı çok sayıda tablo görüldü) | **İncelenmedi** — uygulama turunun ilk adımlarından biri. |

Ek olarak Word raporu, T11'in HEM aylık (Tablo 2.6) HEM kümülatif/dönemler-
arası-karşılaştırmalı (Tablo 2.7, "Ocak-Mart 2024...") halini AYRI tablolar
olarak veriyor — Excel'deki T11 kümülatif-karışıklığı (2026-08-31'de bulunan,
bkz. `06_canli_veri_operasyon_gunlugu.md`) burada YOK, çünkü aylık versiyon
zaten doğrudan mevcut, fark almaya gerek yok.

## Bulgu 4 — `05_kaynak_dosya_sozlesmesi.md` uyarlanabilir mi?

**Hayır, tamamen yeni bir kolon haritası gerekir.** Sütun adları farklı
("Kamu ve Özel Hizmetler Sektörü ile Diğer" vs Excel formatı), Sanayi ayrımı
yok, tablo numaralandırma şeması taban tabana farklı (Excel: düz "Tablo N";
Word: hiyerarşik "Tablo N.M"). Mevcut Excel haritası REFERANS olarak
kullanılabilir (grup/kaynak eşleme mantığı — `grup_esle()`, `il_kodu_bul()`
büyük ölçüde yeniden kullanılabilir) ama kolon pozisyonları/başlıkları için
AYRI bir harita (yeni bir doküman bölümü ya da bu dosyanın devamı) gerekir.

## Karar 1 — T13 (fact_serbest_tuketici) kaynağı yok: kısmi yükleme + açık işaretleme

Word dönemlerinde T13'ün kaynağı YOK. **Karar: kısmi yükleme yapılacak** —
T11 (fact_tuketim), T10-karşılığı (fact_abone), ve varsa T1/T4 (fact_uretim)
normal şekilde yüklenecek, ama **T13 boş kalan her dönem için AÇIKÇA
işaretlenecek** (dim_tarih'e bir bayrak ya da `ingestion_batch.error_summary`
alanına "T13 kaynağı bu dönem için mevcut değil (Word formatı, aylık
raporda serbest tüketici tablosu yok)" notu — uygulama turunda kesin
mekanizma seçilecek). **Amaç:** "parser hatası yüzünden 0 satır" (bugünkü
Mart-Haziran T13 satır-kayması bulgusu gibi) ile "kaynakta gerçekten hiç yok"
durumunu KPI/dashboard seviyesinde her zaman ayırt edebilmek — bugünkü
`audit_log` disiplinini (2026-08-31, bkz. `03_veri_modeli.md` ve
`06_canli_veri_operasyon_gunlugu.md`) bozmadan.

## Karar 2 — `baglanti` (Sanayi-İletim/Dağıtım) kaynakta yok: Sanayi grubu da kapsam dışı

Word kaynağı Sanayi-DAĞITIM/Sanayi-İLETİM ayrımını (P0-2'nin `baglanti`
alanı, `fact_tuketim`'in doğal anahtarının zorunlu parçası) hiç vermiyor.
**Değerlendirilen ama REDDEDİLEN seçenek:** şemaya üçüncü bir `baglanti`
değeri eklemek (örn. `'bilinmiyor'` veya `'toplam'`) — bu hem `db/schema.sql`
CHECK kısıtını hem `worker/kpi.py`'deki P0-2 KPI hesaplarını (Sanayi-Dağıtım
+ Sanayi-İletim toplamına dayanan mantık) değiştirir, yeni bir üçüncü-durum
riski yaratır (KPI kodunun her yerinde "iki değer mi üç değer mi" varsayımı
gözden geçirilmeli).

**Karar: en basit yol seçildi** — bu dönemlerde **Sanayi grubu da T13 gibi
"kaynakta yok" kapsamına alınır, yüklenmez**. Mesken, Tarımsal, Aydınlatma,
Kamu ve Özel Hizmetler grupları normal şekilde yüklenir. Şema ve KPI kodu
DEĞİŞMEZ — mevcut iki-değerli `baglanti` modeli korunur, yalnızca Word
dönemlerinde Sanayi grubunun fact_tuketim'e hiç girmediği (Karar 1'deki
mekanizmayla) açıkça işaretlenir.

**Kapsam netliği (2026-09-01, Mart 2024 dry-run'ında netleştirildi):** Bu
dışlama **YALNIZCA `fact_tuketim`'i (T11-karşılığı) etkiler.** Gerekçe
`baglanti` alanının kendisi — `worker/ingest.py`'nin `_DOGAL_ANAHTAR`'ında
`baglanti` yalnız `fact_tuketim`'in doğal anahtarında var
(`["il_kodu","tarih_id","grup_id","baglanti"]`); `fact_abone`
(`["il_kodu","tarih_id","grup_id"]`), `fact_uretim` ve
`fact_serbest_tuketici`'nin doğal anahtarlarında `baglanti` hiç yok. Yani
**genel ilke**: Sanayi grubu, `baglanti` içermeyen HİÇBİR fact tablosunda
(bugün: `fact_abone`; ileride: T1/T4→`fact_uretim`, varsa T13-karşılığı→
`fact_serbest_tuketici`) dışlanmaz, normal yüklenir — dışlama yalnız
`fact_tuketim`'e özgüdür. Mart 2024'te T10-karşılığında (`fact_abone`)
Sanayi dahil edilerek doğrulandı: 81 il × 5 grup = 405 satır, 49.929.418
toplam abone. Bu ilke her yeni ay/tablo için yeniden sorulmayacak şekilde
buraya sabitlenmiştir.

## Kapsam Tahmini

| Kalem | Süre |
|---|---|
| Tek-seferlik aktarım script'inin ortak çekirdeği (`worker/scripts/` altında — tablo bulma yardımcı fonksiyonu, `ingest.py`/`pipeline.py` primitiflerine bağlanma) | 0,5-1 gün |
| **Her yıl için AYRI, açık eşleme tarifi** (2023, 2024, 2025 — üçü de kendi sütun/tablo haritasıyla, "genel algılama motoru" değil) | ~0,5 gün/yıl × 3 yıl ≈ 1,5 gün |
| T1/T4 (kurulu güç) desteği (her yılın kendi tarifine eklenir) | +0,5-1 gün |
| `baglanti`/T13 "kaynakta yok" işaretleme mekanizması + pipeline entegrasyonu (Karar 1 & 2) | +0,5-1 gün |
| Testler — **2023/2024/2025 AYRI AYRI**, tek seferde değil | +1 gün |
| Dokümantasyon (yıl bazlı kolon haritaları) | +0,5 gün |
| **Toplam** | **3-5 gün** (T13 tam kapsam dışı, T1/T4 dahil) |

Not: "yıl bazlı ayrı tarif" yaklaşımı toplam süreyi tek bir genel motor
yazmaya göre azaltmayabilir (üç tarif yazmak, bir motor yazmaktan az farklı
sürebilir) — ama **riski** azaltır: her tarif yalnızca KENDİ yılının
gerçek verisine karşı doğrulanır ve bir daha DOKUNULMAZ, "gelecekte
bilinmeyen bir format kırar mı" endişesi taşımaz.

**Neden yıl yıl test, tek seferde değil:** Ocak 2025'in numaralandırma kaybı
bile TEK BAŞINA bir format varyasyonu; 2023-2025 arası herhangi bir yılda
(hatta ayda) benzer sürprizler beklenmeli — Excel tarafında Mart 2026'da
EPDK'nın kendi şablonunu değiştirmesiyle yaşanan T11/T13 sürprizleri
(2026-08-31, bkz. `06_canli_veri_operasyon_gunlugu.md`) aynı riskin Word
tarafında da geçerli olduğunu gösteriyor.

## 2024 tarifi UYGULANDI ve gerçek Supabase'e yüklendi (2026-09-01)

Bkz. `06_canli_veri_operasyon_gunlugu.md` ("2026-09-01 — Word (.docx) 2024
tarihsel aktarımı") — tam sonuç, bulunan/düzeltilen idempotency bug'ı, ve
per-ay red/aktivasyon tablosu orada. Özet: `worker/scripts/word_ortak.py`
(ortak çekirdek) + `worker/scripts/word_2024.py` (2024 tarifi) yazıldı,
`python-docx` `requirements.txt`'ye eklendi, Karar 2 netleştirildi (Sanayi
dışlaması yalnız `fact_tuketim`'e özgü). 12/12 ay yüklendi — 9'u aktive
edildi, 3'ü (Ocak/Mart/Nisan, her biri gerçek kaynak verisinde 1'er
açıklanabilir negatif "Tarımsal" değeri yüzünden) elle onay bekliyor.

**Bu turda kapsam dışı kalanlar (Karar 1 gereği, henüz yapılmadı):**
T13-karşılığı (fact_serbest_tuketici — Word'de zaten kaynağı yok, Karar 1'in
"açık işaretleme" mekanizması henüz somutlaştırılmadı) ve T1/T4-karşılığı
(fact_uretim — Word tarafı hiç incelenmedi).

## Yarından devam

1. ~~Ocak/Mart/Nisan 2024'ün 3 bekleyen batch'i için karar ver~~ **YAPILDI
   (2026-09-01 kapanışı)** — üçü de elle onaylandı/aktive edildi, 2024'ün
   12 ayı tamamen aktif ve tutarlı. Detay: `06_canli_veri_operasyon_
   gunlugu.md` ("2026-09-01 (kapanış)").
2. **2023 için ayrı bir tarif yaz** (`worker/scripts/word_2023.py`,
   `word_ortak.py` çekirdeğini kullanarak — 2024'ün desenini birebir
   kopyalama, kendi başlık/sütun farklarını doğrula).
3. **Sonra 2025** — 12 dosyası bu turda `word_2024.py`'nin manifest
   taramasında YAN ÜRÜN olarak zaten bulundu (bkz. o dosyanın modül notu)
   ama hiç işlenmedi.
4. T1/T4 (kurulu güç) tablolarının Word karşılığını incele (hiç yapılmadı).
5. Karar 1'in somut DB/kod mekanizmasını tasarla ve uygula (T13'ün Word
   dönemlerinde "kaynakta yok" olduğunu dim_tarih bayrağı mı,
   `ingestion_batch.error_summary` notu mu ile işaretleyeceğine karar ver).
6. `word_2024.py`'nin regresyon testlerini yaz (şu an yalnız script-içi
   assertion'lara — 81 il, beklenen satır sayısı — güveniliyor, dedike
   pytest testi yok) — 2023 tarifine başlamadan önce ya da onunla birlikte.
7. Yıl bazlı kolon haritalarını `05_kaynak_dosya_sozlesmesi.md`'ye ek bir
   bölüm olarak ya da bu dosyanın devamı olarak yaz.
