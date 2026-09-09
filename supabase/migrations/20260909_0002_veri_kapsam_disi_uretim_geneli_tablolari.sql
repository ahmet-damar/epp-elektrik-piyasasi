BEGIN;

-- EPP — Aşama 3/ADIM 3, Bulgu D kararı (2026-09-09) — `veri_kapsam_disi`
-- tablosunun `fact_tablosu` CHECK kısıtı, orijinal 4 fact tablosuyla
-- (fact_tuketim/fact_uretim/fact_abone/fact_serbest_tuketici) sınırlıydı
-- (migration 20260819_0012). Bu turda `fact_uretim_kaynak_geneli` ve
-- `fact_uretim_il_geneli` (migration 20260909_0001) için de kapsam-dışı
-- kaydı gerekiyor — Word 2016-2017'de Excel'in "Brüt Lisanssız Üretim"
-- tanımıyla eşleşen bir kaynak YOK (bkz. dokumanlar/12_word_uretim_
-- envanteri.md Bulgu D). Kısıt genişletiliyor — mevcut satırlar/davranış
-- DEĞİŞMİYOR, yalnız 2 yeni izinli değer ekleniyor.

ALTER TABLE veri_kapsam_disi DROP CONSTRAINT veri_kapsam_disi_fact_tablosu_check;

ALTER TABLE veri_kapsam_disi ADD CONSTRAINT veri_kapsam_disi_fact_tablosu_check CHECK (
  fact_tablosu IN (
    'fact_tuketim', 'fact_uretim', 'fact_abone', 'fact_serbest_tuketici',
    'fact_uretim_kaynak_geneli', 'fact_uretim_il_geneli'
  )
);

COMMIT;
