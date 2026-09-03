BEGIN;

-- Faz B (çok-kullanıcılı giriş) adım 1 doğrulaması sırasında (2026-09-05)
-- bulunan üçüncü bir bağımsız eksiklik: `20260819_0015_auth_schema_usage_
-- viewer_grants.sql`'in `GRANT USAGE ON SCHEMA auth TO viewer, data_operator,
-- admin;` ifadesi canlı Supabase'de HİÇBİR ZAMAN kalıcı olarak etkili
-- OLMADI — hatasız çalışıyor GÖRÜNÜYOR (`ON_ERROR_STOP` tetiklenmiyor) ama
-- işlem içinde bile `has_schema_privilege(...)` hâlâ false dönüyor. Kök
-- neden: `auth` şeması `supabase_admin`'e ait; bağlantımızın kullandığı
-- `postgres` rolünün KENDİSİ `auth` üzerinde USAGE'a sahip ama WITH GRANT
-- OPTION'ı YOK (`has_schema_privilege('postgres','auth','USAGE WITH GRANT
-- OPTION')` = false) — yani `postgres` bu izni BAŞKA rollere devretme
-- yetkisine sahip değil, Supabase'in yönetilen platformu bunu (sessizce)
-- engelliyor.
--
-- Çözüm: `viewer`/`data_operator`/`admin`'e DOĞRUDAN `auth` şeması erişimi
-- vermeye ÇALIŞMAK yerine, `public.current_app_role()`'ü SECURITY DEFINER
-- yap. Fonksiyon zaten `postgres` sahipliğinde ve `postgres`'in KENDİSİ
-- `auth.jwt()`'yi çağırabiliyor (yalnız bunu BAŞKASINA devredemiyor) —
-- SECURITY DEFINER, fonksiyonun gövdesini ÇAĞIRANIN değil SAHİBİNİN
-- (`postgres`) yetkisiyle çalıştırır, bu yüzden `auth` şema erişimi hiç
-- gerekmez.
--
-- GÜVENLİK NOTU: Bu güvenli bir SECURITY DEFINER kullanımıdır — fonksiyon
-- yalnız ÇAĞIRANIN KENDİ oturumunun `request.jwt.claims` GUC'unu (session-
-- yerel, başka bir oturuma sızmaz) okuyup `{'viewer','data_operator',
-- 'admin'}` kümesine filtrelenmiş bir string döndürür; ek bir yetki
-- YÜKSELTMESİ (privilege escalation) YAPMAZ, yalnız çağıranın zaten
-- kendine ait olan bilgiyi (kendi JWT'si) okumasını sağlar.
--
-- Canlıda test edildi (2026-09-05): SECURITY DEFINER sonrası `viewer`
-- rolü doğru JWT claim'iyle `current_app_role()` = 'viewer' döndürdü VE
-- `fact_tuketim` sorgusu is_active satırlarını doğru filtreledi (JWT
-- claim'siz 0 satır, claim'li 41547 satır) — uçtan uca RLS zinciri artık
-- ÇALIŞIYOR.
ALTER FUNCTION public.current_app_role() SECURITY DEFINER;

COMMIT;
