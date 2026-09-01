# EPP — Proje Dokümanları (Copilot Okunabilir)

Bu klasör, EPDK Elektrik Piyasası Platformu (EPP) projesinin teknik
dokümanlarının **Markdown** versiyonlarını içerir. Amaç: GitHub Copilot'un
kod üretirken bu dosyaları bağlam (context) olarak okuyabilmesi.

> Word (.docx) sürümleri insan okuması içindir; Copilot Markdown'ı daha iyi
> okur/indeksler. Kod üretiminde ESAS ALINACAK kaynak bu Markdown dosyalarıdır.

## Dosya Dizini

| Dosya | İçerik | Kaynak (docx) |
|-------|--------|---------------|
| `01_kavramsal_tasarim.md` | Proje amacı, mimari, veri akışı | SRS Böl. 1-4 |
| `02_srs_ozet.md` | Teknik gereksinim özeti + P0 kuralları | SRS v1.5 |
| `03_veri_modeli.md` | Tablolar, DDL, ilişkiler (yıldız şema) | SRS Böl. 5 / Ek C |
| `04_kpi_sozlesmeleri.md` | KPI formülleri + kenar durumlar | Ek B |
| `05_kaynak_dosya_sozlesmesi.md` | EPDK dosya kolon haritası (parser) | Ek F |
| `06_adr_dashboard_teknoloji.md` | ADR: sunum katmanı Streamlit (Faz 2), Next.js ertelendi | — (2026-08-30) |
| `06_canli_veri_operasyon_gunlugu.md` | Canlı Supabase'de yapılan elle müdahalelerin kaydı | — (2026-08-31) |
| `07_word_parser_kapsam.md` | Word (.docx) EPDK raporları — teşhis + kapsam kararları; T11/T10/T4 36 ay TAM aktif (T4 batch 53-88 aktive edildi). T13 (Karar 1) + T1 (Karar 3) kapsam dışı — artık `veri_kapsam_disi` tablosuyla açıkça işaretli (72 satır). KPI-26 ve KPI-25 düzeltildi, yeni KPI-27 (Sanayi-hariç tüketim CAGR) eklendi | — (2026-09-03) |
| `08_word_2016_2022_kapsam.md` | Word (.docx) EPDK raporları 2016-2022 — teşhis (kod YOK). 12/12 ay her yıl bulundu. T1/T13 kapsam dışı kararları (07'deki) burada da GEÇERLİ, gözden geçirilmedi. YENİ açık karar: tüketici grubu taksonomisi (Ticarethane/Tarımsal Sulama) en az 2022'nin bir kısmına kadar farklı, kanonik eşleme yok | — (2026-09-03) |

## Copilot İçin Kullanım
Chat'te bağlam vermek için:
```
@workspace #file:dokumanlar/03_veri_modeli.md ...
```
veya `.github/copilot-instructions.md` bu dosyalara zaten atıf yapar.

## Sürüm
Bu dokümanlar SRS **v1.5** (5 P0 kapatılmış — bkz. `02_srs_ozet.md`: P0-2,
P0-3, P0-4, P0-5, P0-6; bu, tek kaynağımızdaki tam liste) ile senkrondur.
Resmî imzalı sürümler: `../dokumanlar_docx/` (varsa) veya SharePoint.
