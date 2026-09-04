BEGIN;

-- Kök neden: `20260819_0002_rls_roles.sql` (satır 196) dim_* tablolarına
-- (dim_tarih, dim_il, dim_kaynak, dim_tuketici_grubu, dim_lisans) yalnız
-- `viewer`'a GRANT SELECT vermişti — `data_operator`/`admin` bu tablolara
-- HİÇ grant almadı (0002'nin kendi orijinal hatası, `0017_restore_viewer_
-- data_operator_admin_table_grants.sql`'in geri yüklediği liste de bunu
-- BİREBİR tekrarladı, dim_* için data_operator/admin'i yine atladı).
-- Sonuç: `admin` rolüyle bağlanan sorgular (örn. `worker/analytics.py:
-- donemler_getir()`, önce `dim_tarih`'e bakıyor) "permission denied for
-- table dim_tarih" ile reddediliyordu — RLS politikasından ÖNCE, tablo
-- seviyesi ACL kontrolünde duruyordu (bkz. 0017'nin aynı sınıf bulgusu).
-- Canlı DB'de doğrulandı: data_operator/admin'in dim_* tablolarında
-- HİÇBİR satırı yoktu (`information_schema.role_table_grants`).
GRANT SELECT ON TABLE dim_tarih, dim_il, dim_kaynak, dim_tuketici_grubu, dim_lisans
  TO data_operator, admin;

COMMIT;
