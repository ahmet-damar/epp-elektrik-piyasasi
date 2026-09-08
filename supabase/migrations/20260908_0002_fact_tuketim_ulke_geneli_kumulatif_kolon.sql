BEGIN;

-- EPP — Aşama 3 (2026-09-08) — de-kümülatif mantığının batch bağımlılığı
-- düzeltmesi.
--
-- Kök sorun: `fact_tuketim_ulke_geneli`'nin Excel (2026+) ayları, T11'in
-- KÜMÜLATİF Genel Toplam satırından, bir önceki ayın (aynı yıl içinde)
-- TOPLAMI çıkarılarak türetiliyordu — ama yalnız türetilen AYLIK değer
-- saklanıyordu, ham KÜMÜLATİF değer HİÇ saklanmıyordu. Bu, N. ayın
-- kayıtlı değerinin N-1. ayın (o an sahip olduğu) değerine SESSİZCE
-- bağımlı kalması demekti — N-1 sonradan düzeltilmiş bir batch'le
-- değişirse, N'in kayıtlı aylık değeri artık HİÇBİR aktif/kayıtlı veriden
-- türetilmemiş hâle geliyordu ve bunu tespit edecek hiçbir mekanizma
-- yoktu (projenin "batch izolasyonu" ilkesine aykırı).
--
-- Çözüm: ham kümülatif değer AYRI bir kolonda saklanıyor. Artık N. ayın
-- aylık değeri = (N'in kendi kümülatifi) − (N-1'in KAYITLI kümülatifi,
-- yeniden toplama İHTİYAÇ YOK — tek satır okuma). N-1 sonradan değişirse
-- `worker/scripts/tutarlilik_ulke_geneli_kumulatif.py` bunu AÇIKÇA
-- yakalar (aylik + onceki_kumulatif != kendi_kumulatif tutarsızlığı).
--
-- NULL bırakılıyor (NOT NULL DEĞİL): Word yıllarının (2016-2025) kendi
-- Genel Toplam satırı ZATEN aylık — hiç "kümülatif" kavramı yok, bu
-- kolonun onlar için bir anlamı yok.
ALTER TABLE fact_tuketim_ulke_geneli
  ADD COLUMN kumulatif_tuketim_mwh NUMERIC(16,3)
  CHECK (kumulatif_tuketim_mwh IS NULL OR kumulatif_tuketim_mwh >= 0);

COMMENT ON COLUMN fact_tuketim_ulke_geneli.kumulatif_tuketim_mwh IS
  'Yalnız Excel (2026+) ayları için: T11''in ham KÜMÜLATİF Genel Toplam '
  'değeri (yıl başından bu aya kadar) — tuketim_mwh (türetilen AYLIK '
  'değer) bundan bir önceki ayın KAYITLI kümülatifi çıkarılarak elde '
  'edilir. Word yıllarında (2016-2025) NULL — o yılların Genel Toplam '
  'satırı zaten aylık.';

COMMIT;
