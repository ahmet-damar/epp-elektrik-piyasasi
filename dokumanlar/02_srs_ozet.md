# EPP — SRS v1.5 Özet + Kritik P0 Kuralları

Bu dosya, kod üretiminde ASLA ihlal edilmemesi gereken kuralları içerir.
Kaynak: EPP_SRS_Teknik-Gereksinim_v1.5.

## KRİTİK MİMARİ KURALLAR (P0)

### P0-2: fact_tuketim grain — baglanti dahil
- Doğal anahtar: `(il_kodu, tarih_id, grup_id, baglanti)`
- `baglanti ∈ {iletim, dagitim}` — NOT NULL, grain'in parçası
- İletim ve dağıtım AYRI satırlardır; birleştirilmez
- **İKİ AYRI kısıt gerekir (karıştırma!):**
  - Aktif index (batch_id YOK):
    `CREATE UNIQUE INDEX uq_fact_tuketim_active ON fact_tuketim
     (il_kodu, tarih_id, grup_id, baglanti) WHERE is_active;`
  - Batch tekilliği (batch_id VAR):
    `UNIQUE (il_kodu, tarih_id, grup_id, baglanti, ingestion_batch_id)`
- **UYARI:** Aktif index'e ASLA batch_id ekleme → tek-aktif-sürüm bozulur.

### P0-3: source_asset — dosya VE api ayrımı
- `source_kind ∈ {file, api}` (CHECK)
- file ise: `file_name`, `file_hash` NOT NULL
- api ise: `source_uri`, `request_hash` NOT NULL
- Hava (Open-Meteo) API kaynağıdır; dosyası yoktur.

### P0-5: ingestion_batch — parser sürümlü yeniden işleme
- `UNIQUE (source_asset_id, parser_version, schema_version)`
- Aynı dosya, düzeltilmiş parser ile YENİDEN işlenebilir (yeni batch).

### P0-4: Aktivasyon transaction — doğal anahtar bazlı
- Eski pasifleme ile yeni aktifleme AYNI doğal-anahtar kapsamını kullanır.
- Tek transaction; eşzamanlılık için advisory lock önerilir.

### P0-6: KPI faz kapsamı
- Faz 0 production: KPI-01..10, 13, 23, 24
- KPI-11/12 Faz 0'da yalnız veri altyapısı (HDD/CDD); β/γ hesap Faz 3.

## KONFIGÜRASYON KURALLARI (OD)
- **OD-1:** HDD baz=18°C, CDD baz=22°C — `sistem_parametre`'den oku (koda gömme)
- **OD-2:** Hava normu 10 yıl SABİT; tüketim normu 5 yıl rolling
- **OD-3:** KPI eşikleri `kpi_esik` config tablosunda; PO onaylı
- **OD-4:** Yıllık=yıllık toplamda otoriter, aylık=ay içi otoriter; sapma işaretlenir

## SÜRÜMLEME KURALI
- Veriler ÜZERİNE YAZILMAZ; yeni batch yeni satır ekler.
- Her fact tablosunda `is_active`; raporlama aktif sürüm üzerinden.
- Hava (fact_hava_aylik): güncel kayıt (UPSERT) + JSONB değişiklik logu.

## VERİ KALİTE KURALLARI (parser)
- Negatif tüketim/üretim/abone → satırı REDDET
- Bilinmeyen il/grup/kaynak → KARANTİNA + uyarı
- İl toplamı ↔ 'TÜRKİYE' satırı ±%0,5 mutabık
- Boş hücre = 0 DEĞİL, NULL

## GÜVENLİK
- Roller: admin, data_operator, viewer (RLS zorunlu)
- service_role anahtarı yalnız backend; browser'a ASLA
- Sırlar env'de; parametreli sorgu; audit_log (append-only)

## ADLANDIRMA
- snake_case, Türkçe karaktersiz kolon adı
- il referansı: `il_kodu` (plaka, dim_il.il_kodu'ya FK) — 'il_id' DEĞİL

## ROW LEVEL SECURITY (RLS) ve ROL AYRICALIKLARI
- Tüm uygulama tablolarında Row Level Security (RLS) etkinleştirilecektir. Bu, deny-by-default davranışı sağlar: politika oluşturulmadan hiçbir role erişim verilmez.
- Supabase sistem tablolarına dokunulmayacaktır.
- `service_role` ve `postgres` rollerine dokunulmaz; yalnızca browser-facing roller (anon, authenticated) üzerindeki otomatik ayrıcalıklar geri alınır.

Uygulama için oluşturulan SQL dosyası: `db/schema.sql` — içerik özet:
- `REVOKE ALL ON SCHEMA public FROM anon, authenticated;`
- `REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;`
- `REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;`
- `REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;`
- Her uygulama tablosu için `ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;`

Notlar:
- RLS etkinleştirmek yalnızca deny-by-default sağlar; uygulama ihtiyaçlarına göre her tablo için uygun POLICY (USING/TO) eklenmelidir.
- Yeni tablo eklendiğinde `db/schema.sql` güncellenmeli ve ilgili politika tanımları sağlanmalıdır.
- Bu değişiklikler tarayıcıya doğrudan erişim veren rollerin (anon/authenticated) otomatik izinlerini kaldırır; frontend erişimi için açık, güvenli politikalar oluşturulmalıdır.
