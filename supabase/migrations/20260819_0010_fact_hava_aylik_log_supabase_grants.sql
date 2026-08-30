BEGIN;

-- Supabase-yönetimli roller (authenticated, service_role) için grant'lar -
-- migration 20260819_0003_fix_grants.sql ile AYNI gerekçeyle bilinçli olarak
-- ayrı bir dosyada: bu roller yalnız GERÇEK Supabase Postgres'te var, CI'ın
-- düz postgres:16 servisinde YOK ("role does not exist" hatası verir) - bu
-- yüzden CI'ın migration-apply listesine (bkz. .github/workflows/ci.yml)
-- BİLİNÇLİ OLARAK EKLENMEZ (0003 de aynı şekilde atlanır).
--
-- migration 0003 zaten uygulanmış (immutable) - fact_hava_aylik_log o zaman
-- yoktu, bu yüzden yeni tabloyu 0003'e eklemek yerine ayrı bir migration.
GRANT SELECT, INSERT ON TABLE fact_hava_aylik_log TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE fact_hava_aylik_log_log_id_seq TO authenticated, service_role;

COMMIT;
