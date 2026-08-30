# EPP — KPI Sözleşmeleri (Faz 0)

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
| KPI-13 YoY (%) | (t − t_12ay_önce)/t_12ay ×100 | geçen yıl yoksa 'hesaplanamaz' |

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
- **KPI-25** CAGR — tüketim (%): ilk/son = yıl bazında toplam tuketim_mwh
  (aylar TOPLANIR, akış/flow metriği).
- **KPI-26** CAGR — yenilenebilir kurulu güç (%): ilk/son = yıl bazında
  Σ kurulu_guc_mw WHERE `dim_kaynak.yenilenebilir_mi=true` — **üretim
  DEĞİL**, yalnız kurulu güç; kurulu güç bir STOK metriğidir, aylar
  TOPLANMAZ, yılın en güncel ayı alınır (bkz. worker/analytics.py
  `yillik_yenilenebilir_kurulu_guc_serisi_getir`).
