# EPP Güvenlik ve Rol Yönetimi

## Rol kaynağı

Uygulama rolleri yalnızca `auth.jwt() -> 'app_metadata' ->> 'role'` claim'inden okunur.

Geçerli roller:
- viewer
- data_operator
- admin

Kullanıcı tarafı `user_metadata.role` değeri asla güvenilir yetki kaynağı değildir. `user_metadata.role` kullanımı reddedilir; güvenli kullanıcı ataması yalnızca güvenilir backend/admin akışıyla yapılmalıdır.

## Güvenilir atama akışı

Rol atamasının yapılması gereken yerler:
- Supabase Auth admin işlemleri
- güvenli backend servisleri
- kontrol edilmiş admin panel akışı

Son kullanıcı doğrudan `app_metadata.role` değerini değiştiremez; uygulama kodu bu alanı yazmaz ve frontend/app tarafı rol ataması yapmaz.

## RLS ve politika özeti

- viewer: yalnız `SELECT` ve yalnız `fact_*` aktif kayıtları (`is_active = true`)
- data_operator: kaynak ve batch üst verisi oluşturabilir; fact tablolarına ekleme/güncelleme yapabilir; yetki yönetimi yapamaz
- admin: operasyonel tüm tablolar için gerekli `SELECT/INSERT/UPDATE/DELETE` işlemleri yapar
- audit_log: append-only; `UPDATE`/`DELETE` yok
- service_role: Supabase tarafında RLS bypass davranışı vardır; bu anahtar frontend/dashboard'a asla verilmez

## Statik denetimler

- `public.current_app_role()` yalnızca `app_metadata.role` okur
- `user_metadata.role` kabul edilmez
- kimlik doğrulama sırasında role değeri listeden biri değilse `NULL` döner
- `viewer` için `INSERT/UPDATE/DELETE` politikası yoktur
- `audit_log` için `UPDATE/DELETE` politikası yoktur
