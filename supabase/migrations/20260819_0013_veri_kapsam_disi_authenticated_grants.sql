BEGIN;

-- admin_veri_kapsam_disi_all (0012) FOR ALL politikasıyla, diğer
-- operasyonel tablolarla (0003_fix_grants.sql - source_asset/fact_*) AYNI
-- desende: admin FOR ALL politikası olan her tabloda authenticated'a da
-- DELETE dahil tam erişim, service_role'e de tam erişim verilir
-- (worker/validate_rls_static.py bunu statik olarak doğruluyor — bkz. o
-- dosyanın "admin policies have corresponding authenticated DELETE
-- grants" bölümü). Bu iki rol yalnız GERÇEK Supabase Postgres'te var —
-- 0003 ile AYNI gerekçeyle, bu migration CI'ın apply listesine BİLİNÇLİ
-- OLARAK EKLENMEZ (bkz. .github/workflows/ci.yml).
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE veri_kapsam_disi TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE veri_kapsam_disi TO service_role;

COMMIT;
