BEGIN;

-- fact_serbest_tuketici: gerçek EPDK Tablo 13 verisiyle doğrulandı (2026-08-30):
-- 1) tur CHECK'i gerçek değerlerle uyuşmuyordu - 'Lisansli'/'Lisanssiz' yanlış
--    varsayımdı (T13 lisans durumuyla değil, serbest tüketici hakkı
--    kullanım durumuyla ilgili). Gerçek değerler (Türkçe karaktersiz,
--    dim_lisans.tur ile aynı adlandırma kuralı): 'Serbest Tuketici',
--    'ST Olma Hakki Bulunmayan Aboneler', 'ST Olma Hakkini Kullanmayan
--    Aboneler'.
-- 2) Grain eksikti: her (il, tur) için AYRICA 5 tüketici grubuna
--    (Mesken/Sanayi/Kamu ve Özel Hizmetler/Tarımsal/Aydınlatma) bölünmüş
--    tuketim_mwh + tuketici_sayisi var - grup_id doğal anahtarın parçası
--    olmalı.
-- Tablo Faz 0'da hiç ingest edilmediği için veri taşıma/backfill gerekmiyor.

-- tur üzerindeki (CREATE TABLE'da isimsiz bırakıldığı için otomatik
-- üretilmiş, adı garantili olmayan) eski CHECK kısıtını bul ve kaldır.
DO $$
DECLARE
  con RECORD;
BEGIN
  FOR con IN
    SELECT c.conname
    FROM pg_constraint c
    JOIN pg_class rel ON rel.oid = c.conrelid
    JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(c.conkey)
    WHERE rel.relname = 'fact_serbest_tuketici'
      AND att.attname = 'tur'
      AND c.contype = 'c'
  LOOP
    EXECUTE format('ALTER TABLE fact_serbest_tuketici DROP CONSTRAINT %I', con.conname);
  END LOOP;
END $$;

ALTER TABLE fact_serbest_tuketici
  ADD CONSTRAINT fact_serbest_tuketici_tur_check
  CHECK (tur IN ('Serbest Tuketici', 'ST Olma Hakki Bulunmayan Aboneler', 'ST Olma Hakkini Kullanmayan Aboneler'));

ALTER TABLE fact_serbest_tuketici
  ADD COLUMN grup_id INT NOT NULL REFERENCES dim_tuketici_grubu(grup_id) ON DELETE RESTRICT;

ALTER TABLE fact_serbest_tuketici DROP CONSTRAINT IF EXISTS uq_fact_serbest_tuketici_batch;
ALTER TABLE fact_serbest_tuketici
  ADD CONSTRAINT uq_fact_serbest_tuketici_batch
  UNIQUE (il_kodu, tarih_id, tur, grup_id, ingestion_batch_id);

DROP INDEX IF EXISTS uq_fact_serbest_tuketici_active;
CREATE UNIQUE INDEX uq_fact_serbest_tuketici_active
  ON fact_serbest_tuketici (il_kodu, tarih_id, tur, grup_id)
  WHERE is_active;

COMMIT;
