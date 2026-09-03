BEGIN;

-- 2026-09-05'te bulunan, git geçmişinde HİÇBİR migration dosyasında
-- OLMAYAN 14 politika kaldırılıyor. Adli inceleme (dokumanlar/
-- 06_adr_dashboard_teknoloji.md, aynı tarihli bölüm) KAYNAĞI KESİN OLARAK
-- belirledi: bu politikalar `db/schema.sql`'in EN İLK taslağından
-- (commit `453a2d4`, "Agent host session aa19b6d3-a4a3-4226-9d42-
-- acb526deab0b - turn 1", 2026-08-19 00:53) geliyor — bu commit `main`
-- dalının ATASI DEĞİL (`git merge-base --is-ancestor` ile doğrulandı),
-- yani aynı oturumun SONRAKİ adımlarında (turn 3, commit `5f7b173`)
-- ÇOKTAN daha güvenli, `current_app_role()`-tabanlı isimlerle
-- DEĞİŞTİRİLMİŞ ve o güvenli hâli `main`'e (PR #6, commit `b674592`)
-- birleştirilmiş. Ama bu ilk taslak, `main`'e hiç girmeden ÖNCE canlı
-- Supabase'e (muhtemelen aynı erken oturumda, doğrudan) UYGULANMIŞ
-- görünüyor — ve `main`'deki güvenli sürüm daha sonra AYRICA uygulanınca
-- (0002_rls_roles.sql — AYNI dosya adı, FARKLI/daha dar içerik) eski,
-- artık kullanılmayan politikalar hiç DROP edilmedi (yeni migration
-- yalnız CREATE POLICY yapar, eskiyi otomatik temizlemez).
--
-- Sonuç: canlı DB'de HEM güvenli (current_app_role() kontrollü) HEM bu
-- eski, KOŞULSUZ `USING (true)` politikalar YAN YANA duruyordu — RLS'te
-- birden fazla PERMISSIVE politika OR'lanır, yani tek bir "her zaman
-- true" politika TÜM diğerlerini ANLAMSIZ kılar. `admin`/`data_operator`
-- rolüne `SET ROLE` yapabilen HERHANGİ bir bağlantı, JWT/`current_app_
-- role()` kontrolünden TAMAMEN bağımsız tam erişime sahipti.
--
-- Bağımsız güvenlik teyidi (2026-09-05): `worker/` ve `app/` içinde
-- `admin`/`data_operator`'a `SET ROLE` yapan HİÇBİR kod yolu YOK (yalnız
-- `worker/validate_role_access.py` `anon`/`viewer`'ı test ediyor,
-- `app/dashboard.py`'deki eşleşmeler yalnız açıklayıcı YORUM METNİ) —
-- yani bu politikaların kaldırılması ŞU AN hiçbir çalışan davranışı
-- BOZMUYOR.
--
-- Her satır AYRI ve AÇIK (wildcard/dinamik silme YOK) — PR diff'inde tek
-- tek gözden geçirilebilir olsun diye.
DROP POLICY IF EXISTS admin_fact_manage ON fact_tuketim;
DROP POLICY IF EXISTS data_operator_fact_manage ON fact_tuketim;
DROP POLICY IF EXISTS admin_uretim_fact_manage ON fact_uretim;
DROP POLICY IF EXISTS data_operator_uretim_fact_manage ON fact_uretim;
DROP POLICY IF EXISTS admin_abone_fact_manage ON fact_abone;
DROP POLICY IF EXISTS data_operator_abone_fact_manage ON fact_abone;
DROP POLICY IF EXISTS admin_serbest_tuketici_fact_manage ON fact_serbest_tuketici;
DROP POLICY IF EXISTS data_operator_serbest_tuketici_fact_manage ON fact_serbest_tuketici;
DROP POLICY IF EXISTS admin_hava_fact_manage ON fact_hava_aylik;
DROP POLICY IF EXISTS data_operator_hava_fact_manage ON fact_hava_aylik;
DROP POLICY IF EXISTS admin_batch_manage ON ingestion_batch;
DROP POLICY IF EXISTS data_operator_batch_manage ON ingestion_batch;
DROP POLICY IF EXISTS admin_source_asset_manage ON source_asset;
DROP POLICY IF EXISTS data_operator_source_asset_manage ON source_asset;

COMMIT;
