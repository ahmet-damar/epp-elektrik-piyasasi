# EPP — Kaynak Dosya Sözleşmesi (Parser)

> **STATUS: ACTIVE (sözleşme)** — kolon/tablo haritasını tutar; değişen
> durum bilgisi için `09_PROJE_DURUMU.md`/`10_TEKNIK_MASTER_DOKUMAN.md`'ye
> bakın (2026-09-07 denetimi).

Kaynak: Ek F. EPDK dosyalarının parser için kolon/tablo haritası.
NOT: v0.1 — Faz 0'da gerçek 2016+ dosyalarla doğrulanacak.

## Çapa (Anchor) Tabanlı Okuma
Parser SABİT hücreye güvenmez; değişmez etiketleri arar:
- Tablo: 'Tablo 1', 'Tablo 7 - Faturalanan', 'Tablo 13'
- Sütun: 'İLLER', 'Kaynak Türü', 'Tüketici Grubu', 'Miktar', 'Sayı'
- Satır: 'TÜRKİYE', 'Genel Toplam', 'TOPLAM'
- Normalizasyon: trim + BÜYÜK harf + Türkçe sadeleştir (İ→I)

## Aylık Ek (xlsx) — 13 Tablo

**Durum kolonu (2026-09-07, `worker/parser.py`/`worker/pipeline.py`'ye karşı
doğrulandı; bkz. A1 düzeltmesi):** "Hedef" tek başına yanıltıcıdır — bazı
tablolar bir fact tablosuyla aynı grain'i paylaşsa da GERÇEKTEN parse
edilmez (kaynakta o kesişim yok ya da başka bir tabloyla redundant). Yazan
tablo sayısı tam **5**'tir: T1/T4/T10/T11/T13.

| Tablo | İçerik | Hedef | Durum |
|-------|--------|-------|-------|
| T1 | Lisanslı kurulu güç (il×kaynak) | fact_uretim | Parse edilir, **YAZAR** |
| T2/T3 | Lisanslı üretim (kaynak/il) | fact_uretim | Parse edilmez — il×kaynak kesişimi kaynakta yok |
| T4 | Lisanssız kurulu güç | fact_uretim | Parse edilir, **YAZAR** |
| T5/T6 | Lisanssız üretim (kaynak/il) | fact_uretim | Parse edilmez — T2/T3 ile aynı sebep |
| T7 | Faturalanan tüketim (tür, ülke geneli) | fact_tuketim | Parse edilir ama **YAZMAZ** — yalnız mutabakat |
| T8 | Faturalanan tüketim (il) | fact_tuketim | **Parse edilmez — T11 ile redundant** (bkz. T12 notu) |
| T9 | Tüketici sayısı (tür, ülke geneli) | fact_abone | Parse edilir ama **YAZMAZ** — yalnız mutabakat |
| T10 | Tüketici sayısı (il) | fact_abone | Parse edilir, **YAZAR** |
| **T11** | **Tüketim (iletim/dağıtım!)** | **fact_tuketim.baglanti** | Parse edilir, **YAZAR** (+ kendi Genel Toplam satırı → `fact_tuketim_ulke_geneli`) |
| T12 | Tüketim (dağıtım şirketi) | parse edilmiyor | **Parse edilmez — T11 ile redundant** (bkz. not) |
| T13 | Serbest tüketici (il×tur×grup) | fact_serbest_tuketici | Parse edilir, **YAZAR** — bkz. not

**P0-2 KRİTİK:** Tablo 11, 'Sanayi-İLETİM' ve 'Sanayi-DAĞITIM' sütunlarını
içeren TEK tablodur → fact_tuketim.baglanti'yi besler. Diğer tüketim
tablolarında baglanti='dagitim' varsayılır; iletim yalnız T11'den gelir.

**T8 NOTU (2026-09-07, `worker/parser.py` satır 17-24'e karşı doğrulandı —
bkz. A1 düzeltmesi):** T8, T11 ile birebir aynı il×tüketici-grubu verisini
tekrarlıyor (T11 ayrıca Sanayi'yi iletim/dağıtım olarak ayırıyor, T8
ayırmıyor) → T8 hiçbir yeni bilgi taşımıyor, bu yüzden implemente edilmedi.
**Bu, T12 ile birebir aynı gerekçe** — ikisi de "T11 ile redundant" sınıfına
girer. (Daha önce `10_TEKNIK_MASTER_DOKUMAN.md`'de bu not yanlışlıkla "T8
aslında parse ediliyor" şeklinde 'düzeltilmişti' — o kayıt geri alındı,
bkz. o dokümanın §14 Çelişki Kayıtları.)

**T12 NOTU (2026-08-30, gerçek dosyayla doğrulandı):** Doküman başlığı
"dağıtım bölgesi" diyor ama gerçek kolon adı 'Lisans Unvanı' — grain aslında
**dağıtım şirketi** (21 şirket + ulusal 'İLETİMDEN BAĞLI TÜKETİCİLER
(TÜRKİYE)' satırı, yalnız Sanayi). T12'nin 'Genel Toplam' ve
iletim/Sanayi rakamları T7/T11 ile birebir eşleşiyor → **T11 ile redundant,
hiçbir yeni bilgi taşımıyor.** Bu yüzden parser'da implemente edilmedi
(worker/parser.py). İleride dağıtım şirketi bazlı bir KPI gerekirse (ör.
DSO karşılaştırması), T12'yi parse etmeye gerek yok: statik bir
dim_il → dagitim_sirketi eşleme tablosuyla T11'in il bazlı verisinden
türetilebilir — bilgi kaybı yok.

**T13 NOTU (2026-08-30, gerçek dosyayla doğrulandı, worker/parser.py
`tablo13_serbest_tuketici_oku`):** Grain dokümanın ima ettiğinden farklı —
her (il, tur) AYRICA 5 tüketici grubuna bölünmüş (bkz. migration
20260819_0006). Gerçek 'tur' değerleri 'Lisanslı'/'Lisanssız' DEĞİL:
'Serbest Tüketici', 'ST Olma Hakkı Bulunmayan Aboneler', 'ST Olma Hakkını
Kullanmayan Aboneler'. Yerleşim iki paralel bloktur: 'Tüketim
Miktarı(MWh)' başlığı altında 5 grup sütunu, hemen ardından aynı 5 grup adı
'Tüketici Sayısı' başlığı altında tekrar. İl adı yalnız o ilin ilk
satırında yazılı (ileri doldurma); her ilin sonunda atlanan bir 'İl Toplam'
satırı var. Toplam tuketim_mwh T7/T11/T12 ile, toplam tuketici_sayisi
T9/T10 ile birebir eşleşiyor (çapraz doğrulandı).

## Tüketici Grubu Eşleme
| Kaynak etiket | grup_adi | grup_id |
|---------------|----------|---------|
| Mesken | Mesken | 1 |
| Sanayi / Sanayi-DAĞITIM / Sanayi-İLETİM | Sanayi | 2 |
| Tarımsal Faaliyetler | Tarımsal | 3 |
| Aydınlatma | Aydınlatma | 4 |
| Kamu ve Özel Hizmetler | Kamu ve Özel Hizmetler | 5 |
**NOT:** Sanayi'nin İLETİM/DAĞITIM kırılımı grup DEĞİL, baglanti alanıdır.

## Kaynak Türü Eşleme
| Kaynak etiket | Normalize | Yenilenebilir |
|---------------|-----------|---------------|
| Akarsu/Barajlı/Hidrolik | Hidrolik | Evet |
| Rüzgar | Rüzgar | Evet |
| Güneş | Güneş | Evet |
| Jeotermal | Jeotermal | Evet |
| Biyokütle | Biyokütle | Evet |
| Doğal Gaz/LNG | Doğal Gaz | Hayır |
| İthal Kömür | İthal Kömür | Hayır |
| Linyit | Linyit | Hayır |
| Taş Kömürü | Taş Kömürü | Hayır |
| Asfaltit | Asfaltit | Hayır |
| Fuel Oil | Fuel Oil | Hayır |
| Motorin | Motorin | Hayır |
| Nafta | Nafta | Hayır |

**NOT (2026-08-30, gerçek dosyayla doğrulandı):** Motorin ve Nafta, parser'ın
(`worker/parser.py` KAYNAK_ESLEME) zaten tanıdığı ama `dim_kaynak` seed'inde
(migration 20260819_0004) unutulmuş iki kaynaktı — gerçek 2026 Ocak dosyasının
T1'inde (kurulu güç) her ikisi de sütun olarak mevcut. Migration
20260819_0007 ile eklendi.

## Birim / Tip Kuralları
- Kurulu güç: MWe, numeric(14,3), ≥0
- Üretim/tüketim: MWh, numeric(16,3), ≥0
- Abone: integer, ≥0
- Sayı formatı: nokta binlik, virgül ondalık ('1.432,404') → temizle
- Boş hücre = NULL (0 değil)

## Yıllık Rapor (FR-15)
- tarih_id = yil*100 (202500); ay=0; donem_tipi='yillik'
- Yıllık toplamda otoriter (OD-4); aylık ile sapma → KPI-28 uyarısı

## Doğrulama
- 13 tablo mevcut mu; eksikse batch reddi
- İl toplamı ↔ 'TÜRKİYE' ±%0,5
- İl adları ≥%99 dim_il'e eşlenmeli; eşleşmeyen karantina
- Negatif değer → reddet; bilinmeyen grup/kaynak → karantina + uyarı

**Word yılları — üretim (T2/T3/T5/T6 eşdeğeri) kararları (2026-09-09,
Aşama 3/ADIM 3, `dokumanlar/12_word_uretim_envanteri.md`'deki araştırmaya
dayanır):**
- **Karar (Bulgu C):** Word kaynağında Lisanssız üretim için gerçek bir
  il×kaynak JOINT tablo VAR (2016-2023 doğrulandı, Excel'de YOK) —
  **BİLİNÇLİ OLARAK KULLANILMIYOR**. Gerekçe: 2016-2023 (zengin, il×kaynak)
  ile 2024+ (yalnız marjinal) arasında tanım/grain farkı, Word-Excel
  sınırında davranış değiştiren bir KPI üretir — projenin "tek seride tek
  tanım" ilkesine (bkz. §5.5 T7/T11 dikişi kararı) aykırı. `fact_uretim.
  uretim_mwh` da bu yüzden Word yılları için AYRICA doldurulmuyor (aynı
  sınır sorunu — 2016-2023 dolu/2024+ NULL bir kolon kırılganlık yaratır).
  **İleride il×kaynak kırılımlı bir üretim KPI'sı tanımlanırsa bu bulgu
  yeniden değerlendirilebilir** — bkz. envanterdeki tam detay.
- **Karar (Bulgu D):** 2016-2017 Lisanssız üretim **KAPSAM DIŞI** —
  Excel'in "Brüt Lisanssız Üretim Miktarı" tanımıyla eşleşen bir kaynak bu
  iki yılda YOK (yalnız dar bir "İhtiyaç fazlası satın alınan enerji
  miktarı" alt-kümesi var, 2018'den itibaren Brüt kolonu VAR). `veri_
  kapsam_disi`'ye migration `20260909_0002` ile genişletilen whitelist
  üzerinden 48 satır eklendi (`fact_uretim_kaynak_geneli`/`fact_uretim_
  il_geneli` × 2016-01..2017-12, `nitelik='lisans_durumu=Lisanssız'`,
  `karar_referansi='Karar 4 (2026-09-09, Bulgu D)'`) — canlıda uygulandı.
  Lisanslı üretim ETKİLENMEZ.

**Faz 0 orkestrasyon notu (2026-08-30, worker/pipeline.py):** Yukarıdaki kural
tam 13 tabloyu ima ediyor, ancak fact tablosuna gerçekten YAZAN yalnız 5
tablo var (T1/T4/T10/T11/T13 — bkz. yukarıdaki Hedef sütunu; T8/T12
redundant, T2/T3/T5/T6'da il×kaynak kesişimi hiç yok). `epdk_aylik_isle()`
bu yüzden yalnız bu 5'ini ZORUNLU sayıp eksikse batch'i reddediyor; T7/T9
eksikse yalnız mutabakat kontrolü atlanıyor (batch reddedilmiyor), T2/T3/T5/
T6/T8/T12'nin varlığı hiç aranmıyor. "İl toplamı ↔ TÜRKİYE ±%0,5" kuralı da
sert red değil — uyuşmazlık `IslemSonucu.mutabakat`'a düşer, batch_onayla()
öncesi insan/gelecekteki UI incelemesine bırakılır.

**Gerçek veri notu (2026-08-31, EPDK Ocak 2026 ilk canlı yükleme):** EPDK
raporları zaman zaman retroaktif negatif düzeltme kalemleri içerebiliyor —
bu ayki örnek: Batman/Tarımsal, T11'de tek satır (−471,934 MWh) ve T13'te
aynı toplamı oluşturan iki satıra bölünmüş (−45,081 + −426,853 MWh); ayrıca
Tekirdağ/Sanayi (−172,630) ve Yozgat/Sanayi (−3,791) T13'te. Bunlar parser
hatası DEĞİL — resmi dosyada böyle yayınlanmış, ülke geneli toplamlar
(T7/T9 mutabakatı) bu değerleri zaten içeriyor. Yukarıdaki "Negatif değer →
reddet" kuralı BİLİNÇLİ OLARAK bunları da reddediyor (gerçek veri hatasına
karşı sıfır tolerans tercih edildi) — bu yüzden `otomatik_onaya_uygun()`
her seferinde bu tür satırlar için elle inceleme/onay isteyecek. Kural
DEĞİŞTİRİLMEDİ; bu, "neden yine red var" sorusuna gelecekte hazır cevap
olsun diye düşülmüş bir not.
