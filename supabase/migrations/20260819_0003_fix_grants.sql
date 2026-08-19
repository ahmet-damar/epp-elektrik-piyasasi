BEGIN;

-- Revoke any legacy direct privileges so RLS (app_metadata.role) is authoritative.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM authenticated;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM viewer, data_operator, admin;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM anon;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM viewer, data_operator, admin;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated, viewer, data_operator, admin;

-- Remove object-level capabilities that are not required for browser-facing roles
REVOKE REFERENCES, TRIGGER, TRUNCATE ON ALL TABLES IN SCHEMA public FROM anon, authenticated, viewer, data_operator, admin;

-- Schema usage: only authenticated and service_role should have usage on public
REVOKE USAGE ON SCHEMA public FROM anon;
REVOKE USAGE ON SCHEMA public FROM viewer, data_operator, admin;
GRANT USAGE ON SCHEMA public TO authenticated, service_role;

-- current_app_role function: restrict execute to authenticated and service_role only
REVOKE ALL ON FUNCTION public.current_app_role() FROM public;
GRANT EXECUTE ON FUNCTION public.current_app_role() TO authenticated, service_role;

-- authenticated: dimension tables - SELECT only
GRANT SELECT ON TABLE
  dim_tarih,
  dim_il,
  dim_kaynak,
  dim_tuketici_grubu,
  dim_lisans
TO authenticated;

-- For operational tables where admin policy allows full operations, grant DELETE to authenticated as well
-- (admin policies in 0002: source_asset, ingestion_batch, fact_tuketim, fact_uretim, fact_abone, fact_serbest_tuketici, fact_hava_aylik)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  source_asset,
  ingestion_batch,
  fact_tuketim,
  fact_uretim,
  fact_abone,
  fact_serbest_tuketici,
  fact_hava_aylik
TO authenticated;

-- Jobs, system parameters and KPI config: authenticated can read and maintain
GRANT SELECT, INSERT, UPDATE ON TABLE job_status TO authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE sistem_parametre, kpi_esik TO authenticated;

-- audit_log is append-only: authenticated can read and insert only
GRANT SELECT, INSERT ON TABLE audit_log TO authenticated;

-- service_role: full operational access (except audit_log remains append-only)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  dim_tarih,
  dim_il,
  dim_kaynak,
  dim_tuketici_grubu,
  dim_lisans,
  source_asset,
  ingestion_batch,
  fact_tuketim,
  fact_uretim,
  fact_abone,
  fact_serbest_tuketici,
  fact_hava_aylik,
  job_status,
  sistem_parametre,
  kpi_esik
TO service_role;

GRANT SELECT, INSERT ON TABLE audit_log TO service_role;

-- Identity/serial access for authenticated and service_role; never grant to anon.
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role;

-- Do not alter properties of service_role or postgres (BYPASSRLS, SUPERUSER, etc.)

COMMIT;
