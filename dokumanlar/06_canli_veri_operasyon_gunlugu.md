# EPP — Canlı Veri Operasyon Günlüğü

Faz 0'da onay için ayrı bir UI yok (bkz. `worker/pipeline.py` modül notu) —
`otomatik_onaya_uygun()` eşiği tutmadığında elle `batch_onayla()` (veya onunla
birebir aynı `ingest.aktivasyon_yap()` + `ingest.batch_durumu_guncelle()`
çağrısı) çalıştırılır. Bu dosya, canlı Supabase projesinde yapılan HER TÜRLÜ
elle aktivasyon/müdahaleyi kaydeder — `audit_log` tablosu şemada var ama
hiçbir uygulama kodu ona otomatik yazmıyor (2026-08-31 itibarıyla doğrulandı),
bu yüzden bu günlük + ilgili `audit_log` satırları (bkz. aşağıda) birlikte
kalıcı iz oluşturur.

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

**Açık madde:** `audit_log`'a hiçbir uygulama kodu (ne `aktivasyon_yap()` ne
`batch_onayla()`) otomatik yazmıyor — bu, resmi onay yolundan geçilse bile
geçerli bir eksiklik. Kod değiştirilmedi (kapsam dışı bırakıldı), yalnızca
burada ve `audit_log`'a retroaktif elle kayıtla belgelendi.
