BEGIN;

-- fact_uretim.uretim_mwh NOT NULL idi, ama fact_uretim'in doğal anahtarı
-- (il_kodu, tarih_id, kaynak_id, lisans_id) grain'inde üretim (MWh) verisi
-- aylık EPDK raporunun HİÇBİR tablosunda mevcut değil — yalnızca
-- kurulu_guc_mw bu grain'de var (Tablo 1/4, il×kaynak). Üretim ya kaynak
-- bazında ülke toplamı (Tablo 2/5, il yok) ya il bazında toplam (Tablo 3/6,
-- kaynak yok) olarak raporlanıyor; ikisinin kesişimi raporun 13 tablosunun
-- hiçbirinde yok. Detaylı analiz: worker/parser.py modül notu.
--
-- kurulu_guc_mw NOT NULL kalır (bu grain'de gerçekten mevcut).
ALTER TABLE fact_uretim ALTER COLUMN uretim_mwh DROP NOT NULL;

-- CHECK (uretim_mwh >= 0) dokunulmadan kalır: Postgres'te CHECK kısıtı NULL
-- değerler için UNKNOWN döner ve bu ihlal sayılmaz (ek değişiklik gerekmez).

COMMIT;
