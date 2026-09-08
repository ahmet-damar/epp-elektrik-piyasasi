# EPP — KPI Sözleşmeleri (Faz 0)

> **STATUS: ACTIVE (sözleşme)** — KPI formüllerini/kenar durumlarını tutar;
> güncel hesaplanabilirlik durumu için `09_PROJE_DURUMU.md` ve
> `10_TEKNIK_MASTER_DOKUMAN.md` §7/§11.2'ye bakın (2026-09-07 denetimi).

Kaynak: Ek B. Her KPI: formül + grain + kenar durum. Faz 0 production KPI'ları.

## Ortak Kurallar
- Yalnız `is_active=true` kayıtlar üzerinden hesaplanır.
- Sıfıra bölme: payda 0/NULL ise sonuç NULL + uyarı.
- Yuvarlama: oranlar 1 ondalık (%); kabul toleransı ±%0,5.
- Baz sıcaklıklar `sistem_parametre`'den okunur (koda gömme).

## Üretim & Kapasite
| KPI | Formül | Kenar durum |
|-----|--------|-------------|
| KPI-01 Toplam kurulu güç (MW) | Σ kurulu_guc_mw | yoksa 0 |
| KPI-02 Toplam üretim (MWh) | Σ uretim_mwh (lisanslı) | yoksa 0 |
| KPI-03 Yenilenebilir pay (%) | Σ uretim(yen) / Σ uretim ×100 | payda 0→NULL |
| KPI-04 Kaynak payı (%) | Σ uretim(kaynak)/Σ uretim ×100 | payda 0→NULL |
| KPI-05 Kapasite faktörü (%) | uretim/(kurulu×saat)×100 | kurulu 0→NULL |
| KPI-06 HHI | Σ pay² ; pay=kaynak/toplam ; **ölçek 0–1** | payda 0→NULL |
| KPI-07 Lisanssız pay (%) | Σ uretim(lisanssız)/Σ uretim ×100 | payda 0→NULL |

## Tüketim
| KPI | Formül | Kenar durum |
|-----|--------|-------------|
| KPI-08 Toplam tüketim (MWh) | Σ tuketim_mwh (tüm baglanti) | yoksa 0 |
| KPI-09 Grup payı (%) | Σ tuketim(grup)/Σ tuketim ×100 | payda 0→NULL |
| KPI-10 Abone başı tüketim (MWh) | Σ tuketim/Σ abone | abone 0→NULL |
| KPI-13 YoY (%) | (t − t_12ay_önce)/t_12ay ×100 | geçen yıl yoksa VEYA grup kümesi uyuşmuyorsa 'hesaplanamaz' (aşağıya bkz.) |

**Kaynak (2026-09-08, Aşama 3/ADIM 2'de `fact_tuketim_ulke_geneli`'ye
taşındı):** `t`/`t_12ay_önce` artık **ülke geneli, il kırılımsız**
`fact_tuketim_ulke_geneli`'den geliyor (bkz. worker/analytics.py
`ulke_geneli_tuketim_getir`) — KPI-08/09/10 (yukarıdaki satırlar) hâlâ
İL BAZLI `fact_tuketim`'i kullanıyor, KPI-13 İLE KARIŞTIRILMASIN.

**KPI-13'ün grup-kümesi kısıtı (2026-09-03, KPI-25/26 ile AYNI kök nedene AYNI disiplin):**
`t` ve `t_12ay_önce`'nin GRUP KÜMESİ (örn. Sanayi'nin biri içerip diğerinin
içermemesi) birebir aynı DEĞİLSE YoY hesaplanmaz, None ('hesaplanamaz')
döner — bkz. worker/kpi.py `kpi_13_yoy`. Kanıt (o zamanki il bazlı
kaynakla): 2025-06 (Word, Sanayi kaynakta yok, Karar 2) ile 2026-06
(Excel, Sanayi var) karşılaştırması eskiden %+70,9 gibi sahte bir YoY
üretiyordu; Sanayi her iki taraftan da çıkarılınca gerçek artış %+2,2
çıkıyordu. Kaynak `fact_tuketim_ulke_geneli`'ye taşındıktan SONRA bu
belirli çift (2025-06/2026-06) artık grup kümesi uyuşuyor (ikisinde de
Sanayi var) ve gerçek bir değer üretiyor — güncel değer için
`09_PROJE_DURUMU.md`'ye bakın. Koruma KOD'dan kaldırılmadı — yalnız
FARKLI bir sınırda (örn. 2016-12 Tarımsal'ın eksik olduğu ay
karşılaştırmaları) hâlâ devrede kalabilir. Bu, KPI-25/26'nın "kapsamı
uyuşmayan yılı seriye hiç katma" stratejisinin KPI-13'e (tek bir
dönem-karşılaştırması, yıllık seri değil) uyarlanmış hâli — aynı
"sahte değer üretmeme" ilkesi (bkz. worker/kpi.py modül notu).

## Hava Türetimleri (Faz 0)
| KPI | Formül |
|-----|--------|
| KPI-23 HDD | Σ_gün max(0, 18 − t_gün) ; aylık toplam |
| KPI-24 CDD | Σ_gün max(0, t_gün − 22) ; aylık toplam |

## Hava Normalizasyonu (Faz 3'te production, 2026-08-30)
- **KPI-11** arındırılmış tüketim = gerçek − β·(HDD−HDD_norm) − γ·(CDD−CDD_norm)
  - β/γ: geçmiş (tuketim_mwh, hdd, cdd) gözlemleri üzerinde OLS (min 12 ay);
    yetersizse 'hesaplanamaz' — bkz. worker/kpi.py `beta_gamma_tahmin_et`.
  - HDD_norm/CDD_norm: aynı ay için son 10 yılın SABİT ortalaması (OD-2) —
    `hava_normu_hesapla`.
- **KPI-12** norm sapması = (arındırılmış − tüketim_norm)/tüketim_norm ×100
  - tüketim_norm = son 5 yıl aynı-ay ARINDIRILMIŞ tüketim ort., ROLLING (OD-2)
    — `tuketim_normu_hesapla`.
- Faz 0 çıktısı HDD/CDD kolonları + regresyona hazır veriydi (β/γ YOK); Faz 3
  worker/kpi.py + worker/analytics.py `kpi_11_12_hesapla()` ile production'a
  alındı. Yeterli geçmiş veri yoksa (regresyon/normlardan HERHANGİ biri)
  sahte değer ÜRETİLMEZ, ilgili alanlar None ('hesaplanamaz') kalır.

## CAGR (Yıllık — n = son_yıl − ilk_yıl)
Kaynak: EPP_SRS_Teknik-Gereksinim_v1.5.docx Tablo 26 (Ek B'de bu ikisi hiç
tanımlı değildi — Downloads/1/ altındaki kaynak .docx dosyaları taranarak
2026-08-30'da doğrulandı, bkz. ADR notu worker/kpi.py `kpi_cagr` docstring'i).
Jenerik formül: (son/ilk)^(1/n) − 1 ; **n = yıl farkı** (2021→2025 ⇒ n=4,
"gözlem−1" ile aynı YALNIZCA yıllar ardışıksa).
- **KPI-25** CAGR — tüketim (%), RESMİ "toplam tüketim" tanımı: ilk/son =
  yıl bazında toplam tuketim_mwh, **YALNIZ `fact_tuketim_ulke_geneli`**'nden
  (aylar TOPLANIR, akış/flow metriği; bkz. worker/analytics.py
  `yillik_tuketim_serisi_getir`) — il bazlı `fact_tuketim` ile ASLA
  KARIŞTIRILMAZ (grain karışımı riski).
  **Kaynak kararı (2026-09-08, Aşama 2/C5):** Önceden (2026-09-03'ten bu
  yana) bu KPI il bazlı `fact_tuketim`'i, "yalnız Sanayi grubunu İÇEREN
  yıllar" filtresiyle okuyordu — Sanayi Word (.docx) kaynaklı 2016-2025
  dönemlerinde `fact_tuketim`'e hiç girmediğinden (Karar 2) bu filtre
  pratikte yalnız 2026'yı bırakıyor, KPI-25 sürekli 'hesaplanamaz'
  dönüyordu. `fact_tuketim_ulke_geneli` (2026-09-05/08'de eklendi) artık
  2016-2025'in TAMAMI için Sanayi DAHİL ülke geneli veri sağladığından
  KPI-25 TAMAMEN bu tabloya taşındı, eski "Sanayi'yi içeren yıllar"
  filtresi KALDIRILDI (artık gereksiz — Sanayi zaten her yılda var).
  **Yeni şart — tam yıl VE 5/5 grup:** bir yıl yalnız TÜM 12 ayı VE her
  ayda TÜM 5 tüketici grubu mevcutsa (60/60 satır) seriye girer. Bu,
  **2016'yı otomatik ve KASITLI olarak dışarıda bırakır** — 2016-12
  Tarımsal, ülke seviyesinde de negatif çıktığı için hiç yüklenmedi
  (59/60 satır, bkz. §11.3 master doküman), bu KASITLI bir kapsam
  sınırlaması, bir hata DEĞİL (altı ay sonra "2016 neden yok" diye
  yeniden araştırılmasın diye burada açıkça not düşülüyor). Güncel
  hesaplanan değer için `09_PROJE_DURUMU.md`'ye bakın (sayılar burada
  tutulmuyor, her turda eskir). Sanayi'yi TAMAMEN dışlayan, KPI-25'in
  YERİNE GEÇMEYEN ayrı bir metrik için bkz. **KPI-27**.
- **KPI-27** CAGR — Sanayi-hariç tüketim (%): ilk/son = yıl bazında toplam
  tuketim_mwh, **İL BAZLI `fact_tuketim`**'den (KPI-25'in taşınmasından
  ETKİLENMEDİ, kaynağı DEĞİŞMEDİ), Sanayi grubu **TÜM yıllardan** açıkça
  ÇIKARILARAK hesaplanır (bkz. worker/analytics.py
  `yillik_tuketim_sanayi_haric_serisi_getir`). Yalnız **TAM yıllar** (12
  farklı ay) dahil edilir — kısmi bir yılı tam yıllarla karşılaştırmak
  distorsiyon üretir. **KPI-25'İN YERİNE GEÇMEZ** — resmi "toplam
  tüketim" tanımını KARŞILAMAZ (Sanayi hariç tutulduğu için), yalnız ek
  bağlam/gözlem amaçlı ayrı bir metriktir.
- **KPI-26** CAGR — yenilenebilir kurulu güç (%): ilk/son = yıl bazında
  Σ kurulu_guc_mw WHERE `dim_kaynak.yenilenebilir_mi=true` — **üretim
  DEĞİL**, yalnız kurulu güç; kurulu güç bir STOK metriğidir, aylar
  TOPLANMAZ, yılın en güncel ayı alınır (bkz. worker/analytics.py
  `yillik_yenilenebilir_kurulu_guc_serisi_getir`).
  **2026-09-02'de eklenen kısıt:** yalnız Lisanslı verisi OLAN yıllar
  seriye girer — Word (.docx) kaynaklı 2023-2025 dönemlerinde T1
  (Lisanslı kurulu güç) hiç yok (kaynakta yok, dokumanlar/
  07_word_parser_kapsam.md Bulgu 5 + Karar 3), yalnız T4 (Lisanssız,
  yenilenebilir kapasitenin küçük bir kesri) yüklendi — filtre olmasaydı
  bu yıllar 2026 (Excel, Lisanslı+Lisanssız TAM) ile karışıp sahte bir
  CAGR üretirdi (KPI-25'in Sanayi dahil/hariç sorunuyla AYNI kök neden).
  Lisanslı'sı olmayan yıl "veri yok" sayılır (None/"hesaplanamaz"), sahte
  bir sayı ÜRETİLMEZ.
