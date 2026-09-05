BEGIN;

-- EPP — fact_tuketim_ulke_geneli: EPDK Word raporlarının HER ayında
-- basılan T11 (il×grup) tablosunun KENDİ "Genel Toplam" satırından
-- alınan, il kırılımı OLMAYAN, ülke geneli TÜM tüketici türü (Aydınlatma/
-- Kamu ve Özel Hizmetler/Mesken/Sanayi/Tarımsal) tüketim değerleri.
--
-- Karar 2 (dokumanlar/07_word_parser_kapsam.md) DEĞİŞMEDİ: Sanayi hâlâ
-- fact_tuketim'e (il×grup×baglanti grain'i) YAZILMIYOR, çünkü kaynakta
-- iletim/dağıtım ayrımı yok. Bu tablo AYRI bir amaç için var: Sanayi
-- DAHİL tüm grupların ÜLKE GENELİ (il kırılımsız) serisini KPI-25/27'nin
-- kullanabileceği şekilde hazırlamak (KPI formülü bu turda DEĞİŞTİRİLMEDİ
-- — yalnız veri hazırlığı, bkz. dokumanlar/06_canli_veri_operasyon_
-- gunlugu.md 2026-09-05 kaydı).
--
-- fact_tuketim'den FARKLI: il_kodu/baglanti YOK (grain: tarih_id × grup_id
-- yalnız) — çünkü kaynak (Genel Toplam satırı) zaten il kırılımsız.
--
-- 2026-09-04'teki 4 migration'lık GRANT/RLS dersi (kısmi grant, sonra
-- ayrı "düzeltme" migration'ları) TEKRARLANMIYOR — RLS + policy + GRANT
-- hepsi BU dosyada, fact_tuketim ile BİREBİR AYNI desende.

CREATE TABLE IF NOT EXISTS fact_tuketim_ulke_geneli (
  id BIGSERIAL PRIMARY KEY,
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  grup_id INT NOT NULL REFERENCES dim_tuketici_grubu(grup_id) ON DELETE RESTRICT,
  tuketim_mwh NUMERIC(16,3) NOT NULL CHECK (tuketim_mwh >= 0),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_fact_tuketim_ulke_geneli_batch UNIQUE (tarih_id, grup_id, ingestion_batch_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_tuketim_ulke_geneli_active
  ON fact_tuketim_ulke_geneli (tarih_id, grup_id) WHERE is_active;

ALTER TABLE fact_tuketim_ulke_geneli ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS viewer_fact_tuketim_ulke_geneli_select ON fact_tuketim_ulke_geneli;
DROP POLICY IF EXISTS data_operator_fact_tuketim_ulke_geneli_insert ON fact_tuketim_ulke_geneli;
DROP POLICY IF EXISTS data_operator_fact_tuketim_ulke_geneli_update ON fact_tuketim_ulke_geneli;
DROP POLICY IF EXISTS admin_fact_tuketim_ulke_geneli_all ON fact_tuketim_ulke_geneli;

CREATE POLICY viewer_fact_tuketim_ulke_geneli_select ON fact_tuketim_ulke_geneli
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer' AND is_active = true);

CREATE POLICY data_operator_fact_tuketim_ulke_geneli_insert ON fact_tuketim_ulke_geneli
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY data_operator_fact_tuketim_ulke_geneli_update ON fact_tuketim_ulke_geneli
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY admin_fact_tuketim_ulke_geneli_all ON fact_tuketim_ulke_geneli
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

GRANT SELECT ON TABLE fact_tuketim_ulke_geneli TO viewer;
GRANT SELECT, INSERT, UPDATE ON TABLE fact_tuketim_ulke_geneli TO data_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_tuketim_ulke_geneli TO admin;
-- worker/validate_rls_static.py deseni: admin'in FOR ALL politikası olan
-- her tabloda authenticated'a da eşdeğer bir DELETE grant'i bekleniyor
-- (bkz. 20260819_0003_fix_grants.sql'in AYNI deseni, fact_tuketim vb. için).
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_tuketim_ulke_geneli TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE fact_tuketim_ulke_geneli TO service_role;

-- fact_hava_aylik_log emsali (migration 20260819_0010): bu tablonun
-- BIGSERIAL sırası, 0003_fix_grants.sql'in "ON ALL SEQUENCES IN SCHEMA
-- public" blanket grant'ından SONRA oluşturulduğu için o blanket'e hiç
-- girmedi — authenticated/service_role için AYRICA, açıkça grantlanır.
GRANT USAGE, SELECT ON SEQUENCE fact_tuketim_ulke_geneli_id_seq TO authenticated, service_role;

-- migration 20260819_0013 emsali: Supabase'in proje-seviyesi ALTER
-- DEFAULT PRIVILEGES ayarı REFERENCES/TRIGGER/TRUNCATE gibi nesne
-- yetkilerini anon'a otomatik verebiliyor (20260819_0011'de fact_hava_
-- aylik_log için bulunan davranış) - burada da aynı önlem alınıyor.
REVOKE ALL ON TABLE fact_tuketim_ulke_geneli FROM anon;

COMMIT;
