BEGIN;

-- GEÇİCİ — B2 doğrulama testi (2026-09-07). Bu dosya, ci.yml'in
-- integration job'ının migration'ları artık ELLE isim listesiyle değil
-- GLOB ile uyguladığını (ve uygulanan/toplam sayı doğrulamasının gerçekten
-- çalıştığını) kanıtlamak için BİLEREK, hiçbir listeye eklenmeden buraya
-- konuldu. CI loglarında "RAISE NOTICE" çıktısı görülüp "Uygulanan: 26 /
-- Toplam dosya: 26" satırı doğrulandıktan sonra bu dosya SİLİNECEK — canlı
-- Supabase'e HİÇ uygulanmayacak (deploy.yml'in migrate job'ı build-push'a
-- needs bağlı olduğundan zaten devre dışı, bkz. §9.3).
DO $$
BEGIN
  RAISE NOTICE 'B2 dogrulama: bu migration glob ile YAKALANDI (isim listesinde degil).';
END $$;

COMMIT;
