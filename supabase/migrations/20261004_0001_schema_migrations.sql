BEGIN;

-- EPP — schema_migrations: hangi migration canlıya UYGULANDI kaydı (2026-10-04,
-- `Claude outputs/PROMPT_MIGRATION_CANLI_2026-10-04.md`).
--
-- Neden gerekti: 20260920_0001_toplama_katmani_views.sql disposable'da
-- doğrulanıp canlıya HİÇ UYGULANMADI, ve bunu fark edecek hiçbir mekanizma
-- yoktu. Kök sebep, bu migration'ın kendisinden de daha temel: `deploy.yml`
-- `migrate` job'ı `build-push`'a `needs` ile bağlı, o da `if: false` ile
-- KALICI OLARAK devre dışı (web/worker Dockerfile'ları henüz yok) — yani
-- `migrate` HİÇBİR push'ta hiç çalışmıyor, Faz 0'dan beri TÜM migration'lar
-- ELLE (psql ile) uygulanıyordu, hiçbiri kayıt altına alınmadan. 20260920
-- bu "elle uygulama" zincirinde unutulan İLK dosyaydı — ve unutulduğunu
-- gösterecek hiçbir şey yoktu.
--
-- `worker/scripts/migration_uygula.py` bu tabloyu okuyup/yazıp bu sınıf
-- hatanın TEKRARINI yapısal olarak imkânsız kılar (`--dry-run` her koşuda
-- "bekleyen" migration'ları açıkça listeler). `audit_log` ile AYNI erişim
-- deseni (admin-only, append-only — SELECT/INSERT var, UPDATE/DELETE/
-- TRUNCATE hiç kimseye açılmaz) — bu da bir operasyonel iz kaydı, veri
-- tablosu değil.

CREATE TABLE IF NOT EXISTS schema_migrations (
  dosya_adi TEXT PRIMARY KEY,
  dosya_hash TEXT NOT NULL,
  uygulandi_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  uygulayan TEXT NOT NULL,
  sure_ms BIGINT NOT NULL
);

ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY admin_schema_migrations_select ON schema_migrations
  FOR SELECT TO admin
  USING (public.current_app_role() = 'admin');

CREATE POLICY admin_schema_migrations_insert ON schema_migrations
  FOR INSERT TO admin
  WITH CHECK (public.current_app_role() = 'admin');

GRANT SELECT, INSERT ON TABLE schema_migrations TO admin;

COMMIT;
