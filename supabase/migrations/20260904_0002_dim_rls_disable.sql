BEGIN;

-- Kök neden: dim_tarih/dim_il/dim_kaynak/dim_tuketici_grubu/dim_lisans
-- hiçbir migration'da hiç RLS kapsamına alınmadı (20260819_0001/0002'nin
-- `ENABLE ROW LEVEL SECURITY` listesinde dim_* YOK — yalnız source_asset/
-- ingestion_batch/fact_*/audit_log var). Ama canlı DB'de bu 5 tablonun
-- `relrowsecurity=true` olduğu doğrulandı (muhtemelen migration DIŞINDA,
-- örn. Supabase Dashboard'un "Enable RLS" linter uyarısından sonradan
-- açılmış). RLS açık + hiç policy tanımlı olmayınca PostgreSQL varsayılanı
-- "hepsini reddet" — owner/BYPASSRLS dışındaki HER rol (admin dahil,
-- viewer dahil) SESSİZCE sıfır satır görüyordu (hata yok, boş sonuç).
--
-- Bu tablolar salt referans/boyut (dimension) verisi — il listesi, kaynak
-- türleri, tüketici grupları, lisans türleri, takvim. Satır bazlı gizlilik
-- gerektiren bir yapıları yok (fact_*'nin aksine, orada RLS is_active +
-- rol bazlı erişim için gerçekten kullanılıyor). Erişim kontrolü zaten
-- GRANT (20260819_0002 + bugünkü 20260904_0001) ile sağlanıyor — RLS bu
-- tablolar için YANLIŞLIKLA açılmış fazladan bir katman, 20260819_0002'nin
-- ORİJİNAL tasarımıyla (dim_* hiç RLS kapsamında değildi) tutarlı hale
-- getiriliyor.
ALTER TABLE dim_tarih DISABLE ROW LEVEL SECURITY;
ALTER TABLE dim_il DISABLE ROW LEVEL SECURITY;
ALTER TABLE dim_kaynak DISABLE ROW LEVEL SECURITY;
ALTER TABLE dim_tuketici_grubu DISABLE ROW LEVEL SECURITY;
ALTER TABLE dim_lisans DISABLE ROW LEVEL SECURITY;

COMMIT;
