BEGIN;

-- Small governed reference dimensions (dokumanlar/03_veri_modeli.md) had no
-- natural-key uniqueness, which made a safe upsert impossible from the
-- ingest worker. Add it so dim_kaynak/dim_lisans can be looked up (and,
-- if ever needed, upserted) without risking duplicate rows. Postgres has no
-- ADD CONSTRAINT IF NOT EXISTS, so guard manually to keep this rerunnable.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conname = 'uq_dim_kaynak_adi') THEN
    ALTER TABLE dim_kaynak ADD CONSTRAINT uq_dim_kaynak_adi UNIQUE (kaynak_adi);
  END IF;
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conname = 'uq_dim_lisans_tur') THEN
    ALTER TABLE dim_lisans ADD CONSTRAINT uq_dim_lisans_tur UNIQUE (tur);
  END IF;
END $$;

-- dim_tuketici_grubu (dokumanlar/05_kaynak_dosya_sozlesmesi.md — Tüketici Grubu Eşleme)
INSERT INTO dim_tuketici_grubu (grup_adi)
VALUES
  ('Mesken'),
  ('Sanayi'),
  ('Tarımsal'),
  ('Aydınlatma'),
  ('Kamu ve Özel Hizmetler')
ON CONFLICT (grup_adi) DO NOTHING;

-- dim_lisans — CHECK (tur IN ('Lisansli','Lisanssiz')), Türkçe karaktersiz
INSERT INTO dim_lisans (tur)
VALUES
  ('Lisansli'),
  ('Lisanssiz')
ON CONFLICT (tur) DO NOTHING;

-- dim_kaynak (dokumanlar/05_kaynak_dosya_sozlesmesi.md — Kaynak Türü Eşleme)
INSERT INTO dim_kaynak (kaynak_adi, yenilenebilir_mi, grup)
VALUES
  ('Hidrolik', true, 'Yenilenebilir'),
  ('Rüzgar', true, 'Yenilenebilir'),
  ('Güneş', true, 'Yenilenebilir'),
  ('Jeotermal', true, 'Yenilenebilir'),
  ('Biyokütle', true, 'Yenilenebilir'),
  ('Doğal Gaz', false, 'Fosil'),
  ('İthal Kömür', false, 'Fosil'),
  ('Linyit', false, 'Fosil'),
  ('Taş Kömürü', false, 'Fosil'),
  ('Asfaltit', false, 'Fosil'),
  ('Fuel Oil', false, 'Fosil')
ON CONFLICT (kaynak_adi) DO NOTHING;

-- dim_il — 81 il, resmi plaka kodu (il_kodu PK)
INSERT INTO dim_il (il_kodu, il_adi)
VALUES
  (1, 'Adana'), (2, 'Adıyaman'), (3, 'Afyonkarahisar'), (4, 'Ağrı'), (5, 'Amasya'),
  (6, 'Ankara'), (7, 'Antalya'), (8, 'Artvin'), (9, 'Aydın'), (10, 'Balıkesir'),
  (11, 'Bilecik'), (12, 'Bingöl'), (13, 'Bitlis'), (14, 'Bolu'), (15, 'Burdur'),
  (16, 'Bursa'), (17, 'Çanakkale'), (18, 'Çankırı'), (19, 'Çorum'), (20, 'Denizli'),
  (21, 'Diyarbakır'), (22, 'Edirne'), (23, 'Elazığ'), (24, 'Erzincan'), (25, 'Erzurum'),
  (26, 'Eskişehir'), (27, 'Gaziantep'), (28, 'Giresun'), (29, 'Gümüşhane'), (30, 'Hakkari'),
  (31, 'Hatay'), (32, 'Isparta'), (33, 'Mersin'), (34, 'İstanbul'), (35, 'İzmir'),
  (36, 'Kars'), (37, 'Kastamonu'), (38, 'Kayseri'), (39, 'Kırklareli'), (40, 'Kırşehir'),
  (41, 'Kocaeli'), (42, 'Konya'), (43, 'Kütahya'), (44, 'Malatya'), (45, 'Manisa'),
  (46, 'Kahramanmaraş'), (47, 'Mardin'), (48, 'Muğla'), (49, 'Muş'), (50, 'Nevşehir'),
  (51, 'Niğde'), (52, 'Ordu'), (53, 'Rize'), (54, 'Sakarya'), (55, 'Samsun'),
  (56, 'Siirt'), (57, 'Sinop'), (58, 'Sivas'), (59, 'Tekirdağ'), (60, 'Tokat'),
  (61, 'Trabzon'), (62, 'Tunceli'), (63, 'Şanlıurfa'), (64, 'Uşak'), (65, 'Van'),
  (66, 'Yozgat'), (67, 'Zonguldak'), (68, 'Aksaray'), (69, 'Bayburt'), (70, 'Karaman'),
  (71, 'Kırıkkale'), (72, 'Batman'), (73, 'Şırnak'), (74, 'Bartın'), (75, 'Ardahan'),
  (76, 'Iğdır'), (77, 'Yalova'), (78, 'Karabük'), (79, 'Kilis'), (80, 'Osmaniye'),
  (81, 'Düzce')
ON CONFLICT (il_kodu) DO NOTHING;

-- sistem_parametre (dokumanlar/02_srs_ozet.md — OD-1/OD-2)
INSERT INTO sistem_parametre (parametre_adi, parametre_degeri, aciklama)
VALUES
  ('hdd_baz_c', 18, 'HDD baz sıcaklığı (°C)'),
  ('cdd_baz_c', 22, 'CDD baz sıcaklığı (°C)'),
  ('hava_norm_yil', 10, 'Hava normu periyodu (yıl, sabit)'),
  ('tuketim_norm_yil', 5, 'Tüketim normu periyodu (yıl, rolling)')
ON CONFLICT (parametre_adi) DO NOTHING;

COMMIT;
