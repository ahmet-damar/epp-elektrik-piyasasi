BEGIN;

-- GEÇİCİ — C4 doğrulama testi (2026-09-07). Bu dosya, worker/validate_
-- role_access.py'nin yeni tamlık kontrolünün (her public tabloda RLS +
-- policy zorunlu, istisna yok) GERÇEKTEN çalıştığını CI'da kanıtlamak
-- için BİLEREK RLS'siz/policy'siz bir tablo ekliyor. CI'ın "Schema
-- validation + static RLS validation" job'ının "Run role-based access
-- verification" adımında FAIL etmesi bekleniyor. Doğrulandıktan sonra bu
-- dosya SİLİNECEK — canlı Supabase'e HİÇ uygulanmayacak (deploy.yml'in
-- migrate job'ı build-push'a needs bağlı, o da if:false ile devre dışı).
CREATE TABLE sahte_test_tablosu_c4 (id INT PRIMARY KEY);

COMMIT;
