BEGIN;

-- EPP — 2026-09-18, İş C (kapsam_raporu.md "Doğrulama Turu — 2026-09-17"
-- Madde 1d'nin bulgusu): `ingestion_batch.status` durum makinesi 6 değer
-- taşıyordu (queued, running, succeeded, failed, retrying, dead_letter) —
-- mutabakatın (worker/scripts/mutabakat_uretim.py:periyot_aktivasyona_
-- uygun_mu()) KALICI OLARAK reddettiği bir batch için AYRI bir TERMİNAL
-- durum YOKTU. Sonuç: böyle bir batch (gerçek örnek: batch_id=732,
-- fact_uretim_kaynak_geneli/2024-02, Bulgu J gereği T3 hiç yüklenmediği
-- için mutabakat ASLA geçemez) sonsuza dek 'running'de kalıyordu —
-- job_status.next_retry_at'in geçmişte kalmasıyla AYNI sınıf sessiz-
-- bekleme riski (bkz. worker/scripts/running_batch_kontrolu.py,
-- 2026-09-17).
--
-- 'dead_letter' İLE BİLİNÇLİ OLARAK BİRLEŞTİRİLMEDİ: dead_letter "N
-- retry sonrası pes edildi" anlamına geliyor (worker/ingest.py:
-- is_basarisiz(), _MAX_DENEME), 'mutabakat_reddedildi' İSE "çapraz
-- mutabakat kontrolü kural gereği reddetti" — farklı kavramlar,
-- karıştırılırsa ileride hangi nedenle bir batch'in son bulduğu ayırt
-- edilemez.
--
-- Bu YENİ durum PER-BATCH terminaldir, PER-DÖNEM (tarih_id) kalıcı bir
-- kapan DEĞİLDİR: aynı dönem için FARKLI bir source_asset (örn. EPDK'nın
-- revize ettiği bir dosya, farklı file_hash) ile YENİ bir batch açılıp
-- normal şekilde aktive edilebilir — bkz. worker/tests/test_mutabakat_
-- reddi_geri_donulebilirlik.py (İş C3, uçtan uca kanıt).
ALTER TABLE ingestion_batch DROP CONSTRAINT ingestion_batch_status_check;

ALTER TABLE ingestion_batch ADD CONSTRAINT ingestion_batch_status_check CHECK (
  status IN (
    'queued', 'running', 'succeeded', 'failed', 'retrying', 'dead_letter',
    'mutabakat_reddedildi'
  )
);

COMMIT;
