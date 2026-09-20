BEGIN;

-- EPP — Toplama katmanı (agregasyon), 2026-09-19/20
-- (`Claude outputs/PROMPT_TOPLAMA_KATMANI_2026-09-19.md`).
--
-- Amaç: dashboard'un bugün TEK AY üzerinden çalışan grafiklerini çeyreklik/
-- yıllık/uzun-dönem görülebilir kılmak. Bu migration YALNIZ VERİ KATMANI
-- (view + index) — çözünürlük(ay/çeyrek/yıl)+aralık mantığı, R12, kapsam
-- bayrağı, oran hesapları `worker/toplama.py`'de (SQL'de, view'lerin
-- ÜZERİNE kurulu). UI YOK (ayrı tur).
--
-- **DÜZ VIEW, MATERIALIZED DEĞİL** (kullanıcı kararı, gerekçe: `is_active`
-- aktivasyonuyla refresh bağımlılığı doğar — de-kümülatif işinde yaşanan
-- hatanın, bkz. migration 20260908_0002, TEKRARI olurdu). Gerçekten yavaşsa
-- materialize etmek AYRI bir karar, bu turda ÖLÇÜLDÜ (bkz. kapanış raporu),
-- gerek görülmedi.
--
-- **security_invoker = true ZORUNLU** (PG15+): view'ler varsayılan olarak
-- SAHİBİNİN (migration'ı uygulayan rol, örn. `postgres` — Supabase'de
-- genelde BYPASSRLS) yetkisiyle çalışır, ÇAĞIRANIN DEĞİL — bu, `fact_*`
-- tablolarındaki `current_app_role()` tabanlı RLS politikalarının (bkz.
-- migration 20260905_0002/20260909_0001) view üzerinden SESSİZCE
-- ATLANMASI demek olurdu (viewer rolü is_active dışı satırları da görürdü).
-- `security_invoker=true` RLS'i ÇAĞIRANIN rolüyle değerlendirir — established
-- desenle (fact_* tablolarının kendisi) TUTARLI davranış.
--
-- Kapsam (bu turda): fact_tuketim, fact_tuketim_ulke_geneli,
-- fact_uretim_kaynak_geneli, fact_uretim_il_geneli. fact_hava_aylik ve
-- KPI'lar DIŞARIDA (önce temel toplama doğru olsun).
--
-- Tasarım: her view AYLIK (grain='ay') düzeyde, is_active=true satırları
-- dim_tarih/dim_* ile join'leyip GEREKTİĞİNDE il_kodu üzerinden ÜLKE
-- GENELİNE toplar (bu katmanın amacı çeyreklik/yıllık TREND, il haritası
-- DEĞİL — established `mutabakat_uretim.py`'nin kaynak_geneli/il_geneli
-- ülke-toplamı karşılaştırma deseniyle TUTARLI). `il_sayisi` kolonu
-- (COUNT DISTINCT il_kodu) il kırılımlı iki tabloda (fact_tuketim,
-- fact_uretim_il_geneli) KORUNUR — `worker/toplama.py`'nin il kardinalite
-- kontrolü (2023-01/02 deprem: 79/81 il) bunu kullanır.
--
-- ⚠️ `fact_tuketim_ulke_geneli.kumulatif_tuketim_mwh` BİLEREK dışarıda
-- bırakıldı — yalnız `tuketim_mwh` (zaten de-kümülatif edilmiş aylık
-- değer) expose edilir, kümülatif kolonun YANLIŞLIKLA toplanması bu view
-- seviyesinde YAPISAL OLARAK imkânsız (kolon hiç seçilmiyor).

CREATE INDEX IF NOT EXISTS idx_fact_tuketim_tarih_active
  ON fact_tuketim (tarih_id) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_fact_tuketim_ulke_geneli_tarih_active
  ON fact_tuketim_ulke_geneli (tarih_id) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_fact_uretim_kaynak_geneli_tarih_active
  ON fact_uretim_kaynak_geneli (tarih_id) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_fact_uretim_il_geneli_tarih_active
  ON fact_uretim_il_geneli (tarih_id) WHERE is_active;

CREATE OR REPLACE VIEW vw_toplama_tuketim_aylik
  WITH (security_invoker = true) AS
SELECT
  t.tarih_id, d.yil, d.ay, d.ceyrek,
  t.grup_id, g.grup_adi,
  SUM(t.tuketim_mwh) AS tuketim_mwh,
  COUNT(DISTINCT t.il_kodu) AS il_sayisi
FROM fact_tuketim t
JOIN dim_tarih d ON d.tarih_id = t.tarih_id
JOIN dim_tuketici_grubu g ON g.grup_id = t.grup_id
WHERE t.is_active
GROUP BY t.tarih_id, d.yil, d.ay, d.ceyrek, t.grup_id, g.grup_adi;

CREATE OR REPLACE VIEW vw_toplama_tuketim_ulke_geneli_aylik
  WITH (security_invoker = true) AS
SELECT
  u.tarih_id, d.yil, d.ay, d.ceyrek,
  u.grup_id, g.grup_adi,
  u.tuketim_mwh
FROM fact_tuketim_ulke_geneli u
JOIN dim_tarih d ON d.tarih_id = u.tarih_id
JOIN dim_tuketici_grubu g ON g.grup_id = u.grup_id
WHERE u.is_active;

CREATE OR REPLACE VIEW vw_toplama_uretim_kaynak_aylik
  WITH (security_invoker = true) AS
SELECT
  k.tarih_id, d.yil, d.ay, d.ceyrek,
  k.kaynak_id, dk.kaynak_adi, dk.yenilenebilir_mi,
  k.lisans_id, dl.tur AS lisans_turu,
  k.uretim_mwh
FROM fact_uretim_kaynak_geneli k
JOIN dim_tarih d ON d.tarih_id = k.tarih_id
JOIN dim_kaynak dk ON dk.kaynak_id = k.kaynak_id
JOIN dim_lisans dl ON dl.lisans_id = k.lisans_id
WHERE k.is_active;

CREATE OR REPLACE VIEW vw_toplama_uretim_il_aylik
  WITH (security_invoker = true) AS
SELECT
  i.tarih_id, d.yil, d.ay, d.ceyrek,
  i.lisans_id, dl.tur AS lisans_turu,
  SUM(i.uretim_mwh) AS uretim_mwh,
  COUNT(DISTINCT i.il_kodu) AS il_sayisi
FROM fact_uretim_il_geneli i
JOIN dim_tarih d ON d.tarih_id = i.tarih_id
JOIN dim_lisans dl ON dl.lisans_id = i.lisans_id
WHERE i.is_active
GROUP BY i.tarih_id, d.yil, d.ay, d.ceyrek, i.lisans_id, dl.tur;

-- View'lerin kendi GRANT'i ayrıca gerekir (alttaki tablo grant'ini
-- DEVRALMAZ) — fact_* tablolarıyla BİREBİR AYNI rol seti.
GRANT SELECT ON vw_toplama_tuketim_aylik, vw_toplama_tuketim_ulke_geneli_aylik,
  vw_toplama_uretim_kaynak_aylik, vw_toplama_uretim_il_aylik
  TO viewer, data_operator, admin, authenticated, service_role;

COMMIT;
