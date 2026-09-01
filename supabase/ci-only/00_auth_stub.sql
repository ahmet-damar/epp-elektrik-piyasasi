-- EPP — CI-only auth schema stub. NOT a real migration — never apply to
-- Supabase (staging/prod already provides a real `auth` schema; this file
-- is intentionally kept OUTSIDE supabase/migrations/ so deploy.yml's
-- `supabase/migrations/*.sql` glob never picks it up).
--
-- Why this exists: our migrations (0002_rls_roles.sql) define
-- public.current_app_role(), which calls auth.jwt(). On real Supabase that
-- function already exists; on CI's plain `postgres:16` service (no
-- Supabase image) it doesn't, so applying 0002 fails with
-- "schema auth does not exist".
--
-- This reproduces the REAL auth.jwt() mechanism (not a fake/simplified
-- one), verified against Supabase's own source:
--   - schema: supabase/postgres, migrations/db/init-scripts/
--     00000000000001-auth-schema.sql — "CREATE SCHEMA IF NOT EXISTS auth
--     AUTHORIZATION supabase_admin;"
--   - auth.jwt() reads the `request.jwt.claims` GUC that PostgREST sets per
--     request and parses it as jsonb; current_setting(..., true) uses the
--     missing_ok flag so an unset GUC returns NULL instead of erroring.
--     (Legacy deployments used the singular `request.jwt.claim` GUC name;
--     both are read here for robustness.)
--
-- Net effect: over a direct psql/superuser connection (no PostgREST layer
-- setting the GUC — exactly CI's ingest tests), auth.jwt() correctly
-- returns NULL, matching current_app_role()'s
-- "WHEN auth.jwt() IS NULL THEN NULL" branch on real Supabase too.

CREATE SCHEMA IF NOT EXISTS auth;

CREATE OR REPLACE FUNCTION auth.jwt() RETURNS jsonb
LANGUAGE sql STABLE
AS $$
  SELECT
    COALESCE(
      NULLIF(current_setting('request.jwt.claims', true), ''),
      NULLIF(current_setting('request.jwt.claim', true), '')
    )::jsonb
$$;

-- Real Supabase grants USAGE ON SCHEMA auth + EXECUTE ON auth.jwt() to its
-- own managed roles (anon/authenticated/service_role) by default - AND
-- (found 2026-09-02, migration 20260819_0015) to this project's custom
-- roles (viewer/data_operator/admin) via that migration, since Supabase's
-- own setup predates them and can't know about them. This step runs AFTER
-- 0001 (creates viewer/data_operator/admin) so all 6 roles exist here -
-- reproduces BOTH grants for all of them, matching real Supabase's final
-- state (Supabase's own defaults + migration 0015 combined).
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role, viewer, data_operator, admin;
GRANT EXECUTE ON FUNCTION auth.jwt() TO anon, authenticated, service_role, viewer, data_operator, admin;
