BEGIN;

-- dim_kaynak seed'i (migration 20260819_0004) yalnız 11 kaynak içeriyordu;
-- worker/parser.py'nin KAYNAK_ESLEME'i (dokumanlar/05_kaynak_dosya_sozlesmesi.md
-- — Kaynak Türü Eşleme) 13 kanonik kaynak tanıyor. Gerçek 2026 Ocak EPDK
-- dosyasıyla epdk_aylik_isle() uçtan uca çalıştırılınca (2026-08-30) T1/T4'te
-- "Motorin" ve "Nafta" sütunları bulundu — bu iki kaynak seed'de hiç yoktu,
-- fact_uretim_yukle() dim_kaynak_id_bul() üzerinden ValueError ile patlıyordu.
-- İkisi de mevcut fosil kaynakların (Doğal Gaz, İthal Kömür, Linyit, Taş
-- Kömürü, Asfaltit, Fuel Oil) izlediği aynı desenle eklenir.
INSERT INTO dim_kaynak (kaynak_adi, yenilenebilir_mi, grup)
VALUES
  ('Motorin', false, 'Fosil'),
  ('Nafta', false, 'Fosil')
ON CONFLICT (kaynak_adi) DO NOTHING;

COMMIT;
