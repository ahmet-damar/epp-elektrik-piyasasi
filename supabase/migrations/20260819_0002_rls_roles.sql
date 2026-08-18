BEGIN;

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

ALTER TABLE source_asset ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_batch ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_tuketim ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_uretim ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_abone ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_serbest_tuketici ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_hava_aylik ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS viewer_source_asset_select ON source_asset;
DROP POLICY IF EXISTS viewer_ingestion_batch_select ON ingestion_batch;
DROP POLICY IF EXISTS data_operator_source_asset_insert ON source_asset;
DROP POLICY IF EXISTS data_operator_source_asset_update ON source_asset;
DROP POLICY IF EXISTS data_operator_batch_insert ON ingestion_batch;
DROP POLICY IF EXISTS data_operator_batch_update ON ingestion_batch;
DROP POLICY IF EXISTS data_operator_fact_tuketim_insert ON fact_tuketim;
DROP POLICY IF EXISTS data_operator_fact_tuketim_update ON fact_tuketim;
DROP POLICY IF EXISTS data_operator_fact_uretim_insert ON fact_uretim;
DROP POLICY IF EXISTS data_operator_fact_uretim_update ON fact_uretim;
DROP POLICY IF EXISTS data_operator_fact_abone_insert ON fact_abone;
DROP POLICY IF EXISTS data_operator_fact_abone_update ON fact_abone;
DROP POLICY IF EXISTS data_operator_fact_serbest_tuketici_insert ON fact_serbest_tuketici;
DROP POLICY IF EXISTS data_operator_fact_serbest_tuketici_update ON fact_serbest_tuketici;
DROP POLICY IF EXISTS data_operator_fact_hava_aylik_insert ON fact_hava_aylik;
DROP POLICY IF EXISTS data_operator_fact_hava_aylik_update ON fact_hava_aylik;
DROP POLICY IF EXISTS admin_source_asset_all ON source_asset;
DROP POLICY IF EXISTS admin_ingestion_batch_all ON ingestion_batch;
DROP POLICY IF EXISTS admin_fact_tuketim_all ON fact_tuketim;
DROP POLICY IF EXISTS admin_fact_uretim_all ON fact_uretim;
DROP POLICY IF EXISTS admin_fact_abone_all ON fact_abone;
DROP POLICY IF EXISTS admin_fact_serbest_tuketici_all ON fact_serbest_tuketici;
DROP POLICY IF EXISTS admin_fact_hava_aylik_all ON fact_hava_aylik;
DROP POLICY IF EXISTS viewer_fact_tuketim_select ON fact_tuketim;
DROP POLICY IF EXISTS viewer_fact_uretim_select ON fact_uretim;
DROP POLICY IF EXISTS viewer_fact_abone_select ON fact_abone;
DROP POLICY IF EXISTS viewer_fact_serbest_tuketici_select ON fact_serbest_tuketici;
DROP POLICY IF EXISTS viewer_fact_hava_aylik_select ON fact_hava_aylik;
DROP POLICY IF EXISTS admin_audit_insert ON audit_log;
DROP POLICY IF EXISTS admin_audit_select ON audit_log;

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

COMMIT;
