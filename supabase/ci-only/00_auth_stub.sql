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
