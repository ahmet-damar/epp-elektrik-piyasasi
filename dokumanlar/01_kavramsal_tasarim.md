# EPP — Kavramsal Tasarım

## 1. Amaç
EPDK Elektrik Piyasası Sektör Raporu (aylık + yıllık) verilerini bir veri
tabanına yükleyen, hava durumu (Open-Meteo) ile zenginleştiren, KPI'lar üreten
ve dashboard'a dönüştüren **açık kaynak** web platformu.

## 2. Dört Temel Yetenek
1. **Veri Alımı:** Dosya yükleme (Excel/Word) + API çekimi (Open-Meteo, ileride EPİAŞ)
2. **Depolama & Modelleme:** PostgreSQL yıldız şema, batch bazlı sürümleme
3. **Analitik:** KPI'lar, karşılaştırma, korelasyon, dashboard
4. **Tahminleme:** (Faz 4) hava + takvim ile zaman serisi tahmini

## 3. Mimari (3 Katman)
```
SUNUM      : Streamlit (app/dashboard.py)     — dashboard (Faz 2); Next.js+TS "Son Faz"'a ertelendi
İŞLEM      : Python + FastAPI (worker/)       — parser, KPI, jobs
VERİ       : PostgreSQL (db/)                 — yıldız şema + batch
```
Tüm bileşenler açık kaynak; Docker ile self-host edilebilir.

**NOT (2026-08-30, Faz 2):** Sunum katmanı kararı gözden geçirildi — bkz.
dokumanlar/06_adr_dashboard_teknoloji.md. Next.js+TypeScript'e geçiş
kapsam dışı bırakılmadı, yalnızca "Son Faz" (LinkedIn yayını) öncesine
bilinçli olarak ertelendi.

## 4. Uçtan Uca Veri Akışı (dosya yükleme)
1. Kullanıcı EPDK dosyası yükler → SHA-256 hash
2. `source_asset` kaydı (kind='file') + `ingestion_batch` (queued)
3. Worker batch'i atomik sahiplenir → parse + doğrulama
4. Önizleme/onay → kabul edilen satırlar fact tablosuna (is_active=false)
5. Aktivasyon transaction → is_active=true (eski sürüm pasif)
6. Dashboard güncel aktif sürümü gösterir

## 5. MVP Kapsamı
- **İçinde:** EPDK aylık + yıllık, Open-Meteo, KPI'lar, dashboard, Eskişehir pilotu
- **Dışında (sonraki fazlar):** LinkedIn yayını (son faz), EPİAŞ (Faz 5),
  TEİAŞ projeksiyon (Faz 6), tahminleme (Faz 4)

## 6. Teknoloji (Tümü OSI Açık Kaynak)
| Katman | Seçim | Lisans |
|--------|-------|--------|
| Web | Next.js + TypeScript | MIT/Apache-2.0 |
| Backend | Python 3.12 + FastAPI | PSF/MIT |
| DB | PostgreSQL | PostgreSQL |
| Parser | pandas, openpyxl, python-docx | BSD/MIT |
| Hava | Open-Meteo | CC BY 4.0 |
| Test | pytest, vitest | MIT |

ADR-6: Uygulama bileşenleri OSI açık kaynak; GitHub/Actions/GHCR yönetilen
servis istisnası (self-host alternatifi belgeli).

## 7. Fazlar
- **Faz 0:** Repo + şema + Eskişehir PoC + KPI-01..10/13/23/24
- **Faz 1:** Asenkron worker, tüm iller, sürümleme
- **Faz 2:** Dashboard (KPI görselleştirme)
- **Faz 3:** Hava normalizasyonu (KPI-11/12 production), yıllık KPI'lar
- **Faz 4:** Tahminleme · **Faz 5:** EPİAŞ · **Faz 6:** Projeksiyon
- **Son Faz:** LinkedIn yayını
