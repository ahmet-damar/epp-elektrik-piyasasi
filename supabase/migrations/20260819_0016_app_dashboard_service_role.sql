BEGIN;

-- Faz B (çok-kullanıcılı giriş) adım 1: dashboard bağlantısı için dar
-- yetkili özel bir servis rolü. dokumanlar/06_adr_dashboard_teknoloji.md
-- (2026-09-05, "RLS notu, KESİN KÖK NEDEN bulundu") — canlı Supabase'de
-- `postgres` GERÇEK bir superuser DEĞİL, ve `viewer`/`data_operator`/
-- `admin`'e üyeliği PG16+'nın ayrık `SET` yetkisini (pg_auth_members.
-- set_option) TAŞIMIYOR — bu yüzden `SET ROLE viewer` "permission denied"
-- ile reddediliyordu. Çözüm iki parçalı: (1) panel bağlantısı `postgres`
-- YERİNE bu dar-yetkili role geçecek (Faz B'nin sonraki adımı, henüz
-- BAĞLANMADI — bkz. app/dashboard.py'nin bu migration'la AYRI commit'i),
-- (2) bu role SET yetkisi AÇIKÇA verilir.
--
-- ŞİFRE BU DOSYADA YOK — migration'lar repoya commit'lenir, gizli bilgi
-- git geçmişine ASLA girmemeli. Şifre canlıya (ve varsa CI/staging'e)
-- migration DIŞINDA, doğrudan `ALTER ROLE ... PASSWORD ...` ile ayrıca
-- verilir (bkz. dokumanlar/06 aynı bölüm — "ADIM 2").
CREATE ROLE app_dashboard_service WITH LOGIN;

-- WITH INHERIT FALSE (AÇIKÇA belirtildi, PG'nin "grantee'nin kendi
-- rolinherit'ini miras al" varsayılanına GÜVENİLMEDİ): app_dashboard_
-- service varsayılan olarak viewer/data_operator/admin'in HİÇBİR
-- ayrıcalığını taşımaz — yalnız açıkça `SET ROLE <rol>` yapıldığında o
-- rolün ayrıcalıklarını kazanır. Amaç: bağlantı KENDİ BAŞINA (SET ROLE
-- öncesi) fact tablolarına hiç erişemesin, en az ayrıcalık ilkesi.
--
-- WITH SET TRUE: PG16+'nın ayrık SET yetkisi — `SET ROLE`/`SET SESSION
-- AUTHORIZATION`'ın ÇALIŞABİLMESİ için üyelik (admin_option) tek başına
-- YETMEZ, bu yetkinin AÇIKÇA verilmesi gerekir (bkz. `postgres` rolünün
-- üyeliğinde bu YOKTU — kök nedenin kendisi). Syntax PostgreSQL 16, 17
-- (canlı Supabase'in sürümü, `SHOW server_version` ile doğrulandı) VE
-- CI'nin postgres:16 servisinde AYNI şekilde geçerli (PG16'da tanıtıldı,
-- `GRANT role TO grantee WITH { ADMIN | INHERIT | SET } { TRUE | FALSE }`).
GRANT viewer, data_operator, admin
  TO app_dashboard_service
  WITH INHERIT FALSE, SET TRUE;

COMMIT;
