BEGIN;

-- 20260904_0003'ün GRANT düzeltmesi sonrası bulundu: sistem_parametre/
-- kpi_esik/job_status, dim_*'in 20260904_0002'de düzeltilen AYNI hatasını
-- taşıyor — `relrowsecurity=true` ama `pg_policies`'te SIFIR kayıt.
-- Kapsamlı bir tarama (public şemasındaki 18 tablonun TAMAMI,
-- `relrowsecurity` + policy sayısı karşılaştırıldı) bu deseni yalnız bu
-- 3 tabloda buldu — dim_* (0002'de zaten düzeltildi) dışında başka etkilenen
-- tablo YOK, fact_*/source_asset/ingestion_batch/audit_log/veri_kapsam_disi
-- hepsinin GERÇEK policy'leri var (4'er/2, 20260819_0002'de tanımlı).
--
-- GRANT (0003) SELECT'i mümkün kıldı ama RLS+policy'siz tablo varsayılan
-- olarak "hepsini reddet" davranışında kalmaya devam ediyordu — owner/
-- BYPASSRLS dışı her rol (admin dahil) sorguda hata almadan SESSİZCE
-- sıfır satır görüyordu (dim_tarih ile birebir aynı belirti:
-- sistem_parametre_getir() {} döndürdü, gerçekte 4 satır var).
--
-- Bu 3 tablo da (sistem_parametre/kpi_esik: salt referans/eşik verisi;
-- job_status: pipeline'ın kendi iç durum takibi) satır bazlı gizlilik
-- gerektirmiyor — hiçbiri 20260819_0001/0002'nin ENABLE ROW LEVEL
-- SECURITY listesinde hiç yoktu (dim_* ile aynı, muhtemelen migration
-- dışında/Dashboard linter'ından sonradan açılmış). Erişim GRANT ile
-- kontrol ediliyor (0003).
ALTER TABLE sistem_parametre DISABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_esik DISABLE ROW LEVEL SECURITY;
ALTER TABLE job_status DISABLE ROW LEVEL SECURITY;

COMMIT;
