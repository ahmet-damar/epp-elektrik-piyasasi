BEGIN;

-- EPP — 2026-11-10 bulgusu (Batman/Tarımsal + Bartın/Kamu ve Özel
-- Hizmetler, bkz. Claude outputs/kapanis_2026-11-10_altyapi_ve_dashboard.md
-- ve dokumanlar/09_PROJE_DURUMU.md madde 15): `worker/ingest.py`'nin
-- fact_*_yukle() fonksiyonları bir satırı `tuketim_mwh IS NULL` diye
-- atladığında eskiden yalnız bir SAYAÇ (ingestion_batch.rejected_row_count)
-- artıyordu — HANGİ (il, dönem, grup) satırının NEDEN atlandığı hiçbir
-- yerde kalmıyordu. Bu tablo o boşluğu kapatır: her atlanan hücre için
-- yapılandırılmış, teşhis edilebilir bir kayıt.
--
-- `veri_kapsam_disi` (migration 20260819_0012) ile KARIŞTIRILMASIN — o
-- tablo GÜNCEL bir "durum" kaydıdır (aynı anahtar için UPSERT), bu tablo
-- ise append-only bir DENEME günlüğüdür (aynı hücre farklı batch'lerde
-- tekrar tekrar boş çıkarsa her biri ayrı satır olarak kalır — "bu hücre
-- kaç kez, hangi batch'lerde boş çıktı" sorusu burada cevaplanır).
-- `ham_sinif='bos_hucre'` olan satırlar AYRICA `kapsam_disi_isaretle()`
-- ile `veri_kapsam_disi`'ye yansıtılır (worker/ingest.py:
-- fact_tuketim_yukle()) — "beklenmeyen_icerik" YANSITILMAZ, o gerçek bir
-- sorun olarak görünür kalmalı.
CREATE TABLE IF NOT EXISTS atlanan_hucre (
  id BIGSERIAL PRIMARY KEY,
  -- worker/ingest.py:_DOGAL_ANAHTAR'ın orijinal 4'lü whitelist'iyle AYNI
  -- (veri_kapsam_disi'nin de kullandığı) - bugün yalnız 'fact_tuketim'
  -- yazıyor, diğer üçü aynı deseni izlemek isteyecek gelecekteki
  -- loader'lar için şema değişikliği gerektirmesin diye burada.
  fact_tablosu TEXT NOT NULL CHECK (
    fact_tablosu IN ('fact_tuketim', 'fact_uretim', 'fact_abone', 'fact_serbest_tuketici')
  ),
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id) ON DELETE RESTRICT,
  -- il_kodu/grup_id NULLABLE: her fact tablosunda ikisi de yok (örn.
  -- fact_tuketim_ulke_geneli'nde il_kodu hiç yok).
  il_kodu INT REFERENCES dim_il(il_kodu) ON DELETE RESTRICT,
  grup_id INT REFERENCES dim_tuketici_grubu(grup_id) ON DELETE RESTRICT,
  baglanti TEXT,
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id) ON DELETE RESTRICT,
  -- worker/parser.py:parse_sayi_sinifli() ile AYNI üç değer. 'bilinmiyor'
  -- bugün yalnız Word-yılları (2016-2025) yolundan geliyor - o parser'lar
  -- henüz sınıf/ham_metin taşımıyor (bu turda kapsam dışı), eski
  -- davranışla (yalnız sayaç) aynı bilgi düzeyinde kalır.
  ham_sinif TEXT NOT NULL CHECK (
    ham_sinif IN ('bos_hucre', 'beklenmeyen_icerik', 'bilinmiyor')
  ),
  ham_metin TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_atlanan_hucre_batch ON atlanan_hucre (ingestion_batch_id);
CREATE INDEX IF NOT EXISTS idx_atlanan_hucre_tarih_tablo ON atlanan_hucre (tarih_id, fact_tablosu);

ALTER TABLE atlanan_hucre ENABLE ROW LEVEL SECURITY;

-- veri_kapsam_disi'nin desenini izler, UPDATE politikası YOK: bu tablo
-- append-only bir günlük, var olan bir satırı güncellemek hiç gerekmez
-- (kapsam_disi_isaretle()'ın "durum" UPSERT'inin AKSİNE).
CREATE POLICY viewer_atlanan_hucre_select ON atlanan_hucre
  FOR SELECT TO viewer
  USING (public.current_app_role() = 'viewer');

CREATE POLICY data_operator_atlanan_hucre_insert ON atlanan_hucre
  FOR INSERT TO data_operator
  WITH CHECK (public.current_app_role() = 'data_operator');

CREATE POLICY admin_atlanan_hucre_all ON atlanan_hucre
  FOR ALL TO admin
  USING (public.current_app_role() = 'admin')
  WITH CHECK (public.current_app_role() = 'admin');

GRANT SELECT ON TABLE atlanan_hucre TO viewer;
GRANT SELECT, INSERT ON TABLE atlanan_hucre TO data_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE atlanan_hucre TO admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE atlanan_hucre TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE atlanan_hucre TO service_role;
GRANT USAGE, SELECT ON SEQUENCE atlanan_hucre_id_seq TO authenticated, service_role;
REVOKE ALL ON TABLE atlanan_hucre FROM anon;

COMMIT;
