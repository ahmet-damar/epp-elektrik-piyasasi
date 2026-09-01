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
| `07_word_parser_kapsam.md` | Word (.docx) EPDK raporları — teşhis + kapsam kararları (T13/baglanti); 2023+2024 yüklü VE aktif (24 ay). Sırada: 2025, sonra T1/T4. KPI-25 hâlâ güvenilmez (Sanayi/kısmi-yıl karışıklığı) | — (2026-09-02) |

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
