CREATE TABLE IF NOT EXISTS dim_tarih (
  tarih_id INT PRIMARY KEY,
  yil SMALLINT NOT NULL CHECK (yil >= 2000),
  ay SMALLINT NOT NULL CHECK (ay BETWEEN 0 AND 12),
  ceyrek SMALLINT NOT NULL CHECK (ceyrek BETWEEN 0 AND 4),
  ay_adi TEXT,
  yil_ay TEXT,
  donem_tipi TEXT NOT NULL CHECK (donem_tipi IN ('aylik', 'yillik'))
);

CREATE TABLE IF NOT EXISTS dim_il (
  il_kodu INT PRIMARY KEY CHECK (il_kodu BETWEEN 1 AND 81),
  il_adi TEXT NOT NULL,
  bolge TEXT,
  dagitim_bolgesi TEXT
);

CREATE TABLE IF NOT EXISTS dim_kaynak (
  kaynak_id SERIAL PRIMARY KEY,
  kaynak_adi TEXT NOT NULL UNIQUE,
  yenilenebilir_mi BOOLEAN NOT NULL DEFAULT false,
  grup TEXT NOT NULL CHECK (grup IN ('Yenilenebilir', 'Fosil'))
);

CREATE TABLE IF NOT EXISTS dim_tuketici_grubu (
  grup_id SERIAL PRIMARY KEY,
  grup_adi TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_lisans (
  lisans_id SERIAL PRIMARY KEY,
  tur TEXT NOT NULL UNIQUE CHECK (tur IN ('Lisansli', 'Lisanssiz'))
);

CREATE TABLE IF NOT EXISTS source_asset (
  source_asset_id BIGSERIAL PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_kind TEXT NOT NULL CHECK (source_kind IN ('file', 'api')),
  source_period TEXT,
  donem_tipi TEXT,
  file_name TEXT,
  file_hash TEXT,
  storage_path TEXT,
  source_uri TEXT,
  request_hash TEXT,
  uploaded_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (
    (source_kind = 'file' AND file_name IS NOT NULL AND file_hash IS NOT NULL)
    OR (source_kind = 'api' AND source_uri IS NOT NULL AND request_hash IS NOT NULL)
  )
);

CREATE TABLE IF NOT EXISTS ingestion_batch (
  batch_id BIGSERIAL PRIMARY KEY,
  source_asset_id BIGINT NOT NULL REFERENCES source_asset(source_asset_id) ON DELETE RESTRICT,
  parser_version TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'retrying', 'dead_letter')),
  total_row_count INT NOT NULL DEFAULT 0 CHECK (total_row_count >= 0),
  accepted_row_count INT NOT NULL DEFAULT 0 CHECK (accepted_row_count >= 0),
  rejected_row_count INT NOT NULL DEFAULT 0 CHECK (rejected_row_count >= 0),
  error_summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_asset_id, parser_version, schema_version)
);

CREATE TABLE IF NOT EXISTS fact_tuketim (
  fact_tuketim_id BIGSERIAL PRIMARY KEY,
  il_kodu INT NOT NULL REFERENCES dim_il(il_kodu) ON DELETE RESTRICT,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  grup_id INT NOT NULL REFERENCES dim_tuketici_grubu(grup_id) ON DELETE RESTRICT,
  baglanti TEXT NOT NULL CHECK (baglanti IN ('iletim', 'dagitim')),
  tuketim_mwh NUMERIC(16,3) NOT NULL CHECK (tuketim_mwh >= 0),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_fact_tuketim_batch UNIQUE (il_kodu, tarih_id, grup_id, baglanti, ingestion_batch_id)
);

CREATE TABLE IF NOT EXISTS fact_uretim (
  fact_uretim_id BIGSERIAL PRIMARY KEY,
  il_kodu INT NOT NULL REFERENCES dim_il(il_kodu) ON DELETE RESTRICT,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  kaynak_id INT NOT NULL REFERENCES dim_kaynak(kaynak_id) ON DELETE RESTRICT,
  lisans_id INT NOT NULL REFERENCES dim_lisans(lisans_id) ON DELETE RESTRICT,
  kurulu_guc_mw NUMERIC(16,3) NOT NULL CHECK (kurulu_guc_mw >= 0),
  uretim_mwh NUMERIC(16,3) NOT NULL CHECK (uretim_mwh >= 0),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_fact_uretim_batch UNIQUE (il_kodu, tarih_id, kaynak_id, lisans_id, ingestion_batch_id)
);

CREATE TABLE IF NOT EXISTS fact_abone (
  fact_abone_id BIGSERIAL PRIMARY KEY,
  il_kodu INT NOT NULL REFERENCES dim_il(il_kodu) ON DELETE RESTRICT,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  grup_id INT NOT NULL REFERENCES dim_tuketici_grubu(grup_id) ON DELETE RESTRICT,
  abone_sayisi BIGINT NOT NULL CHECK (abone_sayisi >= 0),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_fact_abone_batch UNIQUE (il_kodu, tarih_id, grup_id, ingestion_batch_id)
);

CREATE TABLE IF NOT EXISTS fact_serbest_tuketici (
  fact_serbest_tuketici_id BIGSERIAL PRIMARY KEY,
  il_kodu INT NOT NULL REFERENCES dim_il(il_kodu) ON DELETE RESTRICT,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  tur TEXT NOT NULL CHECK (tur IN ('Lisansli', 'Lisanssiz')),
  tuketim_mwh NUMERIC(16,3) NOT NULL CHECK (tuketim_mwh >= 0),
  tuketici_sayisi BIGINT NOT NULL CHECK (tuketici_sayisi >= 0),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_fact_serbest_tuketici_batch UNIQUE (il_kodu, tarih_id, tur, ingestion_batch_id)
);

CREATE TABLE IF NOT EXISTS fact_hava_aylik (
  fact_hava_aylik_id BIGSERIAL PRIMARY KEY,
  il_kodu INT NOT NULL REFERENCES dim_il(il_kodu) ON DELETE RESTRICT,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  t_ort NUMERIC(6,2) CHECK (t_ort >= -100 AND t_ort <= 100),
  hdd NUMERIC(8,2) CHECK (hdd >= 0),
  cdd NUMERIC(8,2) CHECK (cdd >= 0),
  radyasyon NUMERIC(8,2),
  ruzgar NUMERIC(8,2),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_fact_hava_batch UNIQUE (il_kodu, tarih_id, ingestion_batch_id)
);

CREATE TABLE IF NOT EXISTS job_status (
  job_id BIGSERIAL PRIMARY KEY,
  correlation_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'retrying', 'dead_letter')),
  attempt_count INT NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  locked_by TEXT,
  heartbeat_at TIMESTAMPTZ,
  next_retry_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sistem_parametre (
  parametre_adi TEXT PRIMARY KEY,
  parametre_degeri NUMERIC(10,3) NOT NULL,
  aciklama TEXT
);

CREATE TABLE IF NOT EXISTS kpi_esik (
  kpi_id TEXT NOT NULL,
  surum TEXT NOT NULL,
  yesil_alt NUMERIC(10,3),
  sari_alt NUMERIC(10,3),
  kirmizi_alt NUMERIC(10,3),
  yon TEXT CHECK (yon IN ('yukselik', 'alcelik')),
  PRIMARY KEY (kpi_id, surum)
);

CREATE TABLE IF NOT EXISTS audit_log (
  audit_id BIGSERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  record_id BIGINT,
  action_type TEXT NOT NULL CHECK (action_type IN ('INSERT', 'UPDATE', 'DELETE', 'SELECT')),
  actor_name TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_tuketim_active
  ON fact_tuketim (il_kodu, tarih_id, grup_id, baglanti)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_uretim_active
  ON fact_uretim (il_kodu, tarih_id, kaynak_id, lisans_id)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_abone_active
  ON fact_abone (il_kodu, tarih_id, grup_id)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_serbest_tuketici_active
  ON fact_serbest_tuketici (il_kodu, tarih_id, tur)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_hava_aylik_active
  ON fact_hava_aylik (il_kodu, tarih_id)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_fact_tuketim_batch_id ON fact_tuketim (ingestion_batch_id);
CREATE INDEX IF NOT EXISTS idx_fact_uretim_batch_id ON fact_uretim (ingestion_batch_id);
CREATE INDEX IF NOT EXISTS idx_fact_abone_batch_id ON fact_abone (ingestion_batch_id);
CREATE INDEX IF NOT EXISTS idx_fact_serbest_tuketici_batch_id ON fact_serbest_tuketici (ingestion_batch_id);
CREATE INDEX IF NOT EXISTS idx_fact_hava_aylik_batch_id ON fact_hava_aylik (ingestion_batch_id);
CREATE INDEX IF NOT EXISTS idx_source_asset_kind ON source_asset (source_kind);
CREATE INDEX IF NOT EXISTS idx_ingestion_batch_status ON ingestion_batch (status);

CREATE OR REPLACE FUNCTION public.current_app_role()
RETURNS text
LANGUAGE sql
STABLE
SET search_path = public, pg_catalog
AS $$
  SELECT CASE
    WHEN auth.jwt() IS NULL THEN NULL
    ELSE CASE
      WHEN (auth.jwt() -> 'app_metadata' ->> 'role') IN ('viewer', 'data_operator', 'admin')
        THEN auth.jwt() -> 'app_metadata' ->> 'role'
      ELSE NULL
    END
  END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'viewer') THEN
    CREATE ROLE viewer NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'data_operator') THEN
    CREATE ROLE data_operator NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin') THEN
    CREATE ROLE admin NOLOGIN;
  END IF;
END $$;

ALTER TABLE source_asset ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_batch ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_tuketim ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_uretim ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_abone ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_serbest_tuketici ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_hava_aylik ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY viewer_source_asset_select ON source_asset
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer');

CREATE POLICY viewer_ingestion_batch_select ON ingestion_batch
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer');

CREATE POLICY viewer_fact_tuketim_select ON fact_tuketim
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer' AND is_active = true);

CREATE POLICY viewer_fact_uretim_select ON fact_uretim
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer' AND is_active = true);

CREATE POLICY viewer_fact_abone_select ON fact_abone
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer' AND is_active = true);

CREATE POLICY viewer_fact_serbest_tuketici_select ON fact_serbest_tuketici
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer' AND is_active = true);

CREATE POLICY viewer_fact_hava_aylik_select ON fact_hava_aylik
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer' AND is_active = true);

CREATE POLICY data_operator_source_asset_insert ON source_asset
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_source_asset_update ON source_asset
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_batch_insert ON ingestion_batch
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_batch_update ON ingestion_batch
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_tuketim_insert ON fact_tuketim
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_tuketim_update ON fact_tuketim
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_uretim_insert ON fact_uretim
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_uretim_update ON fact_uretim
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_abone_insert ON fact_abone
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_abone_update ON fact_abone
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_serbest_tuketici_insert ON fact_serbest_tuketici
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_serbest_tuketici_update ON fact_serbest_tuketici
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_hava_aylik_insert ON fact_hava_aylik
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_hava_aylik_update ON fact_hava_aylik
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY admin_source_asset_all ON source_asset
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY admin_ingestion_batch_all ON ingestion_batch
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY admin_fact_tuketim_all ON fact_tuketim
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY admin_fact_uretim_all ON fact_uretim
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY admin_fact_abone_all ON fact_abone
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY admin_fact_serbest_tuketici_all ON fact_serbest_tuketici
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY admin_fact_hava_aylik_all ON fact_hava_aylik
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY admin_audit_log_select ON audit_log
  FOR SELECT TO admin
  USING (public.current_app_role() = 'admin');

CREATE POLICY admin_audit_log_insert ON audit_log
  FOR INSERT TO admin
  WITH CHECK (public.current_app_role() = 'admin');

-- Service role bypasses RLS by design in Supabase. Do not expose the service role key to browser/dashboard or frontend code.

GRANT USAGE ON SCHEMA public TO viewer, data_operator, admin;
GRANT SELECT ON TABLE dim_tarih, dim_il, dim_kaynak, dim_tuketici_grubu, dim_lisans TO viewer;
GRANT SELECT ON TABLE source_asset, ingestion_batch, fact_tuketim, fact_uretim, fact_abone, fact_serbest_tuketici, fact_hava_aylik TO viewer;
GRANT SELECT, INSERT, UPDATE ON TABLE source_asset, ingestion_batch TO data_operator;
GRANT SELECT, INSERT, UPDATE ON TABLE fact_tuketim, fact_uretim, fact_abone, fact_serbest_tuketici, fact_hava_aylik TO data_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE source_asset, ingestion_batch TO admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_tuketim, fact_uretim, fact_abone, fact_serbest_tuketici, fact_hava_aylik TO admin;
GRANT SELECT, INSERT ON TABLE audit_log TO admin;

BEGIN;

REVOKE ALL ON SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;

ALTER TABLE public.source_asset ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_batch ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_tuketim ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_uretim ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_abone ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_serbest_tuketici ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_hava_aylik ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_tarih ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_il ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_kaynak ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_tuketici_grubu ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_lisans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sistem_parametre ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kpi_esik ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

COMMIT;