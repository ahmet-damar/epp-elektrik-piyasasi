BEGIN;

-- Görev 3 (2026-09-05): kpi_esik tablosu 20260819_0001'den beri boştu,
-- hiçbir kod tüketmiyordu. Bu tur dashboard'a trafik ışığı eklerken
-- ilk gerçek veri satırları girildi — yalnız DEĞİŞİM/SAPMA/YOĞUNLAŞMA
-- tipi metrikler için (kurulu güç, toplam üretim/tüketim gibi ham
-- büyüklüklere KEYFİ bir "iyi/kötü" hedefi uydurulmadı, bilinçli olarak
-- eşiksiz bırakıldı — bkz. worker/kpi.py:esik_rengi() sözleşmesi).
--
-- KPI-06 (HHI, yön=alcelik): yerleşik ABD DOJ/FTC birleşme kılavuzu
-- eşikleri (0,15/0,25), 0-1 skalaya (bu projenin HHI ölçeği) çevrildi —
-- keyfi değil, tanınmış bir standart.
--
-- KPI-12 (Norm Sapması, yön=alcelik): dashboard bu KPI için |değer|
-- (mutlak değer) geçirecek — worker/kpi.py:esik_rengi() işareti kendisi
-- yorumlamaz.
--
-- KPI-13 (Tüketim YoY, yön=yukselik): gerçek dağılıma dayalı (2016-2025,
-- Sanayi-hariç, n=114 ay): medyan %+3,5, p10=-%4,4 — negatif YoY nadir/
-- dikkat çekici.
--
-- KPI-25/KPI-27 (CAGR, tüketim/Sanayi-hariç, yön=yukselik): gerçek yıllık
-- değişim aralığına (-%1,4…+%9,4) dayalı.
--
-- KPI-26 (yenilenebilir kurulu güç CAGR, yön=yukselik): AYRI bir bant —
-- KPI-25/27'nin tüketim bandını (0-3%) kullanmak YANLIŞ olurdu. Gerçek
-- veri (2016-2025 yıl-sonu toplam): en "sakin" yıllar bile %+9,7-15
-- arası (2016→17'nin %+210'u erken-adaptasyon, 2025→26'nın %+245'i
-- Lisanslı verinin İLK KEZ sisteme girmesinden kaynaklanan bir kapsam
-- artışı — ikisi de gerçek büyüme değil, kalibrasyondan HARİÇ tutuldu).
INSERT INTO kpi_esik (kpi_id, surum, yesil_alt, sari_alt, kirmizi_alt, yon) VALUES
  ('KPI-06', 'v1', 0.15, 0.25, NULL, 'alcelik'),
  ('KPI-12', 'v1', 5.0, 10.0, NULL, 'alcelik'),
  ('KPI-13', 'v1', 0.0, -5.0, NULL, 'yukselik'),
  ('KPI-25', 'v1', 3.0, 0.0, NULL, 'yukselik'),
  ('KPI-26', 'v1', 15.0, 5.0, NULL, 'yukselik'),
  ('KPI-27', 'v1', 3.0, 0.0, NULL, 'yukselik')
ON CONFLICT (kpi_id, surum) DO UPDATE SET
  yesil_alt = excluded.yesil_alt,
  sari_alt = excluded.sari_alt,
  kirmizi_alt = excluded.kirmizi_alt,
  yon = excluded.yon;

COMMIT;
