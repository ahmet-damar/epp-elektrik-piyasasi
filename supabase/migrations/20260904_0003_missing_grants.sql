BEGIN;

-- Üçüncü GRANT düzeltmesi (bkz. 20260904_0001/0002). Kök neden: `public`
-- şemasındaki 18 tablonun TAMAMI `information_schema.role_table_grants`
-- ile tek tek tarandı, `20260819_0002_rls_roles.sql`'in (ve onu geri
-- yükleyen 0017'nin) kapsadığı listeyle karşılaştırıldı. 3 tablo
-- `viewer`/`data_operator`/`admin`'in HİÇBİRİNDEN grant almamış:
--
-- 1) `sistem_parametre` — salt-okunur (worker/analytics.py:
--    sistem_parametre_getir(), app/dashboard.py'nin OD-1 baz sıcaklık
--    okuması). Hiçbir worker kodu bu tabloya YAZMIYOR. `20260819_0003_
--    fix_grants.sql`, bu tabloya yalnız Supabase'in kendi `authenticated`
--    rolüne (bu projenin FİİLEN kullanmadığı, ADR'de "ölü yol" olarak
--    belgelenen ayrı bir mekanizma) SELECT/INSERT/UPDATE vermiş —
--    `viewer`/`data_operator`/`admin` hiç almamıştı.
-- 2) `kpi_esik` — şu an hiçbir Python kodunda (worker/ ya da app/) okunmuyor
--    ya da yazılmıyor (repo genelinde tarandı, yalnız migration/şema
--    tanımında geçiyor). `sistem_parametre` ile AYNI eksiklik (0003'te
--    yalnız `authenticated`e verilmiş) — ileride kullanılmaya
--    başlanırsa sürpriz olmasın diye, dim_*/sistem_parametre ile AYNI
--    "salt-okunur referans tablosu" muamelesiyle şimdiden SELECT
--    veriliyor.
-- 3) `job_status` — `worker/ingest.py` (satır 660: INSERT, 680/688/714/
--    733/740: UPDATE) ve `worker/job_worker.py`'nin yazdığı asenkron iş
--    kuyruğu. `ingestion_batch`/`source_asset` ile BİREBİR AYNI
--    operasyonel kategori (pipeline'ın kendi durum takibi) — 0002/0017'nin
--    o tablolara uyguladığı AYNI desen burada da uygulanıyor: `viewer`
--    salt-okunur görebilir, `data_operator` INSERT/UPDATE yapabilir,
--    `admin` ayrıca DELETE (elle temizlik, bkz. word_2024.py'nin mükerrer
--    batch temizliği emsali) yapabilir.
GRANT SELECT ON TABLE sistem_parametre, kpi_esik, job_status TO viewer;
GRANT SELECT ON TABLE sistem_parametre, kpi_esik TO data_operator, admin;
GRANT SELECT, INSERT, UPDATE ON TABLE job_status TO data_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE job_status TO admin;

COMMIT;
