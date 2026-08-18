# EPP — Kaynak Dosya Sözleşmesi (Parser)

Kaynak: Ek F. EPDK dosyalarının parser için kolon/tablo haritası.
NOT: v0.1 — Faz 0'da gerçek 2016+ dosyalarla doğrulanacak.

## Çapa (Anchor) Tabanlı Okuma
Parser SABİT hücreye güvenmez; değişmez etiketleri arar:
- Tablo: 'Tablo 1', 'Tablo 7 - Faturalanan', 'Tablo 13'
- Sütun: 'İLLER', 'Kaynak Türü', 'Tüketici Grubu', 'Miktar', 'Sayı'
- Satır: 'TÜRKİYE', 'Genel Toplam', 'TOPLAM'
- Normalizasyon: trim + BÜYÜK harf + Türkçe sadeleştir (İ→I)

## Aylık Ek (xlsx) — 13 Tablo
| Tablo | İçerik | Hedef |
|-------|--------|-------|
| T1 | Lisanslı kurulu güç (il×kaynak) | fact_uretim |
| T2/T3 | Lisanslı üretim (kaynak/il) | fact_uretim |
| T4/T5/T6 | Lisanssız kurulu güç/üretim | fact_uretim |
| T7 | Faturalanan tüketim (tür) | fact_tuketim |
| T8 | Faturalanan tüketim (il) | fact_tuketim |
| T9/T10 | Tüketici sayısı | fact_abone |
| **T11** | **Tüketim (iletim/dağıtım!)** | **fact_tuketim.baglanti** |
| T12 | Tüketim (dağıtım bölgesi) | fact_tuketim |
| T13 | Serbest tüketici | fact_serbest_tuketici |

**P0-2 KRİTİK:** Tablo 11, 'Sanayi-İLETİM' ve 'Sanayi-DAĞITIM' sütunlarını
içeren TEK tablodur → fact_tuketim.baglanti'yi besler. Diğer tüketim
tablolarında baglanti='dagitim' varsayılır; iletim yalnız T11'den gelir.

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
