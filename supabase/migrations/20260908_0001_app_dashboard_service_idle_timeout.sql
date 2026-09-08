BEGIN;

-- EPP — Aşama 1 kapanışı (2026-09-08): app_dashboard_service için
-- idle_in_transaction_session_timeout.
--
-- Gerçek olay (2026-09-07, C4 migration'ı uygularken): bu rolle
-- Supavisor üzerinden açılan bir Streamlit oturumu, son sorgusundan
-- sonra commit/rollback YAPMADAN 3+ saat "idle in transaction" durumda
-- kaldı ve bir sonraki migration'ın ihtiyaç duyduğu kilidi engelleyip
-- statement_timeout ile onu durdurdu (bkz. 06_canli_veri_operasyon_
-- gunlugu.md 2026-09-07 kaydı).
--
-- Kök neden SİSTEMATİK, tek seferlik değil: app/dashboard.py hiçbir
-- yerde conn.commit()/rollback() ya da autocommit=True kullanmıyor
-- (psycopg varsayılanı autocommit=False) — bu yüzden HER dashboard
-- oturumu, İLK sorgusundan itibaren kapanana kadar TEK bir açık işlem
-- içinde kalıyor; Streamlit sekmesi etkileşimsiz bırakıldığında bu işlem
-- otomatik olarak "idle in transaction" hâline geliyor. Bu davranışı
-- KOD SEVİYESİNDE düzeltmek (autocommit/periyodik commit) bu turun
-- kapsamı DIŞI bırakıldı — burada yalnız DB seviyesinde bir üst sınır
-- konuyor.
--
-- NOT — YANLIŞ parametre ile karıştırılmasın: idle_session_timeout
-- (PG14+) TAMAMEN BOŞ/işlemsiz oturumlar içindir, bu senaryoya UYMUYOR.
-- Doğru parametre idle_in_transaction_session_timeout (PG9.6+) — açık
-- bir işlemi olan ama sorgu ÇALIŞTIRMAYAN oturumlar için, yaşanan olay
-- tam olarak buydu.
--
-- Test edildi, VARSAYILMADI (2026-09-08): kısa bir timeout (2s) ile
-- gerçek bir oturumda ikinci sorgu psycopg.errors.
-- IdleInTransactionSessionTimeout fırlattı — app/dashboard.py'de bu
-- hatayı yakalayıp otomatik yeniden bağlanan bir mekanizma YOK (ayrı bir
-- iyileştirme konusu, kapsam dışı), kullanıcı "Çıkış Yap" ile elle
-- yeniden giriş yapmalı. 30 dakikalık değer, aktif kullanımda (herhangi
-- bir 30 dk pencerede en az bir etkileşim) bu riski pratikte sıfıra
-- indiriyor — yalnız gerçekten terk edilmiş sekmeler etkilenir, ki asıl
-- amaç zaten onları temizlemek.
ALTER ROLE app_dashboard_service SET idle_in_transaction_session_timeout = '30min';

COMMIT;
