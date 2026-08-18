# dokumanlar/ — Copilot Okunabilir Proje Dokümanları

Bu klasördeki **.md** dosyaları Copilot'un kod üretirken okuduğu kaynaktır.
İnsan okuması için imzalı **.docx** sürümleri SharePoint/OneDrive (önceki paylaşımlar) veya ayrı `dokumanlar_docx/` klasöründe tutulur.

## Nasıl kullanılır (VS Code Copilot Chat)
```
@workspace #file:dokumanlar/03_veri_modeli.md db/schema.sql'i bu modele göre üret
```
`.github/copilot-instructions.md` bu dosyalara zaten atıf yapar; çoğu zaman
sadece @workspace demeniz yeterli olur.

## Dosyalar
- 00_INDEX.md — dizin
- 01_kavramsal_tasarim.md — amaç, mimari, fazlar
- 02_srs_ozet.md — KRİTİK P0 kuralları
- 03_veri_modeli.md — tablolar + DDL
- 04_kpi_sozlesmeleri.md — KPI formülleri
- 05_kaynak_dosya_sozlesmesi.md — parser haritası
