BEGIN;

-- EPP — 2026-09-19, 3. tur (`Claude outputs/PROMPT_BATCH_DURUM_2026-09-19.md`
-- Görev 1). Kök neden: `otomatik_onaya_uygun()` `False` döndüğünde
-- `worker/job_worker.py` batch'i HİÇBİR duruma geçirmiyordu — yalnız konsola
-- uyarı basıp bırakıyordu, batch sonsuza dek 'running'de kalıyordu (gerçek
-- örnek: batch 4-8, 2026-02..06 Excel, 19 gün fark edilmedi — bkz.
-- `Claude outputs/kapanis_2026-09-19_batch_4_8.md`). Bu, mutabakat_
-- reddedildi'nin (migration 20260918_0001) kapattığı boşlukla TIPATIP AYNI
-- aile: doğru bir karar veriliyordu ama hiçbir kalıcı yere yazılmıyordu.
--
-- İKİ yeni değer:
--
-- 'onay_bekliyor' — TERMİNAL DEĞİL. Ingest başarıyla bitti, `otomatik_
-- onaya_uygun()` `False` döndü, İNSAN KARARI bekleniyor. `worker/job_
-- worker.py`'nin otomatik yolu artık batch'i buraya geçirir + `audit_log`a
-- yazar (hangi kontrol, hangi sebep). `running_batch_kontrolu.py`'nin
-- "takılı running" alarmından AYRI, sakin bir "inceleme kuyruğu" listesi
-- olarak raporlanır (`onay_bekleyen_batchleri_bul()`).
--
-- 'onaylanmadi' — TERMİNAL. Cloud oturumunun önerdiği dar kapsamlı
-- 'yerine_gecildi' YERİNE BİLİNÇLİ OLARAK daha GENİŞ bir isim seçildi
-- (2026-09-19 kapanış raporunda gerekçeli itiraz — bkz. `Claude outputs/
-- kapanis_2026-09-19_batch_durum.md`): 'onay_bekliyor' durumundaki bir
-- batch için insan "hayır" dediğinde (nedeni ne olursa olsun — başka bir
-- batch yerine geçti, veri hatalı bulundu, tekrar/gereksiz, vb.) bu duruma
-- geçer; SPESİFİK sebep (örn. "yerine batch 10 geçti") her zaman olduğu
-- gibi `error_summary` + `audit_log`'a yazılır. Dar bir 'yerine_gecildi'
-- yalnız "supersede" senaryosunu kapsardı — bir sonraki FARKLI red
-- senaryosunda YENİ bir durum daha icat etmek gerekirdi. 'dead_letter'
-- YENİDEN KULLANILMADI: `worker/ingest.py:is_basarisiz()` + `worker/job_
-- worker.py` arasındaki established İLİŞKİ (bir batch dead_letter
-- olduğunda `job_status`u da dead_letter olur — kod: `worker/ingest.py`
-- satır ~935) bir DEĞİŞMEZ oluşturuyor: dead_letter bir batch'in
-- `job_status`unun da başarısız/tükenmiş olduğunu ÖRTÜK OLARAK iddia eder.
-- 'onay_bekliyor'dan reddedilen batch'lerin (batch 4-8 gibi) `job_status`u
-- ZATEN 'succeeded'dir (asenkron İŞİN kendisi başarılıydı, yalnız
-- AKTİVASYON reddedildi) — dead_letter kullanmak bu değişmezi ihlal edip
-- YANLIŞ bir anlatı üretirdi ("iş başarısız oldu" derken iş aslında
-- başarılıydı). Bu yüzden AYRI bir terminal değer gerekli — ama TEK bir
-- geniş isimle, 'yerine_gecildi' gibi dar/tekrarlanabilir bir isim değil.
ALTER TABLE ingestion_batch DROP CONSTRAINT ingestion_batch_status_check;

ALTER TABLE ingestion_batch ADD CONSTRAINT ingestion_batch_status_check CHECK (
  status IN (
    'queued', 'running', 'succeeded', 'failed', 'retrying', 'dead_letter',
    'mutabakat_reddedildi', 'onay_bekliyor', 'onaylanmadi'
  )
);

COMMIT;
