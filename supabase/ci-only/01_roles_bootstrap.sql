-- EPP — CI-only Supabase role bootstrap. NOT a real migration — never
-- apply to Supabase (staging/prod already provides these roles; this file
-- is intentionally kept OUTSIDE supabase/migrations/ so deploy.yml's
-- `supabase/migrations/*.sql` glob never picks it up, same convention as
-- 00_auth_stub.sql in this directory).
--
-- Why this exists: `supabase start` (Supabase CLI, local dev) creates a
-- minimal role set on a fresh Postgres cluster BEFORE any project
-- migration runs. Real Supabase (staging/prod) already has these roles.
-- CI's plain `postgres:16` service has neither — so any migration that
-- GRANTs/REVOKEs against anon/authenticated/service_role fails with
-- "role ... does not exist". Until 2026-09-02 this was worked around by
-- EXCLUDING those migrations (0003, 0010, 0011, 0013) from CI's apply
-- list entirely — meaning they were NEVER actually validated in CI. This
-- file removes that workaround permanently: bootstrap the roles here,
-- apply ALL migrations in CI, same as production.
--
-- Scanned all of supabase/migrations/ for anon/authenticated/service_role
-- references (2026-09-02): every subsequent statement is a GRANT/REVOKE
-- (0003, 0010, 0011, 0013) or a GRANT EXECUTE (0003, current_app_role()).
-- REVOKE of a privilege a role never held is a no-op in Postgres (not an
-- error), and GRANT only requires the grantee role to EXIST — so once
-- these 3 roles exist, every one of those statements applies cleanly.
-- No sequence/function-level pre-grant is needed beyond schema USAGE
-- (0003 immediately re-tightens USAGE itself: REVOKEs it from anon,
-- GRANTs it to authenticated/service_role — this bootstrap's blanket
-- GRANT below is just the same kind of permissive starting point
-- `supabase start` itself sets up, which project migrations then narrow).

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOLOGIN NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOLOGIN NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role NOLOGIN NOINHERIT BYPASSRLS;
  END IF;
END $$;

GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
