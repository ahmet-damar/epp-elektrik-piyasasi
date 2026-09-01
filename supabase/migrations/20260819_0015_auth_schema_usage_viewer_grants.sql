BEGIN;

-- Gerçek bir izin boşluğu, migration 20260819_0014'ün EXECUTE düzeltmesiyle
-- AYNI kökten: Supabase'in kendi `auth` şeması yalnız KENDİ yönettiği
-- rollere (anon/authenticated/service_role) USAGE veriyor — bu projenin
-- ÖZEL rolleri (viewer/data_operator/admin, migration 0001'de yaratıldı)
-- Supabase'in kurulumu SIRASINDA henüz yoktu, o yüzden hiç USAGE almadılar.
-- Sonuç: current_app_role() (0014'ten sonra EXECUTE edilebiliyor) İÇİNDEKİ
-- auth.jwt() çağrısı bu 3 rol için "permission denied for schema auth"
-- ile patlıyordu — kendi RLS politikalarının gerektirdiği fonksiyon
-- zincirini hiçbiri uçtan uca çalıştıramıyordu.
--
-- 2026-09-02'de worker/validate_role_access.py'nin CI'da (gerçek SET ROLE
-- ile) çalıştırılmasıyla bulundu, canlı Supabase'de de
-- has_schema_privilege() ile doğrulandı (viewer/data_operator/admin=false,
-- anon/authenticated/service_role=true) — CI'a özgü DEĞİL, gerçek prod'da
-- da mevcuttu.
GRANT USAGE ON SCHEMA auth TO viewer, data_operator, admin;

COMMIT;
