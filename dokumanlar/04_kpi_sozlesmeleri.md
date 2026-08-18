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

## Faz 3'e ERTELENEN (Faz 0'da yalnız altyapı)
- **KPI-11** arındırılmış tüketim = gerçek − β·(HDD−HDD_norm) − γ·(CDD−CDD_norm)
- **KPI-12** norm sapması = (arındırılmış − tüketim_norm)/tüketim_norm ×100
  - tüketim_norm = son 5 yıl aynı-ay ARINDIRILMIŞ tüketim ort. (OD-2)
- Faz 0 çıktısı: HDD/CDD kolonları + regresyona hazır veri (β/γ YOK)

## CAGR (Yıllık — n=yıl farkı)
- KPI-25/26: (son/ilk)^(1/n) − 1 ; **n = gözlem − 1** (2021→2025 ⇒ n=4)
