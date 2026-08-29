# EPP — Veri Modeli (Yıldız Şema)

Kaynak: SRS Böl. 5 + Ek C (Veri Sözlüğü). Kod üretiminde ESAS ALINIR.

## Boyut Tabloları

### dim_tarih
| Kolon | Tip | Zorunlu | Açıklama |
|-------|-----|---------|----------|
| tarih_id | int | PK | YYYYMM (202601) / YYYY00 yıllık (202500) |
| yil, ay, ceyrek | smallint | NN | ay=0 yıllık kayıtta |
| ay_adi, yil_ay | text | — | türetilmiş |
| donem_tipi | text | NN | 'aylik' \| 'yillik' |

### dim_il
| il_kodu | int PK | plaka (1-81) |
| il_adi | text NN | normalize |
| bolge, dagitim_bolgesi | text | — |

### dim_kaynak
| kaynak_id | int PK |
| kaynak_adi | text NN | Hidrolik/Rüzgar/Güneş... |
| yenilenebilir_mi | boolean NN |
| grup | text | Yenilenebilir/Fosil |

### dim_tuketici_grubu / dim_lisans
- grup_id PK, grup_adi (Mesken/Sanayi/Tarımsal/Aydınlatma/Kamu ve Özel Hizmetler)
- lisans_id PK, tur (Lisanslı/Lisanssız)

## Kaynak & Batch Tabloları

### source_asset (P0-3)
```sql
CREATE TABLE source_asset (
  source_asset_id BIGSERIAL PRIMARY KEY,
  source_type TEXT NOT NULL,   -- 'epdk_aylik','epdk_yillik','hava'
  source_kind TEXT NOT NULL CHECK (source_kind IN ('file','api')),
  source_period TEXT, donem_tipi TEXT,
  file_name TEXT, file_hash TEXT, storage_path TEXT,   -- file
  source_uri TEXT, request_hash TEXT,                  -- api
  uploaded_by UUID, created_at TIMESTAMPTZ DEFAULT now(),
  CHECK ((source_kind='file' AND file_name IS NOT NULL AND file_hash IS NOT NULL)
      OR (source_kind='api'  AND source_uri IS NOT NULL AND request_hash IS NOT NULL))
);
```

### ingestion_batch (P0-5)
```sql
CREATE TABLE ingestion_batch (
  batch_id BIGSERIAL PRIMARY KEY,
  source_asset_id BIGINT NOT NULL REFERENCES source_asset(source_asset_id),
  parser_version TEXT NOT NULL, schema_version TEXT NOT NULL,
  status TEXT NOT NULL,
  total_row_count INT DEFAULT 0, accepted_row_count INT DEFAULT 0,
  rejected_row_count INT DEFAULT 0, error_summary TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (source_asset_id, parser_version, schema_version)  -- P0-5
);
```

## Fact Tabloları

### fact_tuketim (P0-2 — KRİTİK)
```sql
CREATE TABLE fact_tuketim (
  id BIGSERIAL PRIMARY KEY,
  il_kodu INT NOT NULL REFERENCES dim_il(il_kodu),
  tarih_id INT NOT NULL REFERENCES dim_tarih(tarih_id),
  grup_id INT NOT NULL REFERENCES dim_tuketici_grubu(grup_id),
  baglanti TEXT NOT NULL,   -- 'iletim' | 'dagitim'  (GRAIN parçası!)
  tuketim_mwh NUMERIC(16,3),
  ingestion_batch_id BIGINT NOT NULL REFERENCES ingestion_batch(batch_id),
  is_active BOOLEAN NOT NULL DEFAULT true,
  -- Batch tekilliği (duplicate önleme):
  CONSTRAINT uq_fact_tuketim_batch
    UNIQUE (il_kodu, tarih_id, grup_id, baglanti, ingestion_batch_id)
);
-- Aktif sürüm (batch_id YOK — tek aktif garanti):
CREATE UNIQUE INDEX uq_fact_tuketim_active
  ON fact_tuketim (il_kodu, tarih_id, grup_id, baglanti)
  WHERE is_active;
```

### Diğer fact (aynı desen: batch_id + is_active + iki kısıt)
- **fact_uretim:** NK (il_kodu, tarih_id, kaynak_id, lisans_id); kurulu_guc_mw, uretim_mwh
- **fact_abone:** NK (il_kodu, tarih_id, grup_id); abone_sayisi
- **fact_serbest_tuketici:** NK (il_kodu, tarih_id, tur, grup_id); tuketim_mwh, tuketici_sayisi
  (tur: gerçek T13 değerleri — 'Serbest Tuketici' / 'ST Olma Hakki Bulunmayan
  Aboneler' / 'ST Olma Hakkini Kullanmayan Aboneler', 2026-08-30 doğrulandı)
- **fact_hava_aylik:** UNIQUE(il_kodu, tarih_id); t_ort, hdd, cdd, radyasyon, ruzgar
  + **fact_hava_aylik_log:** old_data/new_data JSONB (tüm ölçüm snapshot)

## İşlem & Config Tabloları
- **job_status:** correlation_id, status CHECK(queued/running/succeeded/failed/retrying/dead_letter),
  attempt_count, locked_by, heartbeat_at, next_retry_at
- **sistem_parametre:** (anahtar PK, deger) → hdd_baz_c=18, cdd_baz_c=22, hava_norm_yil=10, tuketim_norm_yil=5
- **kpi_esik:** (kpi_id, surum PK), yesil/sari/kirmizi bantları, yon
- **il_baz_sicaklik:** (Faz 3) il bazlı override
- **audit_log:** append-only (revoke update/delete)

## İlişki Özeti
- dim_tarih 1→N tüm fact · dim_il 1→N tüm fact
- dim_kaynak 1→N fact_uretim · dim_lisans 1→N fact_uretim
- dim_tuketici_grubu 1→N fact_tuketim, fact_abone
- source_asset 1→N ingestion_batch 1→N tüm fact
