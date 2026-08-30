BEGIN;

-- Canlı Supabase projesinde tespit edildi (CI'ın düz postgres:16'sında görünmez):
-- yeni tablolar oluşturulduğunda Supabase'in proje-seviyesi ALTER DEFAULT
-- PRIVILEGES ayarı, anon rolüne REFERENCES/TRIGGER/TRUNCATE gibi nesne
-- yetkilerini otomatik veriyor. Migration 20260819_0009 bu tabloyu
-- oluşturduğunda migration 20260819_0003'ün "REVOKE ALL ... FROM anon"
-- ifadesi henüz yoktu, bu yüzden fact_hava_aylik_log bu otomatik grant'lardan
-- etkilendi. 0010 yalnızca authenticated/service_role'e GRANT ekledi, anon'u
-- hiç REVOKE etmedi - bu migration o boşluğu kapatıyor.
--
-- anon/authenticated/service_role rolleri yalnız GERÇEK Supabase Postgres'te
-- var (CI'ın düz postgres:16'sında yok) - bu yüzden 0003/0010 ile aynı
-- gerekçeyle CI'ın migration-apply listesine BİLİNÇLİ OLARAK EKLENMEZ.
REVOKE ALL PRIVILEGES ON TABLE fact_hava_aylik_log FROM anon;

COMMIT;
