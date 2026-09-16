BEGIN;

-- 2026-09-16 (dashboard incelemesi, "iki küçük iş" madde 2): KPI-12'nin
-- eşikleri (yesil_alt=5.0, sari_alt=10.0, migration 20260905_0001) KONTROL
-- EDİLDİ — gerekçesi ölçülerek DOĞRULANDI, MİSKALİBRE ÇIKTI, burada
-- düzeltiliyor.
--
-- Bulgu: 20260905_0001'in kendi yorumu KPI-06/13/25/26/27 için gerçek
-- dağılıma referans veriyor ("gerçek dağılıma dayalı", "n=114 ay" vb.) ama
-- KPI-12 için HİÇBİR ampirik referans YOK — yalnız "dashboard |değer|
-- geçirecek" notu var. Aynı gün (2026-09-05), `06_canli_veri_operasyon_
-- gunlugu.md`'nin "KPI-11/12 doğrulaması" kaydı canlıda ZATEN ölçülmüş,
-- Ankara için %52-81 aralığında KPI-12 değerleri gösteriyordu — yani
-- 5.0/10.0 eşiği seçilirken görünürde gerçek canlı veriyle KARŞILAŞTIRMA
-- YAPILMAMIŞ (yapılsaydı 5/10 bandının neredeyse HİÇBİR gerçek gözlemi
-- kapsamadığı hemen görülürdü) — bu yüzden "şişik veriye göre kalibre
-- edildi" DEĞİL, muhtemelen hiç veriye bakılmadan genel/keyfi bir
-- yüzde (%5/%10) seçildi. Sonuç aynı: MİSKALİBRE, düzeltme gerekiyor.
--
-- 2026-09-16'da "Sanayi dikişi" düzeltmesinden (bkz. `04_kpi_sozlesmeleri.
-- md`) SONRA, canlıya karşı GERÇEK bir dağılım ölçüldü — 81 il × 5 ay
-- (2026-02..2026-06, hava-normu 10 yıllık sabit pencerenin ilk kez tam
-- dolduğu aylar), n=403 geçerli (il, ay) gözlemi, |KPI-12| değerleri:
--   min=0.2  p10=7.7  p25=12.9  medyan=19.1  p75=24.7  p90=31.0  max=124.4
-- (`06_canli_veri_operasyon_gunlugu.md` 2026-09-16 kaydına bkz., tam
-- rakamlar ve sorgu orada). Eski eşikle (yeşil≤5, sarı≤10) gözlemlerin
-- EZİCİ ÇOĞUNLUĞU (kabaca %90'ı) "kırmızı" gösteriyordu — trafik ışığı
-- tipik/beklenen sapmayı ANOMALİ gibi işaretliyordu.
--
-- Yeni eşik (KPI-13/25/27'nin izlediği "ampirik persentile dayalı, temiz
-- yuvarlak sayı" yöntemiyle): yeşil_alt=15 (medyanın biraz altı — %15 ve
-- altı sapma "tipik/iyi"), sari_alt=30 (p90'a yakın — %30'un üstü, gözlenen
-- dağılımın en uç ~%10'u, GERÇEKTEN dikkat çekici). Bu bant hem il bazlı
-- kartı (yukarıdaki n=403 örneklemin doğrudan kaynağı) hem "Türkiye
-- Geneli" toplamını (81 ilin kendi β/γ'sıyla toplanan, tek tek illerden
-- daha az gürültülü bir agregasyon — bkz. dashboard 2026-09-05 Görev 4
-- Seçenek A) aynı `kpi_esik` satırıyla kullanıyor; toplamın bireysel
-- illerden daha düşük/istikrarlı çıkması BEKLENEN bir durum, ayrı bir
-- eşik gerektirmiyor.
--
-- KPI-11'i girdi alan BAŞKA bir eşik YOK (kontrol edildi — `kpi_esik`'te
-- yalnız KPI-06/12/13/25/26/27 satırları var, hiçbiri KPI-11'in
-- arındırılmış tüketim çıktısını doğrudan girdi almıyor; KPI-13/25/27
-- kendi bağımsız `fact_tuketim_ulke_geneli`/`fact_tuketim` kaynaklarını
-- kullanıyor) — KPI-11'in kendisi hiçbir zaman ayrı bir trafik ışığı
-- almadı (yalnız KPI-12 renklendirilir), bu yüzden onun için AYRI bir
-- değişiklik gerekmiyor.
UPDATE kpi_esik SET yesil_alt = 15.0, sari_alt = 30.0
WHERE kpi_id = 'KPI-12' AND surum = 'v1';

COMMIT;
