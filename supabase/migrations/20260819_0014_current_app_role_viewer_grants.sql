BEGIN;

-- Gerçek bir izin boşluğu: 0003_fix_grants.sql, public.current_app_role()
-- fonksiyonuna YALNIZ authenticated/service_role'e EXECUTE verdi -
-- viewer/data_operator/admin'e HİÇ vermedi. Ama RLS politikaları AÇIKÇA
-- "TO viewer"/"TO data_operator"/"TO admin" (bkz. db/schema.sql,
-- 0002_rls_roles.sql) ve HER BİRİ USING (public.current_app_role() = ...)
-- çağırıyor — yani bağlantı GERÇEKTEN bu rollerden birine SET ROLE
-- yapıldığında (tasarımın öngördüğü senaryo), kendi politikasının
-- gerektirdiği fonksiyonu bile ÇAĞIRAMIYORDU: "permission denied for
-- function current_app_role".
--
-- 2026-09-02'de worker/validate_role_access.py'nin CI'da (gerçek SET ROLE
-- ile) çalıştırılmasıyla bulundu - CI'a özgü DEĞİL, aynı 0003 gerçek
-- Supabase'de de uygulı olduğundan orada da mevcuttu (bkz.
-- dokumanlar/06_canli_veri_operasyon_gunlugu.md).
GRANT EXECUTE ON FUNCTION public.current_app_role() TO viewer, data_operator, admin;

COMMIT;
