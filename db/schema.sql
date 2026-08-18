-- db/schema.sql
-- Enable Row Level Security (RLS) for all application tables in the public schema
-- Deny-by-default: no policies are created here. Policies must be added separately per-role/use-case.
-- Do NOT modify Supabase system tables. Do NOT change service_role or postgres roles.

BEGIN;

-- Revoke automatic privileges that Supabase may grant to browser roles (anon/authenticated).
-- If these roles have been granted schema/table/sequence/function rights, remove them so RLS + explicit policies control access.
REVOKE ALL ON SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;

-- Enable RLS on application tables (public schema).
-- Add any additional application tables here as they are created.
ALTER TABLE public.source_asset ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_batch ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_tuketim ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_uretim ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_abone ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_serbest_tuketici ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_hava_aylik ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_hava_aylik_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_tarih ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_il ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_kaynak ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_tuketici_grubu ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_lisans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sistem_parametre ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kpi_esik ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.il_baz_sicaklik ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- NOTE:
-- 1) Enabling RLS without policies causes deny-by-default (recommended). Create explicit policies
--    for roles that should be allowed to SELECT/INSERT/UPDATE/DELETE.
-- 2) This file intentionally does not alter service_role or postgres roles.
-- 3) If the project uses additional application tables, add corresponding ALTER TABLE ... ENABLE ROW LEVEL SECURITY;

COMMIT;
