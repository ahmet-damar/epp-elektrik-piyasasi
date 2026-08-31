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

## Bulgu 1 — Tablo yapısı Excel'den kökten farklı

Excel'de her "Tablo N" ayrı bir çalışma sayfası; Word'de **27-28 tablo, TEK
`document.xml` içinde**, sırayla paragraf başlıklarıyla ayrılmış. python-docx
resmi API'si (`document.tables`) paragraf↔tablo sırasını VERMİYOR — hangi
paragrafın hangi tablonun başlığı olduğunu bulmak için `document.element.
body.iterchildren()` ile XML seviyesinde manuel gezinme gerekti (paragraf ve
tablo elemanlarını orijinal doküman sırasında karışık dolaşan bir yardımcı
fonksiyon yazıldı, teşhis sırasında doğrulandı — uygulama turunda `worker/`
içine taşınacak).

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

## Kapsam Tahmini

| Kalem | Süre |
|---|---|
| Docx parser çekirdeği (tablo bulma — metin arama, T11/T10 sütun eşleme, il normalizasyonu — mevcut `il_kodu_bul()`/`grup_esle()` büyük ölçüde yeniden kullanılabilir) | 1-2 gün |
| T1/T4 (kurulu güç) desteği | +0,5-1 gün |
| `baglanti`/T13 "kaynakta yok" işaretleme mekanizması + pipeline entegrasyonu (Karar 1 & 2) | +0,5-1 gün |
| Testler — **2023/2024/2025 AYRI AYRI**, tek seferde değil | +1 gün |
| Dokümantasyon (yeni kolon haritası) | +0,5 gün |
| **Toplam** | **3-5 gün** (T13 tam kapsam dışı, T1/T4 dahil) |

**Neden yıl yıl test, tek seferde değil:** Ocak 2025'in numaralandırma kaybı
bile TEK BAŞINA bir format varyasyonu; 2023-2025 arası herhangi bir yılda
(hatta ayda) benzer sürprizler beklenmeli — Excel tarafında Mart 2026'da
EPDK'nın kendi şablonunu değiştirmesiyle yaşanan T11/T13 sürprizleri
(2026-08-31, bkz. `06_canli_veri_operasyon_gunlugu.md`) aynı riskin Word
tarafında da geçerli olduğunu gösteriyor.

## Yarından devam — uygulama turu başlangıç noktası

1. `requirements.txt`'ye `python-docx` ekle (kurulu ama deklare edilmemiş).
2. T1/T4 (kurulu güç) tablolarının Word karşılığını incele (bu turda
   yapılmadı).
3. Docx parser çekirdeğini yaz (metin-arama tabanlı tablo bulma —
   `document.element.body.iterchildren()` + başlık paragrafı eşleştirme).
4. Karar 1 & 2'nin somut DB/kod mekanizmasını tasarla ve uygula (dim_tarih
   bayrağı mı, `ingestion_batch.error_summary` notu mu — karar ver).
5. Yeni kolon haritasını `05_kaynak_dosya_sozlesmesi.md`'ye ek bir bölüm
   olarak ya da bu dosyanın devamı olarak yaz.
6. 2023, 2024, 2025 için AYRI AYRI regresyon testi.
