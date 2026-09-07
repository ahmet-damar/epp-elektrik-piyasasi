BEGIN;

-- EPP — C4 (2026-09-07 dış denetim): 8 tabloda RLS'i, körlemesine değil
-- gerçek erişim niyetiyle geri açar.
--
-- Durum: 20260904_0002 + 20260904_0004, dim_tarih/dim_il/dim_kaynak/
-- dim_tuketici_grubu/dim_lisans + sistem_parametre/kpi_esik/job_status'ta
-- RLS'i DISABLE etmişti (o turda gerekçe: "policy'siz RLS-açık" deseni
-- SESSİZCE sıfır satır veriyordu — bkz. o migration'ların kendi
-- yorumları). Ama 02_srs_ozet.md'nin P0 kuralı hâlâ "TÜM uygulama
-- tablolarında RLS zorunlu, deny-by-default" diyor — bu 8 tablo bu
-- kuralın istisnasıydı ve İSTİSNA HİÇBİR YERDE karar olarak yazılı
-- değildi. Karar (2026-09-07): istisna KALDIRILIR, RLS geri açılır —
-- kural değişmedi, gerçeklik ona uyduruldu (02_srs_ozet.md'ye dokunulmadı).
--
-- Bu 8 tablo salt referans/config verisi (il/kaynak/tüketici grubu/lisans
-- listeleri, takvim, sistem eşikleri, iş kuyruğu durumu) — SATIR bazlı
-- gizlilik gerektirmiyorlar (fact_*'nin is_active filtresi gibi bir
-- ihtiyaçları yok), ama bu "USING (true) FOR ALL" ile KÖRLEMESİNE
-- geçilebileceği anlamına GELMİYOR: erişim niyeti açıkça iki katmanlı
-- kodlanıyor —
--   SELECT: viewer + data_operator + admin (hepsi aynı referans veriyi
--           görmeli, satır filtresi yok → USING (true) burada GERÇEK
--           niyeti yansıtıyor, formalite değil)
--   INSERT/UPDATE/DELETE: yalnız admin
--
-- job_status'a worker'ın kendi yazması ETKİLENMEZ — worker DATABASE_URL
-- (postgres, service rolü) ile bağlanıyor, RLS'ten muaf (BYPASSRLS).
-- Canlıya uygulamadan ÖNCE disposable postgres:16'da (ci.yml'in
-- integration job'ı) doğrulandı: validate_rls_static.py + yeni bir
-- tamlık kontrolü (worker/validate_role_access.py) + gerçek SET ROLE
-- senaryoları (bkz. dokumanlar/10_TEKNIK_MASTER_DOKUMAN.md §8.1/§8.2).

ALTER TABLE dim_tarih ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_il ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_kaynak ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_tuketici_grubu ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_lisans ENABLE ROW LEVEL SECURITY;
ALTER TABLE sistem_parametre ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_esik ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_status ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS app_roles_dim_tarih_select ON dim_tarih;
DROP POLICY IF EXISTS admin_dim_tarih_all ON dim_tarih;
DROP POLICY IF EXISTS app_roles_dim_il_select ON dim_il;
DROP POLICY IF EXISTS admin_dim_il_all ON dim_il;
DROP POLICY IF EXISTS app_roles_dim_kaynak_select ON dim_kaynak;
DROP POLICY IF EXISTS admin_dim_kaynak_all ON dim_kaynak;
DROP POLICY IF EXISTS app_roles_dim_tuketici_grubu_select ON dim_tuketici_grubu;
DROP POLICY IF EXISTS admin_dim_tuketici_grubu_all ON dim_tuketici_grubu;
DROP POLICY IF EXISTS app_roles_dim_lisans_select ON dim_lisans;
DROP POLICY IF EXISTS admin_dim_lisans_all ON dim_lisans;
DROP POLICY IF EXISTS app_roles_sistem_parametre_select ON sistem_parametre;
DROP POLICY IF EXISTS admin_sistem_parametre_all ON sistem_parametre;
DROP POLICY IF EXISTS app_roles_kpi_esik_select ON kpi_esik;
DROP POLICY IF EXISTS admin_kpi_esik_all ON kpi_esik;
DROP POLICY IF EXISTS app_roles_job_status_select ON job_status;
DROP POLICY IF EXISTS admin_job_status_all ON job_status;

CREATE POLICY app_roles_dim_tarih_select ON dim_tarih
  FOR SELECT TO viewer, data_operator, admin
  USING (true);
CREATE POLICY admin_dim_tarih_all ON dim_tarih
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY app_roles_dim_il_select ON dim_il
  FOR SELECT TO viewer, data_operator, admin
  USING (true);
CREATE POLICY admin_dim_il_all ON dim_il
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY app_roles_dim_kaynak_select ON dim_kaynak
  FOR SELECT TO viewer, data_operator, admin
  USING (true);
CREATE POLICY admin_dim_kaynak_all ON dim_kaynak
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY app_roles_dim_tuketici_grubu_select ON dim_tuketici_grubu
  FOR SELECT TO viewer, data_operator, admin
  USING (true);
CREATE POLICY admin_dim_tuketici_grubu_all ON dim_tuketici_grubu
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY app_roles_dim_lisans_select ON dim_lisans
  FOR SELECT TO viewer, data_operator, admin
  USING (true);
CREATE POLICY admin_dim_lisans_all ON dim_lisans
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY app_roles_sistem_parametre_select ON sistem_parametre
  FOR SELECT TO viewer, data_operator, admin
  USING (true);
CREATE POLICY admin_sistem_parametre_all ON sistem_parametre
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY app_roles_kpi_esik_select ON kpi_esik
  FOR SELECT TO viewer, data_operator, admin
  USING (true);
CREATE POLICY admin_kpi_esik_all ON kpi_esik
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

CREATE POLICY app_roles_job_status_select ON job_status
  FOR SELECT TO viewer, data_operator, admin
  USING (true);
CREATE POLICY admin_job_status_all ON job_status
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

-- admin'in yeni FOR ALL politikalarının GERÇEKTEN kullanılabilir olması
-- için eksik INSERT/UPDATE/DELETE grant'leri (önceden yalnız SELECT
-- vardı — RLS kapalıyken bunlara zaten gerek yoktu). data_operator'a
-- BİLEREK write grant'i eklenmiyor (tasarım: yalnız admin yazar) — bu
-- tabloların bazılarında (job_status/kpi_esik/sistem_parametre)
-- data_operator/authenticated'ın ÖNCEDEN VAR olan INSERT/UPDATE
-- grant'leri kasıtlı olarak dokunulmadan bırakıldı (geri almak ayrı bir
-- karar) — yeni admin-only RLS politikası onları fiilen etkisiz kılıyor
-- (GRANT izin verse de RLS hiçbir satırı geçirmeyecek).
GRANT INSERT, UPDATE, DELETE ON TABLE dim_tarih TO admin;
GRANT INSERT, UPDATE, DELETE ON TABLE dim_il TO admin;
GRANT INSERT, UPDATE, DELETE ON TABLE dim_kaynak TO admin;
GRANT INSERT, UPDATE, DELETE ON TABLE dim_tuketici_grubu TO admin;
GRANT INSERT, UPDATE, DELETE ON TABLE dim_lisans TO admin;
GRANT INSERT, UPDATE, DELETE ON TABLE sistem_parametre TO admin;
GRANT INSERT, UPDATE, DELETE ON TABLE kpi_esik TO admin;
-- job_status: admin zaten DELETE,INSERT,SELECT,UPDATE grant'ine sahipti.

-- worker/validate_rls_static.py deseni: admin'in FOR ALL politikası olan
-- her tabloda authenticated'a da eşdeğer bir DELETE grant'i bekleniyor
-- (bkz. 20260905_0002'nin AYNI deseni).
GRANT DELETE ON TABLE dim_tarih, dim_il, dim_kaynak, dim_tuketici_grubu,
  dim_lisans, sistem_parametre, kpi_esik, job_status TO authenticated;

COMMIT;
