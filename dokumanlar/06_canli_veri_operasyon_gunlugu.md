# EPP — Canlı Veri Operasyon Günlüğü

Faz 0'da onay için ayrı bir UI yok (bkz. `worker/pipeline.py` modül notu) —
`otomatik_onaya_uygun()` eşiği tutmadığında elle onay verilir: **artık
`worker/scripts/onayla.py --batch-id N --actor "..."` ile resmi
`pipeline.batch_onayla(conn, batch_id, actor_name)` doğrudan çağrılabilir**
(2026-08-31'den itibaren — bkz. aşağıdaki "2026-08-31 (devam)" bölümü;
önceki `batch_id=1`/`batch_id=3` aktivasyonları bu araç var olmadan, elle
`aktivasyon_yap()` çağrılarıyla yapılmıştı). `_isle_govde()` ve
`batch_onayla()` artık `audit_log`'a KENDİLİĞİNDEN yazıyor (kim/ne zaman/
hangi batch/hangi istisna satırlar — bkz. `03_veri_modeli.md`), bu yüzden bu
günlük dosyası artık her elle müdahale için ZORUNLU bir yedek değil, ama
"neden bu batch elle onaylandı" gibi anlatısal bağlamı (audit_log payload'ı
saklamıyor) kaydetmeye devam eder.

## 2026-08-31 — EPDK Ocak 2026, ilk canlı yükleme + T13 düzeltmesi

**Kaynak dosya:** `_PortalAdmin_Uploads_Content_FastAccess_8684c04c60369.xlsx`
("Elektrik Piyasası Sektör Raporu Ocak 2026 - Ek"), tarih_id=202601.

**batch_id=1** (parser_version=0.1, ilk yükleme):
- `epdk_aylik_isle()` ile parse+yüklendi (is_active=false).
- `otomatik_onaya_uygun()` → `False`, sebep: `fact_tuketim: 1 satır reddedildi`
  (Batman/Tarımsal −471,934 MWh — resmi raporun kendisindeki gerçek negatif
  düzeltme kalemi, parser hatası değil; T7/T9 ülke geneli mutabakatı bu
  değeri zaten içeriyor — bkz. `05_kaynak_dosya_sozlesmesi.md`).
- Kullanıcı onayıyla `batch_onayla()` eşdeğeri elle aktivasyon çalıştırıldı
  (`ingest.aktivasyon_yap()` her 4 fact tablosu için + `batch_durumu_guncelle(...,
  'succeeded')`) — tam SQL için `worker/ingest.py:aktivasyon_yap()`.
- **Sonradan bulundu:** bu batch'in `fact_serbest_tuketici` verisi hatalıydı —
  `tablo13_serbest_tuketici_oku()` İstanbul'un Anadolu/Avrupa satırlarını
  toplamıyordu, `ON CONFLICT DO NOTHING` Avrupa tarafını (~2.772.123 MWh)
  sessizce eliyordu. Kök neden ve düzeltme: commit `8ef843f`.

**batch_id=3** (parser_version=0.2, düzeltme sonrası yeniden işleme):
- Aynı kaynak dosya, düzeltilmiş parser ile yeniden işlendi.
- `otomatik_onaya_uygun()` → `False`, aynı sebep (T11 + T13'teki 5 bilinen
  gerçek negatif düzeltme satırı, aşağıda tam liste).
- Kullanıcı onayıyla aynı şekilde elle aktive edildi — batch_id=1'in fact
  satırları `is_active=false` oldu, batch_id=3'ünkiler `is_active=true`.
- Doğrulama: `fact_serbest_tuketici` aktif toplamı 23.376.859 → 26.148.982
  MWh (+2.772.123, tam kayıp kadar); İstanbul/Mesken/Serbest Tüketici artık
  122.240,29 MWh (Anadolu+Avrupa toplamı, önceden 36.974,32 idi).

**Her iki batch'te de reddedilen 5 satır** (P0 kuralı gereği bilinçli red,
gerçek resmi veri, `dogrula_tuketim`/`dogrula_serbest_tuketici`'nin
`tuketim_mwh < 0` kuralı):

| Tablo | İl | Tür | Grup | MWh |
|---|---|---|---|---|
| fact_tuketim | Batman | — | Tarımsal | −471,934 |
| fact_serbest_tuketici | Batman | ST Olma Hakkı Bulunmayan Aboneler | Tarımsal | −45,081 |
| fact_serbest_tuketici | Batman | ST Olma Hakkını Kullanmayan Aboneler | Tarımsal | −426,853 |
| fact_serbest_tuketici | Tekirdağ | ST Olma Hakkı Bulunmayan Aboneler | Sanayi | −172,630 |
| fact_serbest_tuketici | Yozgat | ST Olma Hakkı Bulunmayan Aboneler | Sanayi | −3,791 |

**Kalıcı iz:** `audit_log.audit_id` 1 ve 2 (`table_name='ingestion_batch'`,
`record_id`=batch_id, `actor_name='manual-remediation:claude-code (kullanıcı
onaylı)'`, `payload` JSONB'de bu tablodaki bilgilerin makine-okunur hâli).

**Açık madde (2026-08-31'de KAPATILDI, aşağıya bkz.):** ~~`audit_log`'a
hiçbir uygulama kodu (ne `aktivasyon_yap()` ne `batch_onayla()`) otomatik
yazmıyor~~.

## 2026-08-31 (devam) — Üç açık madde kapatıldı

Yukarıdaki elle remediation sırasında bulunan üç boşluk, aynı günün
devamında kapatıldı:

1. **Stray uncommitted dosyalar temizlendi** (commit `c926a04`): `worker/
   validate_rls_static.py` ve `.github/workflows/security.yml`'deki iz-suz
   değişiklikler HEAD'e sıfırlandı; 2 boş migration + 2 boş debug script
   silindi. Kök neden: `git stash`'te duran, 2026-08-19'dan kalma terk
   edilmiş bir RLS yeniden-tasarım denemesi (authenticated + current_app_
   role() modeline geçiş, migration 0004-0005 numaralı) — karar gerekçesi
   ve migration-numarası çakışma uyarısı `01_kavramsal_tasarim.md` ADR-8'e
   düşüldü, stash'ler drop edildi.

2. **`batch_onayla()` artık pratik çağrılabilir** (commit `9bcd824`):
   imza `batch_onayla(conn, sonuc: IslemSonucu)` → `batch_onayla(conn,
   batch_id: int, actor_name="system")`. IslemSonucu (pandas DataFrame'ler
   içeren bellek nesnesi) süreç sınırını aşamıyordu — batch_id (düz int)
   aşabiliyor. Hangi tabloların aktive edileceği artık `ingest.
   batch_dolu_tablolari_bul()` ile DB'den sorgulanıyor. Yeni `worker/
   scripts/onayla.py` CLI: `python -m worker.scripts.onayla --batch-id N
   --actor "..."`. 2 yeni test (bir batch'in bazı/tüm tablolara hiç veri
   yazmadığı durum) CI'ın gerçek postgres:16'sında doğrulandı.

3. **`audit_log` artık koddan otomatik yazılıyor** (commit `fd6cfaa`):
   `_isle_govde()` tamamlandığında (`action_type='INSERT'`, RED satırlarının
   tam detayı + KARANTİNA'nın sayı+ilk 20 örneği) ve `batch_onayla()`
   tamamlandığında (`action_type='UPDATE'`, `actor_name` + aktive edilen
   tablolar) birer kayıt düşülüyor — manuel backfill değil. Şema
   `03_veri_modeli.md`'ye belgelendi. `audit_id` 1-2 (bu dosyanın yukarıdaki
   bölümündeki `batch_id=1`/`batch_id=3` için) hâlâ geçerli, retroaktif elle
   yazılmış kayıtlar olarak kalıyor — yeni mekanizma yalnız BUNDAN SONRAKİ
   ingest/onay çağrıları için otomatik çalışır.

Üçü de CI + Security'de yeşil, gerçek izole `postgres:16` entegrasyon
testleriyle doğrulandı.

## 2026-08-31 (devam 2) — Şubat-Haziran toplu yükleme: EPDK şablon değişikliği bulundu

Kullanıcı Şubat-Haziran 2026 (5 ay) EPDK dosyalarını `worker/scripts/
backfill.py` + `worker/job_worker.py` (asenkron yol, ilk kez canlı DB'ye
karşı denendi) ile kuyruğa alıp işletti — hepsinde `otomatik_onaya_uygun()`
`False` döndü (`mutabakat uyuşmadı: fact_tuketim`), hiçbiri aktive edilmedi,
derinlemesine incelendi. **EPDK'nın rapor şablonu Mart 2026'dan itibaren
değişmiş**, üç ayrı sorun bulundu:

1. **Tablo 11 KÜMÜLATİF** (başlığı açıkça "Kümülatif Faturalanan Elektrik
   Tüketimi..." diyor) — parser bunu aylık sanıp doğrudan `fact_tuketim`'e
   yüklüyordu. Ocak'ta sorun görünmedi (yılın ilk ayında kümülatif=aylık).
   **Düzeltildi**: `ingest.yil_ici_onceki_tuketim_toplami()` + `pipeline.py`
   T11 okuma sonrası fark alma adımı — aynı yılın önceki aktif aylarının
   toplamını DB'den çekip kümülatif değerden çıkarıyor. **Sonuç: ayları
   SIRAYLA işlemek artık mimari bir zorunluluk** (bir ayı işlemek, o yılın
   önceki tüm aylarının DB'de aktif/doğru olmasını gerektirir).
2. **Tablo 13 satır düzeni kaymış** — "İl Adı" etiketi Ocak/Şubat'ta kendi
   satırında, Mart'tan itibaren grup adlarıyla (Mesken/Sanayi/...) aynı
   satırda; "Tüketici Sayısı" etiketi de bir üst satıra taşınmış.
   `fact_serbest_tuketici`'yi Mart-Haziran için TAMAMEN BOŞ bırakıyordu
   (`toplam=0`, sessizce — `eksik_tablolar` kontrolü bunu yakalamadı çünkü
   sayfa VARDI, yalnız içeriği okunamıyordu). **Düzeltildi**:
   `tablo13_serbest_tuketici_oku()` artık "Tüketici Sayısı" etiketini ve
   grup-adı satırını sabit pozisyon yerine dinamik arıyor, her iki formatı
   da destekliyor (regresyon testiyle: eski format `test_tablo13_serbest_
   tuketici`, yeni format `test_tablo13_serbest_tuketici_yeni_format_
   2026_03`).
3. **Tablo 7 çoklu-ay format — DÜZELTİLMEDİ, bilinen gap.** T7 her ay yeni
   bir "Miktar" sütunu ekleyerek büyüyor (Ocak, Ocak+Şubat, ...); parser
   (`_uzun_format_grup_oku`) her zaman İLK sütunu (hep Ocak'ı) okuyor. Bu,
   T7'nin SADECE mutabakat kontrolü için kullanılması nedeniyle fact
   tablosuna yazılan veriyi ETKİLEMİYOR (düşük risk) — kullanıcı kararıyla
   şimdilik ertelendi. **Etkisi**: `_mutabakat()`'ın fact_tuketim sonucu
   Şubat'tan itibaren güvenilmez (yanlış pozitif/negatif verebilir);
   `otomatik_onaya_uygun()` bu yüzden T11 düzeltmesi sonrasında bile
   muhtemelen hâlâ elle onay isteyecek — bu BEKLENEN, T7 düzeltilene kadar
   sürecek bir durum.

Commit'ler: T11+T13 fix (bkz. main geçmişi), gerçek Mart dosyasına karşı
doğrulandı (satır sayısı/toplam Şubat'a yakın çıktı, artık kümülatif artış
göstermiyor). 5 ay, düzeltme sonrası sırayla (Şubat→Haziran) yeniden
işlendi — sonuçlar bu bölümün devamında.
