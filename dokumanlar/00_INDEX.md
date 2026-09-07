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
| `07_word_parser_kapsam.md` | Word (.docx) EPDK raporları — teşhis + kapsam kararları; T11/T10/T4 36 ay TAM aktif (T4 batch 53-88 aktive edildi). T13 (Karar 1) + T1 (Karar 3) kapsam dışı — artık `veri_kapsam_disi` tablosuyla açıkça işaretli (güncel satır sayısı için `09_PROJE_DURUMU.md`'ye bakın, burada tekrarlanmıyor). KPI-26 ve KPI-25 düzeltildi, yeni KPI-27 (Sanayi-hariç tüketim CAGR) eklendi | — (2026-09-03) |
| `08_word_2016_2022_kapsam.md` | Word (.docx) EPDK raporları 2016-2022 — teşhis + TAM implementasyon. 2016-2022'nin TAMAMI (T11/T4) işlendi, T10 yapısal olarak çoğunlukla kaynakta yok (kapsam_disi ile işaretli), taksonomi kararı (RENAME) verildi ve uygulandı | — (2026-09-05) |
| `09_PROJE_DURUMU.md` | **Projenin GÜNCEL, canlı DB'ye karşı doğrulanmış tam durum raporu** — tamamlanan işler, aktivasyon durumu (yıl × tablo), geriye kalanlar, güvenilirlik notu. `SABAH_OZETI.md`'nin YERİNE bakılmalı | — (2026-09-05) |
| `10_TEKNIK_MASTER_DOKUMAN.md` | **Teknik Master Doküman** — Faz 0'dan bugüne HER ŞEYİN (mimari, veri modeli, parser, pipeline, KPI, güvenlik, CI/CD, kronolojik faz geçmişi, açık maddeler, sözlük) tek dosyada, gerçek koda/git'e karşı doğrulanmış hâli. Diğer tüm `dokumanlar/` dosyalarının ÜST ÖZETİ — yeni başlayan biri (insan ya da Claude oturumu) için TEK giriş noktası | — (2026-09-07) |
| `11_yedekleme_runbook.md` | **Yedekleme + geri yükleme runbook** — Supabase Free plan'de otomatik yedek YOK; `worker/scripts/backup.py` (pg_dump --data-only) + GERÇEKTEN denenmiş bir restore drilinin kanıtı (19/19 tablo eşleşti, 0 hata) | — (2026-09-07) |
| ~~`SABAH_OZETI.md`~~ | **SİLİNDİ (2026-09-03)** — 2016-2022 Word aktarımının gece-turu dizisinin geçici notuydu, bazı iddiaları (2021/2022 T11-T10 aktivasyon durumu) DB'yle karşılaştırıldığında yanlış çıktı. Proje durumu için **bkz. `09_PROJE_DURUMU.md`** | — (2026-08-30, silindi 2026-09-03) |

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

**Not (2026-09-07):** Numaralandırma kasıtlı olarak **P0-2**'den
başlıyor — `P0-1` hiçbir dokümanda veya kodda tanımlı değil (repo genelinde
doğrulandı: `grep -rn "P0-1"` sıfır sonuç verir). Orijinal SRS'te bu
slotun neye ayrıldığı bilinmiyor; muhtemelen "PostgreSQL kullan" gibi
tartışmasız bir gereksinimdi ve hiç ayrı bir P0 notu olarak yazılmadı.
Bu bir eksik doküman değil, **numaralandırmanın kendisi 2'den başlıyor**
— ileride yeni bir P0 eklenirse P0-7 kullanılmalı, P0-1 boş bırakılmalı.
