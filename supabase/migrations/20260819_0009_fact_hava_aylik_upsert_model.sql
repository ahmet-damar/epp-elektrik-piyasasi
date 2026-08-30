BEGIN;

-- Faz 3 (hava normalizasyonu): fact_hava_aylik diğer fact tablolarının
-- batch-versiyonlama modelinden (ingestion_batch_id çoğulluğu + is_active)
-- BİLİNÇLİ OLARAK farklıdır - dokumanlar/02_srs_ozet.md SÜRÜMLEME KURALI:
-- "Hava (fact_hava_aylik): güncel kayıt (UPSERT) + JSONB değişiklik logu."
-- Her (il_kodu, tarih_id) için TEK güncel satır olur; worker/jobs/
-- fetch_weather.py bunun üzerine UPSERT eder. ingestion_batch_id son
-- yazan batch'i işaret etmeye devam eder (provenance), ama artık
-- çoğulluk/tekillik anahtarının parçası DEĞİLDİR.

-- Politika is_active'e bağımlı (USING (... AND is_active = true)) - kolonu
-- DÜŞÜRMEDEN ÖNCE politikayı düşürüp is_active'siz yeniden kurmak gerekir
-- (aksi halde "cannot drop column ... because other objects depend on it").
DROP POLICY IF EXISTS viewer_fact_hava_aylik_select ON fact_hava_aylik;

ALTER TABLE fact_hava_aylik DROP CONSTRAINT IF EXISTS uq_fact_hava_batch;
ALTER TABLE fact_hava_aylik ADD CONSTRAINT uq_fact_hava_aylik_il_tarih UNIQUE (il_kodu, tarih_id);
ALTER TABLE fact_hava_aylik DROP COLUMN IF EXISTS is_active;

CREATE POLICY viewer_fact_hava_aylik_select ON fact_hava_aylik
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer');

-- fact_hava_aylik_log: append-only değişiklik geçmişi (audit_log ile aynı
-- erişim deseni - yalnız SELECT+INSERT, UPDATE/DELETE hiç kimseye açılmaz).
CREATE TABLE IF NOT EXISTS fact_hava_aylik_log (
  log_id BIGSERIAL PRIMARY KEY,
  il_kodu INT NOT NULL REFERENCES dim_il(il_kodu) ON DELETE RESTRICT,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  old_data JSONB,
  new_data JSONB NOT NULL,
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fact_hava_aylik_log_il_tarih ON fact_hava_aylik_log (il_kodu, tarih_id);

ALTER TABLE fact_hava_aylik_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY data_operator_fact_hava_aylik_log_select ON fact_hava_aylik_log
  FOR SELECT TO data_operator
  USING (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_hava_aylik_log_insert ON fact_hava_aylik_log
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY admin_fact_hava_aylik_log_select ON fact_hava_aylik_log
  FOR SELECT TO admin
  USING (public.current_app_role() = 'admin');

CREATE POLICY admin_fact_hava_aylik_log_insert ON fact_hava_aylik_log
  FOR INSERT TO admin
  WITH CHECK (public.current_app_role() = 'admin');

GRANT SELECT, INSERT ON TABLE fact_hava_aylik_log TO data_operator, admin, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE fact_hava_aylik_log_log_id_seq TO authenticated, service_role;

COMMIT;
