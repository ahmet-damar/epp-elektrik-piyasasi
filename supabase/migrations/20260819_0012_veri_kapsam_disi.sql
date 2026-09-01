BEGIN;

-- Karar 1 (dokumanlar/07_word_parser_kapsam.md, T13/fact_serbest_tuketici)
-- ve Karar 3 (T1/fact_uretim Lisanslı) her ikisi de "kaynakta gerçekten
-- yok" durumunun "parser hatası yüzünden 0 satır" durumundan KPI/dashboard
-- seviyesinde her zaman ayırt edilebilmesini gerektiriyordu — mekanizma o
-- kararlarda "uygulama turunda seçilecek" olarak bırakılmıştı, bu migration
-- onu seçiyor: ingestion_batch/source_asset'ten BAĞIMSIZ, tablo+dönem+
-- nitelik bazında sorgulanabilir bir "bu neden yok" kaydı. Bilinçli olarak
-- batch'e BAĞLANMIYOR (ingestion_batch_id yok) — bir dönem için o fact
-- tablosunda HİÇBİR batch/veri girişimi bile olmayabilir (Word kaynağında
-- T13/T1 hiç aranmıyor bile), bu yüzden "batch'e iliştirilmiş bir not"
-- değil, kendi başına bir gerçek.
CREATE TABLE IF NOT EXISTS veri_kapsam_disi (
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  -- worker/ingest.py:_DOGAL_ANAHTAR ile aynı whitelist (aktivasyon_yap()'ın
  -- kullandığı 4 fact tablosu) - serbest metin DEĞİL, keyfi bir tablo adı
  -- buraya yazılamaz.
  fact_tablosu TEXT NOT NULL CHECK (
    fact_tablosu IN ('fact_tuketim', 'fact_uretim', 'fact_abone', 'fact_serbest_tuketici')
  ),
  -- Aynı fact tablosunun İÇİNDE bile kısmi kapsam dışılık olabilir (örn.
  -- fact_uretim'in yalnız Lisanslı kesiti Word'de yok, Lisanssız VAR -
  -- Karar 3). '(tumu)' = tüm tablo bu dönem için kapsam dışı (örn. Karar 1,
  -- fact_serbest_tuketici).
  nitelik TEXT NOT NULL DEFAULT '(tumu)',
  sebep TEXT NOT NULL,
  -- Serbest metin (dokumanlar/07_word_parser_kapsam.md'deki karar
  -- başlıklarıyla aynı sözcükler - 'Karar 1', 'Karar 3' vb.) - CHECK ile
  -- sabit bir listeye kilitlemek, yeni bir karar eklendiğinde bu migration'a
  -- geri dönüp ALTER gerektirir; şimdilik gerekli görülmedi.
  karar_referansi TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tarih_id, fact_tablosu, nitelik)
);

CREATE INDEX IF NOT EXISTS idx_veri_kapsam_disi_fact_tablosu ON veri_kapsam_disi (fact_tablosu);

ALTER TABLE veri_kapsam_disi ENABLE ROW LEVEL SECURITY;

-- Diğer fact_*_select politikalarıyla aynı desen (bkz. db/schema.sql) -
-- is_active filtresi YOK, bu tabloda öyle bir kolon yok (her satır zaten
-- "geçerli" bir kapsam-dışı kaydı).
CREATE POLICY viewer_veri_kapsam_disi_select ON veri_kapsam_disi
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer');

CREATE POLICY data_operator_veri_kapsam_disi_insert ON veri_kapsam_disi
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

-- UPDATE gerekli: kapsam_disi_isaretle() (worker/pipeline.py) ayni
-- (tarih_id, fact_tablosu, nitelik) icin ikinci kez cagrilirsa UPSERT
-- yapar (ON CONFLICT DO UPDATE) - sebep/karar_referansi metni
-- guncellenebilsin diye, hata firlatmak yerine.
CREATE POLICY data_operator_veri_kapsam_disi_update ON veri_kapsam_disi
  FOR UPDATE TO data_operator
  USING (public.current_app_role() = 'data_operator')
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY admin_veri_kapsam_disi_all ON veri_kapsam_disi
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

GRANT SELECT ON TABLE veri_kapsam_disi TO viewer;
GRANT SELECT, INSERT, UPDATE ON TABLE veri_kapsam_disi TO data_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE veri_kapsam_disi TO admin;
REVOKE ALL ON TABLE veri_kapsam_disi FROM anon, authenticated;

COMMIT;
