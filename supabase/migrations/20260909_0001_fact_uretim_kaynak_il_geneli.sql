BEGIN;

-- EPP — Aşama 3/ADIM 3 madde 2 (2026-09-09, gece çalışması) —
-- KPI-02/03/05/06/07 için üretim verisi hazırlığı. İki yeni tablo,
-- `fact_tuketim_ulke_geneli` (migration 20260905_0002) ile BİREBİR AYNI
-- batch/is_active/RLS/policy/GRANT deseni.
--
-- Kaynak (ADIM 1 araştırması, dokumanlar/09_PROJE_DURUMU.md ve
-- 06_canli_veri_operasyon_gunlugu.md'de belgelendi): EPDK ne Excel
-- (2026+) ne Word (2016-2025) formatında il×kaynak JOINT bir üretim
-- kırılımı vermiyor — yalnız İKİ AYRI marjinal seri var: kaynak-bazında
-- ülke geneli (Excel T2/T5, Word Tablo 1.6/1.11) ve il-bazında ülke
-- geneli (Excel T3/T6, Word Tablo 1.7/1.12). Bu iki tablo bu iki
-- marjinali AYRI AYRI tutar — aralarındaki tutarlılık `worker/scripts/
-- mutabakat_uretim.py` (ADIM 3 madde 3) ile çapraz doğrulanır.
--
-- ⚠️ KÜMÜLATİF DEĞİL: T2/T3/T5/T6 (Excel) zaten AY BAZINDA değer veriyor
-- (ADIM 1'de gerçek dosyaya karşı doğrulandı — Şubat < Ocak örneği ile
-- kümülatif OLMADIĞI kanıtlandı). `fact_tuketim_ulke_geneli`'nin
-- `kumulatif_tuketim_mwh` deseni (migration 20260908_0002) buraya
-- KASITLI OLARAK kopyalanmadı — bu tablolarda öyle bir kolon YOK.
--
-- `lisans_id` HER İKİ tabloda da var (Lisanslı/Lisanssız ayrımı,
-- Excel T2/T3 vs T5/T6, Word Tablo 1.6/1.7 vs 1.11/1.12) — KPI-05'in
-- pay/payda tutarlılığı (bkz. dokumanlar/09_PROJE_DURUMU.md ADIM 5 notu)
-- ve mutabakat script'inin (tarih_id, lisans_id) bazında karşılaştırma
-- yapabilmesi için gerekli.

CREATE TABLE IF NOT EXISTS fact_uretim_kaynak_geneli (
  id BIGSERIAL PRIMARY KEY,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  kaynak_id INT NOT NULL REFERENCES dim_kaynak(kaynak_id) ON DELETE RESTRICT,
  lisans_id INT NOT NULL REFERENCES dim_lisans(lisans_id) ON DELETE RESTRICT,
  uretim_mwh NUMERIC(16,3) NOT NULL CHECK (uretim_mwh >= 0),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_fact_uretim_kaynak_geneli_batch
    UNIQUE (tarih_id, kaynak_id, lisans_id, ingestion_batch_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_uretim_kaynak_geneli_active
  ON fact_uretim_kaynak_geneli (tarih_id, kaynak_id, lisans_id) WHERE is_active;

CREATE TABLE IF NOT EXISTS fact_uretim_il_geneli (
  id BIGSERIAL PRIMARY KEY,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  il_kodu INT NOT NULL REFERENCES dim_il(il_kodu) ON DELETE RESTRICT,
  lisans_id INT NOT NULL REFERENCES dim_lisans(lisans_id) ON DELETE RESTRICT,
  uretim_mwh NUMERIC(16,3) NOT NULL CHECK (uretim_mwh >= 0),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_fact_uretim_il_geneli_batch
    UNIQUE (tarih_id, il_kodu, lisans_id, ingestion_batch_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_uretim_il_geneli_active
  ON fact_uretim_il_geneli (tarih_id, il_kodu, lisans_id) WHERE is_active;

-- === RLS + policy + GRANT — fact_tuketim_ulke_geneli ile BİREBİR AYNI
-- desen, iki tablo için tekrarlanır (2026-09-04'teki 4 migration'lık
-- kısmi-grant dersi tekrarlanmasın diye hepsi TEK dosyada). ===

ALTER TABLE fact_uretim_kaynak_geneli ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS viewer_fact_uretim_kaynak_geneli_select ON fact_uretim_kaynak_geneli;
DROP POLICY IF EXISTS data_operator_fact_uretim_kaynak_geneli_insert ON fact_uretim_kaynak_geneli;
DROP POLICY IF EXISTS data_operator_fact_uretim_kaynak_geneli_update ON fact_uretim_kaynak_geneli;
DROP POLICY IF EXISTS admin_fact_uretim_kaynak_geneli_all ON fact_uretim_kaynak_geneli;

CREATE POLICY viewer_fact_uretim_kaynak_geneli_select ON fact_uretim_kaynak_geneli
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer' AND is_active = true);

CREATE POLICY data_operator_fact_uretim_kaynak_geneli_insert ON fact_uretim_kaynak_geneli
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_uretim_kaynak_geneli_update ON fact_uretim_kaynak_geneli
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY admin_fact_uretim_kaynak_geneli_all ON fact_uretim_kaynak_geneli
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

GRANT SELECT ON TABLE fact_uretim_kaynak_geneli TO viewer;
GRANT SELECT, INSERT, UPDATE ON TABLE fact_uretim_kaynak_geneli TO data_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_uretim_kaynak_geneli TO admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_uretim_kaynak_geneli TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_uretim_kaynak_geneli TO service_role;
GRANT USAGE, SELECT ON SEQUENCE fact_uretim_kaynak_geneli_id_seq TO authenticated, service_role;
REVOKE ALL ON TABLE fact_uretim_kaynak_geneli FROM anon;

ALTER TABLE fact_uretim_il_geneli ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS viewer_fact_uretim_il_geneli_select ON fact_uretim_il_geneli;
DROP POLICY IF EXISTS data_operator_fact_uretim_il_geneli_insert ON fact_uretim_il_geneli;
DROP POLICY IF EXISTS data_operator_fact_uretim_il_geneli_update ON fact_uretim_il_geneli;
DROP POLICY IF EXISTS admin_fact_uretim_il_geneli_all ON fact_uretim_il_geneli;

CREATE POLICY viewer_fact_uretim_il_geneli_select ON fact_uretim_il_geneli
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer' AND is_active = true);

CREATE POLICY data_operator_fact_uretim_il_geneli_insert ON fact_uretim_il_geneli
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_uretim_il_geneli_update ON fact_uretim_il_geneli
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY admin_fact_uretim_il_geneli_all ON fact_uretim_il_geneli
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

GRANT SELECT ON TABLE fact_uretim_il_geneli TO viewer;
GRANT SELECT, INSERT, UPDATE ON TABLE fact_uretim_il_geneli TO data_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_uretim_il_geneli TO admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_uretim_il_geneli TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_uretim_il_geneli TO service_role;
GRANT USAGE, SELECT ON SEQUENCE fact_uretim_il_geneli_id_seq TO authenticated, service_role;
REVOKE ALL ON TABLE fact_uretim_il_geneli FROM anon;

COMMIT;
