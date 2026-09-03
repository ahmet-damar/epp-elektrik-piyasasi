BEGIN;

-- Faz B (çok-kullanıcılı giriş) adım 1 doğrulaması sırasında (2026-09-05)
-- bulunan, BAĞIMSIZ ve önceden BİLİNMEYEN bir eksiklik: `20260819_0003_
-- fix_grants.sql`'in "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public
-- FROM viewer, data_operator, admin;" satırı, `20260819_0002_rls_roles.sql`
-- (satır 195-202) tarafından bu üç role verilen TÜM tablo-seviyesi
-- grant'ları (dim_*, source_asset, ingestion_batch, fact_tuketim,
-- fact_uretim, fact_abone, fact_serbest_tuketici, fact_hava_aylik,
-- audit_log) SİLDİ — ve o tarihten (2026-08-19) beri yalnız İKİ dar
-- istisna geri verildi: `veri_kapsam_disi` (0012/0013) ve
-- `fact_hava_aylik_log` (0009, yalnız data_operator/admin). Geri
-- kalan TÜM temel tablolar hâlâ grant'sızdı.
--
-- Bu, RLS politikalarının KENDİSİNİN yanlış olmasından FARKLI bir sorun —
-- PostgreSQL önce GRANT (tablo-seviyesi ACL) kontrol eder, SONRA RLS
-- politikasını uygular; GRANT yoksa RLS'e hiç gelinmeden "permission
-- denied for table" ile durur. `worker/validate_role_access.py`'nin CI
-- testi yalnız `veri_kapsam_disi`'yi test ettiğinden (0012'nin dar
-- grant'ı sayesinde geçiyordu) bu boşluk hiç yakalanmamıştı.
--
-- Bulunma yolu: `app_dashboard_service` (0016) ile canlı Supabase'e
-- bağlanıp `SET ROLE viewer` + `SELECT count(*) FROM fact_tuketim`
-- denendi — SET ROLE artık BAŞARILI (0016'nın çözdüğü sorun), ama sorgu
-- "permission denied for table fact_tuketim" ile reddedildi.
-- `has_table_privilege('viewer','fact_tuketim','SELECT')` = false ve
-- `information_schema.role_table_grants`'ta bu satır hiç yoktu — kanıt.
--
-- Bu migration 0002'nin ORİJİNAL niyetini (satır 195-202) BİREBİR
-- yeniden uygular, yeni bir karar/kapsam DEĞİL.
GRANT SELECT ON TABLE dim_tarih, dim_il, dim_kaynak, dim_tuketici_grubu, dim_lisans
  TO viewer;
GRANT SELECT ON TABLE source_asset, ingestion_batch, fact_tuketim, fact_uretim,
  fact_abone, fact_serbest_tuketici, fact_hava_aylik
  TO viewer;
GRANT SELECT, INSERT, UPDATE ON TABLE source_asset, ingestion_batch
  TO data_operator;
GRANT SELECT, INSERT, UPDATE ON TABLE fact_tuketim, fact_uretim, fact_abone,
  fact_serbest_tuketici, fact_hava_aylik
  TO data_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE source_asset, ingestion_batch
  TO admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_tuketim, fact_uretim, fact_abone,
  fact_serbest_tuketici, fact_hava_aylik
  TO admin;
GRANT SELECT, INSERT ON TABLE audit_log TO admin;

COMMIT;
