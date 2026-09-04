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

## 2026-08-31 (kapanış) — Ocak-Haziran 2026 aktif, 2 ek bulgu ele alındı

**Aktif/doğrulanmış dönemler (6/6):** `dim_tarih` = 202601..202606, hepsi
`is_active=true` — batch_id 3 (Ocak, T13 fix sonrası), 10 (Şubat), 12
(Mart), 13 (Nisan), 14 (Mayıs), 15 (Haziran). Eski/bozuk-parser'lı batch'ler
(1, 4-8) hiçbir zaman aktive edilmedi, zararsız şekilde `succeeded`/`running`
durumunda DB'de iz olarak duruyor.

| Tarih | fact_uretim | fact_abone | fact_tuketim | fact_serbest_tuketici |
|---|---|---|---|---|
| 202601 | 521 | 405 | 485 | 1170 |
| 202602 | 836 | 405 | 485 | 1169 |
| 202603 | 504 | 405 | 485 | 1169 |
| 202604 | 529 | 405 | 482 | 1162 |
| 202605 | 531 | 405 | 483 | 1167 |
| 202606 | 528 | 405 | 484 | 1172 |

**KPI durumu (dashboard varsayılanı = en son dönem, 202606):**
- Çalışıyor: KPI-01 (126.113 MW), KPI-08 (24,10 TWh), KPI-09, KPI-10.
- "Veri yok" (bilinen, tasarım gereği): KPI-02/03/05/06/07 (uretim_mwh
  il×kaynak grain'inde yok), KPI-13 YoY (önceki yıl verisi yok, beklenen).
- **KPI-11/12 hâlâ "hesaplanamaz"** — sebep: hava verisi yalnız Ocak
  2026 için var, Şubat-Haziran hiç çekilmedi (bu oturumun kapsamı dışında
  bırakıldı, bkz. aşağıda "yarından devam"). β/γ regresyonu için tek veri
  noktası yeterli değil.
- **KPI-23/24 hâlâ "veri yok" (Haziran için)** — aynı sebep; Ocak
  seçilirse hesaplanabilir durumda.
- **KPI-25/26 hâlâ "hesaplanamaz"** — sebep: CAGR en az 2 farklı yıl
  gerektiriyor, hâlâ tek yıl (2026) içindeyiz. Bu, öngörülen/beklenen bir
  durum, veri eksikliği değil.

**Şubat fact_uretim anomalisi (836 satır, diğer aylar 504-531) — TEŞHİS
EDİLDİ, KOD HATASI DEĞİL, DÜZELTME YAPILMADI.** Kök neden: EPDK'nın Şubat
raporunda "Doğal Gaz" kurulu güç sütunu her il için `0.0` olarak dolu
yazılmış (333 hücre); Mart'tan itibaren aynı (sıfır kapasiteli) hücreler
tamamen BOŞ bırakılmış. Parser zaten P0 kuralına ("boş hücre=NULL, 0
DEĞİL") göre doğru davranıyor — bu, kaynak dosyanın kendi raporlama
tutarsızlığı. Doğrulama: toplam kurulu güç makul ve tutarlı kaldı (Şubat
124.320 MW → Mart 125.078 MW, doğal artış) — satır sayısı farkı TOPLAM
DEĞERİ etkilemiyor, çünkü 0 zaten toplama katkı sağlamıyordu. Kod
değiştirilmedi; bu, gelecekte tekrar karşılaşılırsa "neden yine böyle"
sorusuna hazır cevap olsun diye burada belgelendi.

**`psycopg.errors.DuplicatePreparedStatement` — DÜZELTİLDİ** (commit
`769074c`). Kök neden: Supabase'in transaction pooler'ı (pgbouncer),
psycopg3'ün otomatik server-side prepared statement'larını (varsayılan
eşik=5 kullanım) bağlantılar arası paylaşmıyor/temizlemiyor. 5 production
kod yolunda aynı desen vardı, hepsine `prepare_threshold=None` eklendi:
`worker/db.py` (`get_db_connection()` — dashboard'un ana yolu),
`worker/job_worker.py`, `worker/scripts/onayla.py`, `worker/scripts/
backfill.py`, `worker/jobs/fetch_weather.py`. Test dosyalarına
dokunulmadı (CI'ın düz `postgres:16`'sında pgbouncer yok, risk yok).
Doğrulama: CI'da (ruff/mypy/pytest, gerçek `postgres:16` entegrasyon
testleri) tamamen yeşil + canlı DB'ye karşı aynı bağlantıda 8 tekrarlı
sorgu (varsayılan eşiği aşan) hatasız çalıştı.

**Yarından devam edilecekler:**
1. **Şubat-Haziran için Open-Meteo hava verisi çek** (`fetch_weather.py
   --tarih-id 202602` ... `202606`) — KPI-11/12/23/24'ü tüm 6 ay için
   gerçek hale getirir. Bugün BİLİNÇLİ OLARAK başlanmadı (kapsam/zaman
   nedeniyle).
2. **Faz 4 (Tahminleme) / Faz 5 (EPİAŞ) kavramsal tasarımı** — daha önce
   "2-3 ay daha gerçek veri biriktirelim" kararıyla ertelenmişti; artık
   6 ay veri var, karar gözden geçirilebilir.
3. *(Düşük öncelik)* T7 çoklu-ay format düzeltmesi — hâlâ bilinen-gap
   (bkz. yukarıdaki bölüm), `_mutabakat()` sonucu güvenilmez kalmaya
   devam ediyor ama fact tablosuna yazmadığı için risk düşük.

## 2026-09-01 — Word (.docx) 2024 tarihsel aktarımı: ilk gerçek yükleme

Kaynak: `dokumanlar/07_word_parser_kapsam.md` (teşhis + Karar 1/2). Bu turda
**kod yazıldı ve gerçek Supabase'e yazıldı**: `worker/scripts/word_ortak.py`
(ortak tablo-bulma çekirdeği) + `worker/scripts/word_2024.py` (2024'e özel
tarif — T11-karşılığı→`fact_tuketim`, T10-karşılığı→`fact_abone`;
T13/T1/T4-karşılığı Karar 1 gereği bu turda YOK). `requirements.txt`'ye
`python-docx` eklendi.

**Karar 2 netleştirildi** (bkz. `07_word_parser_kapsam.md`): Sanayi dışlaması
YALNIZ `fact_tuketim`'e özgü (`baglanti` yalnız onun doğal anahtarında var) —
`fact_abone`'de Sanayi normal yüklenir. Mart 2024 dry-run'ında doğrulandı:
T11 81×4=324 satır (Sanayi hariç), T10 81×5=405 satır (Sanayi dahil).

**Dosya→ay eşlemesi (MANIFEST_2024):** gerçek dosya adları opak portal
hash'leri, tarih taşımıyor (`backfill.py`'deki manifest gerekçesiyle aynı).
Hafif bir `zipfile`+regex taramasıyla (python-docx açmadan) 12 aday bulundu;
**her biri işlenirken kendi T11-karşılığı başlığından ("...{Ay} {Yıl}
Döneminde...") ay/yıl yeniden çıkarılıp manifest'le karşılaştırıldı**
(`_ay_yil_dogrula`) — 12/12 doğrulandı, uyuşmazlık çıkmadı.

**Bulunan ve düzeltilen bir script bug'ı (idempotency):**
`ingest.kaynak_asset_olustur()` HER ÇAĞRIDA yeni bir `source_asset` satırı
açar (bilinçli — bir audit log). Mart 2024 önce `--ay 3` ile tek başına
gerçek yüklendi (`batch_id=16`), sonra tüm-yıl çalıştırması (henüz
idempotency kontrolü yokken) Mart'ı BİR DAHA işledi (`batch_id=19`, TAM
AYNI 323 fact_tuketim + 405 fact_abone satırı, `is_active=false`). Fark
edildi (DB'den doğrudan sorgulanarak, çıktıdaki `[ATLA]` mesajının
eksikliğinden şüphelenilerek) — **hiçbir aktivasyon yapılmadan önce**
yakalandı, dolayısıyla `is_active=true` hiçbir satır etkilenmedi. Temizlik:
`batch_id=19`'un veri satırları silindi, batch `'failed'` + açıklayıcı
`error_summary` ile işaretlendi (silinmedi — audit izi kalıcı), yeni bir
`audit_log` satırı (`olay: mukerrer_batch_temizlendi`) düşüldü. **Kalıcı
düzeltme:** `word_2024.py`'nin `isle_ay()`'i artık her ay başında
`source_period` bazlı bir idempotency kontrolüyle açılıyor — aynı ay ikinci
kez çalıştırılırsa `[ATLA]` ile sessizce (ama açıkça loglanarak) çıkar,
yeni bir batch/satır seti YARATMAZ.

**Sonuç — 12/12 ay gerçek Supabase'e yüklendi, ay/yıl+satır sayısı
doğrulandı:**

| Dönem | batch_id | red | Durum |
|---|---|---|---|
| 2024-01 | 17 | 1 | ✅ aktive edildi (2026-09-01 kapanışında, bkz. aşağıda) |
| 2024-02 | 18 | 0 | ✅ aktive edildi |
| 2024-03 | 16 | 1 | ✅ aktive edildi (2026-09-01 kapanışında, bkz. aşağıda) |
| 2024-04 | 20 | 1 | ✅ aktive edildi (2026-09-01 kapanışında, bkz. aşağıda) |
| 2024-05..12 | 21-28 | 0 | ✅ aktive edildi (9 ay toplam: 02,05,06,07,08,09,10,11,12) |

3 ayda (Ocak/Mart/Nisan) `kpi.dogrula_tuketim()`'in sıfır-tolerans kuralı
(`tuketim_mwh < 0` → red) tam olarak 1'er satırı reddetti — **parser hatası
DEĞİL**: üçü de "Tarımsal" grubunda, farklı il/ay, kaynak dosyanın kendi
"Genel Toplam" sütunuyla aritmetik olarak tutarlı küçük negatif değerler
(Ağrı -1,63 MWh Ocak; Malatya -63,96 MWh Mart; Sivas -100,75 MWh Nisan —
muhtemelen EPDK'nın kendi fatura düzeltmeleri). Mevcut proje politikası
(`otomatik_onaya_uygun()`, 2026-08-30 kararı) gereği red>0 olan batch'ler
otomatik aktive edilmez, insan onayı bekler — bu 3 ay bilinçli olarak
`running` durumunda bırakıldı, elle onay için: `python -m worker.scripts.
onayla --batch-id 17/16/20 --actor "..."`.

**Kapsam dışı (Karar 1 gereği, bu turda yok):** T13-karşılığı
(fact_serbest_tuketici) ve T1/T4-karşılığı (fact_uretim, henüz incelenmedi).

## 2026-09-01 (kapanış) — 3 bekleyen batch onaylandı, 2024 tamamlandı

Yukarıdaki 3 bekleyen batch (Ocak/Mart/Nisan 2024, batch_id 17/16/20)
incelendi: red satırları tutarlı bir desen (bugün sabahki Malatya -63,96 MWh
dahil, toplam 5 satır — hepsi "Tarımsal" grubunda, kaynağın kendi "Genel
Toplam" sütunuyla aritmetik olarak uyuşan, bilinen negatif-fatura-düzeltmesi
sınıfı, parser hatası değil). Elle onaylandı:

```
python -m worker.scripts.onayla --batch-id 17 --actor "ahmet-manual"  # Ocak 2024
python -m worker.scripts.onayla --batch-id 16 --actor "ahmet-manual"  # Mart 2024
python -m worker.scripts.onayla --batch-id 20 --actor "ahmet-manual"  # Nisan 2024
```

**Doğrulama (DB'den doğrudan sorgulanarak):**
- `fact_tuketim`: 2024-01..12'nin TAMAMI `is_active=true`, tarih_id başına
  tek aktif satır seti (323 satır — 1 red hariç — 3 ay için; 324 satır 9 ay
  için); hiçbir ay için birden fazla aktif `ingestion_batch_id` YOK
  (çelişki kontrolü temiz).
- `fact_abone`: 2024-01..12'nin TAMAMI `is_active=true`, her ay 405 satır.
- `ingestion_batch`: 12 `succeeded` (2024'ün her ayı için 1) + 1 `failed`
  (batch_id=19, Mart'ın temizlenen mükerrer kopyası — bkz. yukarıdaki
  idempotency bug notu).
- `audit_log`: batch_id 16/17/20 için 3 yeni `UPDATE` satırı,
  `payload->>'olay'='batch_onaylandi'`, **`actor_name='ahmet-manual'`**
  olarak görünür (kim onayladığı DB'de kalıcı).

**2024'ün 12 ayı da artık tamamen aktif ve tutarlı.** Bu turda kod
değişikliği YAPILMADI — yalnız aktivasyon + doğrulama.

**Bu gece YENİ kapsam açılmadı** (bilinçli karar): 2023/2025'e veya
T1/T4-karşılığına geçilmedi, yalnız 2024'ün kapanışı tamamlandı.

**Yarın nereden devam edilecek (sırayla):**
1. **2023 için ayrı bir tarif yaz** (`worker/scripts/word_2023.py`,
   `word_ortak.py` çekirdeğini kullanarak — 2024'ün desenini birebir
   kopyalama, kendi başlık/sütun farklarını doğrula; bkz.
   `07_word_parser_kapsam.md` Bulgu 2 — "yakın=güvenilir" varsayımı
   burada da geçerli değil, her yıl kendi metniyle doğrulanmalı).
2. **Sonra 2025** — 12 dosyası bu turda YAN ÜRÜN olarak zaten bulundu
   (`word_2024.py`'nin manifest taramasında, bkz. modül notu) ama HİÇ
   işlenmedi; 2023 tarifi kapandıktan sonra sırada.
3. **T13-karşılığı (Karar 1) ve T1/T4-karşılığı (fact_uretim) hâlâ kapsam
   dışı** — 2023/2025 tarifleri de aynı şekilde bu ikisini atlayacak,
   ayrı bir karar/iş kalemi gerekiyor (Word'de T13 kaynağı hiç yok; T1/T4
   Word karşılığı bu session'da hiç incelenmedi).
4. `word_2024.py`'nin parse mantığı için dedike pytest regresyon testi
   yok (yalnız script-içi assertion'lara güveniliyor) — 2023 tarifine
   başlamadan önce ya da onunla birlikte eklenmesi düşünülebilir.

## 2026-09-02 — 2023 Word raporları yüklendi (12/12), KPI-25/26 durumu netleşti

**2023 için ayrı tarif** (`worker/scripts/word_2023.py`, `word_ortak.py`
çekirdeğini yeniden kullanarak) yazıldı ve 12/12 ay gerçek Supabase'e
yüklendi. **2023 tek bir şablon DEĞİL** — Ocak-Nisan "Tablo 2.5/2.6" +
kısaltılmış grup etiketleri kullanırken, Mayıs-Aralık "Tablo 5.2" + tam
etiketler kullanıyor (2024'ün formatıyla örtüşen taraf) — yıl içi bir EPDK
şablon geçişi. Karşılaşılan ve `worker/parser.py`'a DOKUNMADAN, yalnız
`word_2023.py`'ye özel çözülen 3 yeni sürpriz sınıfı: (1) "Kamu ve Özel
Hizmetler" için 4 farklı kısaltma varyantı; (2) `ADIYAMAN*` gibi dipnot
yıldızlı il adları; (3) `HAKKÂRİ` gibi inceltme-işaretli eski yazım.

**Aktivasyon — 4 ay otomatik (temiz), 8 ay elle, TEK TEK onaylandı (toplu
değil, kullanıcı talebiyle):** Ağustos/Eylül/Ekim/Kasım red=0 otomatik
aktive oldu. Kalan 8 ayda toplam 16 kırmızı satır vardı (2024'ün 3 satırına
göre çok daha yoğun) — her biri "Genel Toplam" ile aritmetik tutarlılık
açısından örneklem doğrulamasından geçirildi (bkz. aşağıdaki not), sonra
kullanıcı hepsini tek tek (`--batch-id 29,30,31,33,40` sonra ayrı bir turda
`32,34,35`) onayladı. **2023'ün 12 ayı da artık tamamen aktif, çelişki yok.**

**Not — 3 batch'te (32=Nisan, 34=Haziran, 35=Temmuz) sıra dışı bir desen:**
kırmızı satırın grubu "Tarımsal" değil, **Kahramanmaraş/Kamu ve Özel
Hizmetler**, **Batman/Aydınlatma**, **Şanlıurfa/Aydınlatma** idi — üçü de
**6 Şubat 2023 deprem bölgesindeki iller**. Kullanıcı talebiyle özellikle
doğrulandı: üçü de "Genel Toplam" sütunuyla tam aritmetik tutarlı (fark
0,0000) — parser/hizalama hatası DEĞİL. Kahramanmaraş'ın Nisan satırında
ayrıca Mesken VE Tarımsal sıfır — muhtemelen deprem sonrası fatura/mahsup
düzeltmeleri bu bölgede birden fazla grupta sıra dışı değerler olarak
yansımış. **Bu not buraya bilinçli düşüldü:** ileride biri bu 3 batch'in
audit_log'unda "neden Tarımsal değil de Aydınlatma/Kamu grubunda kırmızı
satır var" diye şüphelenip yeniden araştırmaya kalkmasın — köküne kadar
inildi, açıklaması var, kod sorunu değil.

**KPI-25 (tüketim CAGR) — hâlâ GÜVENİLMEZ, sebebi netleşti:**
`worker/analytics.py:yillik_tuketim_serisi_getir()` `fact_tuketim`'in TÜM
gruplarını toplar. 2023/2024 (Word) Sanayi'yi HİÇ içermiyor (Karar 2), 2026
(Excel) içeriyor — üstüne 2026 yalnızca 6 aylık kısmi veri (Ocak-Haziran),
2023/2024 tam 12 ay. İkisi birden devreye girince naif hesap **-2,2%**
çıkıyor (2023→2026, n=3) — bu gerçek bir düşüş DEĞİL, iki ayrı ölçüm
biçiminin (Sanayi dahil/hariç + tam-yıl/yarım-yıl) çarpışması. **Sanayi
hariç tutularak, iki TAM yıl (2023↔2024) karşılaştırıldığında anlamlı bir
sonuç çıkıyor: +9,4%** — ama bu KPI-25'in tanımladığı "toplam tüketim CAGR"
değil, "Sanayi-hariç tüketim CAGR". KPI-25'in mevcut hesaplama sorgusuna
DOKUNULMADI (kapsam dışı, yalnız teşhis istendi) — düzeltme için ya (a)
Sanayi'yi 2023/2024'e bir şekilde tamamlamak (kaynakta yok, mümkün değil),
ya (b) sorguyu yalnızca TAM yıllar + tutarlı grup kümesiyle sınırlamak, ya
da (c) "Sanayi-hariç" ayrı bir KPI-25-varyantı tanımlamak gerekiyor — ayrı
bir karar/iş kalemi.

**KPI-26 (yenilenebilir kurulu güç CAGR) — hâlâ hesaplanamıyor:**
`fact_uretim`'de yalnızca 2026 var (T1/T4-karşılığı Word tarafında hiç
işlenmedi, Karar 1 kapsam dışı listesinde). En az 2 farklı yıl gerekiyor
(`cagr_seriden_hesapla()`), tek yılla `None` döner. T1/T4 işlenmeden
KPI-26 açılamaz.

**Yarından devam:**
1. 2025 için ayrı tarif (`word_2025.py`) — 12 dosyası zaten bulundu
   (`word_2024.py` modül notu), hiç işlenmedi.
2. T1/T4-karşılığı (fact_uretim) — hem T13/Karar 1'in hem KPI-26'nın
   önünü açar, öncelik kazandı.
3. KPI-25'in Sanayi-dahil/hariç + tam-yıl/kısmi-yıl karışıklığı için bir
   karar gerekiyor (yukarıdaki 3 seçenek) — dashboard'a yanlış bir "-2,2%"
   sızmadan önce ele alınmalı.
4. `word_2023.py`/`word_2024.py` için dedike pytest regresyon testi hâlâ
   yok.

## 2026-09-02 (devam) — 2025 Word raporları yüklendi (12/12), 36 ay tamamlandı

`worker/scripts/word_2025.py` yazıldı ve 12/12 ay gerçek Supabase'e
yüklendi. **2023'ün aksine 2025 tek tip bir şablon** — 12 ay ön-taramada
tek tek kontrol edildi (varsayılmadı): T11 başlığı hepsinde birebir aynı,
T10'da yalnız 1 alias gerekti (`Kamu/Özel/Diğer`, 2024 Mart'la aynı).

**Aktivasyon:** 8 ay otomatik (Mart, Mayıs, Haziran, Temmuz, Ağustos,
Eylül, Ekim, Aralık), 4 ay (Ocak=41, Şubat=42, Nisan=44, Kasım=51) elle
onaylandı — onaydan ÖNCE `source_asset`+`ingestion_batch`+`audit_log`
doğrudan DB'den sorgulanarak red satırları (il/grup/değer) önceki dry-run
taramasıyla birebir karşılaştırıldı, uyuşmazlık çıkmadı. **2023+2024+2025
= 36 ayın TAMAMI artık `is_active=true`**, DB'den doğrulandı (36/36,
çelişki yok).

**Gözlem (kesin değil, ileride araştırılabilir):** "Aydınlatma + güneydoğu
illeri" kırmızı-satır deseni hem 2023 (Haziran: Batman -1.259,11 MWh;
Temmuz: Şanlıurfa -2.911,37 MWh) hem 2025'te (Nisan: Batman/Mardin/Siirt/
Şanlıurfa/Şırnak, 5 il birden, hepsi Aydınlatma) tekrar ediyor. 2023'ün
deprem-bölgesi vakaları (Kahramanmaraş/Batman/Şanlıurfa, yukarıda) 6 Şubat
2023 depremiyle açıklanabilirken, 2025 Nisan'ının aynı bölgede AYNI grupta
(Aydınlatma) tekrar etmesi — deprem 2 yıl önce olduğuna göre — muhtemelen
depremden BAĞIMSIZ, bölgesel/yıllık bir mahsuplaşma/fatura döngüsü olduğuna
işaret ediyor (örn. belediye aydınlatma sözleşmelerinin yıllık dönemsel
kapanışı). Kesin değil — ayrı bir araştırma konusu, kod/veri sorunu değil.

**Yarından devam (güncellendi):**
1. **T1/T4 (kurulu güç) için YENİ bir teşhis turu** — T11/T10 gibi kendi
   keşif turunu hak ediyor, hiç incelenmedi. Hem Karar 1'in hem KPI-26'nın
   önünü açar, öncelik kazandı.
2. KPI-25'in Sanayi-dahil/hariç + tam-yıl/kısmi-yıl karışıklığı için bir
   karar gerekiyor (yukarıdaki 3 seçenek).
3. `word_2023.py`/`word_2024.py`/`word_2025.py` için dedike pytest
   regresyon testi hâlâ yok.
4. 2022 ve öncesi yıllara genişletme — 2022'nin 12 dosyası da yan ürün
   olarak zaten bulundu, hiç işlenmedi.

## 2026-09-02 (T4) — T1/T4 teşhisi + T4 implementasyonu, KPI-26 düzeltmesi

**Teşhis (Bulgu 5, `07_word_parser_kapsam.md`):** 4 dosya (2023 iki
şablonu + 2024 + 2025) incelendi, kod yazılmadı. Kritik asimetri: **T1
(Lisanslı) için il×kaynak birleşik tablo Word'de HİÇ YOK** (yalnız il-only
ve kaynak-only ayrı tablolar var) — **T4 (Lisanssız) için VAR**
("...İllere ve Kaynaklara Göre Dağılımı (MW)"), grain `fact_uretim`'in
doğal anahtarına uyuyor. **Karar 3:** T1 kapsam dışı (T13 gibi), T4 tek
başına yüklenecek.

**İmplementasyon (aynı gün, uygulama turu):** `word_ortak.py`'ye
`t4_tablosunu_bul()`; her 3 yıl script'ine `t4_oku()` (kapasitesi sıfır
olan iller — 2023'te bazı aylarda satır olarak hiç görünmüyor — için tüm
kaynak türlerini AÇIKÇA 0 yazan, "beklenen=81 satır" yerine tablonun kendi
`Genel Toplam`'ıyla aritmetik tutarlılık kontrol eden bir okuyucu) + AYRI
bir `isle_ay_t4()` (kendi `parser_version` = `word-YYYY-t4-v1`, T11/T10'un
ZATEN aktif/succeeded batch'lerine DOKUNMADAN — farklı parser_version =
P0-5 gereği meşru yeni batch) eklendi.

**Sonuç — 36/36 ay (2023+2024+2025) dry-run VE gerçek yükleme, HEPSİ
temiz:**

| Yıl | Batch_id aralığı | Ay | Red | Kaynak sütunu sayısı |
|---|---|---|---|---|
| 2023 | 53-64 | 12 | 0 | 5 (Biyokütle/Doğal Gaz/Güneş/Hidrolik/Rüzgar) |
| 2024 | 65-76 | 12 | 0 | 5 (Oca-Mar) → 6 (Nis-Ara, Linyit eklendi) |
| 2025 | 77-88 | 12 | 0 | 6 (Linyit dahil, tüm yıl) |

`fact_uretim`'e toplam 16.281 satır yazıldı (2023: 4.860 = 81×5×12;
2024: 5.589 = 81×5×3+81×6×9; 2025: 5.832 = 81×6×12), hepsi
`is_active=false`. **Kullanıcı talebiyle `--onayla` HİÇ ÇAĞRILMADI** — 36
batch de (53-88) `running` durumda, elle onay bekliyor (T9/T10
disiplininin aynısı: `python -m worker.scripts.onayla --batch-id N --actor
"..."`). T11/T10'un mevcut aktif verisi (fact_tuketim 11.620 aktif satır)
doğrulandı, dokunulmadı.

**KPI-26 düzeltmesi (kod değişikliği, gerekçesi burada):** T4 yüklenince
`fact_uretim`'de 2023-2025 için ARTIK veri var ama YALNIZ Lisanssız
(Türkiye'nin toplam yenilenebilir kapasitesinin küçük bir kesri — büyük
rüzgar/güneş/hidrolik çiftlikleri Lisanslı'dır). Bu, 2026 (Excel, Lisanslı+
Lisanssız TAM) ile aynı CAGR serisine karışırsa KPI-25'in Sanayi dahil/
hariç sorunuyla AYNI kök nedenden sahte bir sayı üretirdi. **Çözüm:**
`worker/analytics.py:yillik_yenilenebilir_kurulu_guc_serisi_getir()`
artık yalnız Lisanslı verisi OLAN yılları seriye alıyor (alt sorgu) —
Word'ün Lisanssız-only yılları otomatik "veri yok" (None/"hesaplanamaz")
sayılıyor, KPI-25 gibi belgelenip kod değişikliği ERTELENMEDİ, doğrudan
düzeltildi (mevcut testler — `test_yillik_yenilenebilir_kurulu_guc_serisi_
yil_sonu_alir` zaten Lisanslı veriyle kurulu, bozulmadı). **KPI-25 bu
düzeltmeyi almadı** — hâlâ açık bir karar bekliyor (bkz. yukarıdaki
2026-09-01 bölümü).

**Yarından devam (güncellendi — tam liste `07_word_parser_kapsam.md`'de):**
1. ~~36 bekleyen T4 batch'i (53-88) için aktivasyon kararı~~ **YAPILDI
   (2026-09-02, aynı gün devam)** — 4 bağımsız kontrolden geçti, 36/36
   aktive edildi. Bkz. aşağıdaki "(T4 aktivasyon)" bölümü.
2. KPI-25 için hâlâ bir karar gerekiyor (KPI-26'nın aksine kod
   düzeltilmedi).
3. ~~Karar 1'in (artık T13 VE T1) somut mekanizması~~ **YAPILDI
   (2026-09-02)** — `veri_kapsam_disi` tablosu. Bkz. aşağıdaki
   "(kapsam dışı mekanizması)" bölümü.
4. T4 dahil regresyon testleri, 2022 genişletmesi.

## 2026-09-02 (T4 aktivasyon) — 4 bağımsız kontrol, 36/36 batch aktive edildi

Aktivasyon öncesi kullanıcı talebiyle 4 bağımsız kontrol yapıldı (hiçbiri
`worker/scripts`'teki `t4_oku()`/`isle_ay_t4()` kodunu ÇAĞIRMADI — paylaşılan
bir kod hatası varsa yakalanabilsin diye):
1. **Kaynak çapraz doğrulama:** 4 örnek ay (2023-Eylül, 2024-Mart,
   2025-Ekim, ve en büyük sıçramalı 2024-Nisan) — bağımsız bir script
   `.docx`'u yeniden açtı, `Genel Toplam`'ı okudu, DB'deki batch
   toplamıyla karşılaştırdı. 3'ü yuvarlama seviyesinde (≤0,08 MW), biri
   (Nisan 2024) **tam 0,0000 MW fark**.
2. **Ay-ay trend:** 36 ayın tamamında >%5 sıçrama taraması — 3 bulundu
   (2024-02/04/07), kaynak kırılımı hepsinin neredeyse tamamen **Güneş**
   (lisanssız/çatı solar) kaynaklı olduğunu gösterdi — Türkiye'nin o
   dönemki bilinen büyüme trendiyle örtüşüyor, tek yönlü, açıklanabilir.
3. **Linyit geçişi:** Nisan 2024 öncesi Linyit satırı DB'de HİÇ yok (0
   değil), sonrası her ayda tam 81 satır — doğrulandı.
4. **pytest:** `test_yillik_yenilenebilir_kurulu_guc_serisi_yil_sonu_alir`
   canlı DB'ye karşı PASSED (yerelde `DATABASE_URL` export edilerek
   çalıştırıldı, varsayılan olarak SKIP oluyordu).

**Sonuç: 36/36 batch (53-88) aktive edildi, 0 UYARI.** `fact_uretim`'de
2023-2025'in tamamı `is_active=true`, eksik/çelişki yok, T11/T10
dokunulmadan sağlam. Kod (`word_ortak.py`, `word_2023/2024/2025.py`,
`worker/analytics.py`) + dokümanlar TEK commit'te (`95ea9be`, ardından bir
`ruff format` düzeltmesi `8bb1eca`) push edildi, CI yeşil.

## 2026-09-02 (kapsam dışı mekanizması) — veri_kapsam_disi tablosu

Karar 1 (T13) ve Karar 3'ün (T1) beklediği "kaynakta yok" işaretleme
mekanizması kuruldu — dim_tarih bayrağı ya da `ingestion_batch.
error_summary` notu DEĞİL (seçenekler arasından), yeni bir tablo:

- **Migration:** `supabase/migrations/20260819_0012_veri_kapsam_disi.sql`
  — `veri_kapsam_disi (tarih_id, fact_tablosu, nitelik, sebep,
  karar_referansi, created_at)`, PK (tarih_id, fact_tablosu, nitelik).
  `fact_tablosu` DB CHECK ile 4'lü whitelist'e (worker/ingest.py
  `_DOGAL_ANAHTAR` ile aynı) kilitli. RLS + viewer/data_operator/admin
  politikaları diğer tablolarla aynı desende. **`.github/workflows/
  ci.yml`'in migration-apply listesine eklendi** (aksi halde CI'ın
  integration testleri bu tabloyu görmez).
- **`worker/pipeline.py:kapsam_disi_isaretle()`:** primitif fonksiyon,
  `ingest.py`'nin diğer primitifleriyle aynı desende (Karar 1'in "paralel
  yol icat etme" ilkesi). Aynı `(tarih_id, fact_tablosu, nitelik)` için
  ikinci çağrı **UPSERT** yapar (hata FIRLATMAZ) — bu tablo `ingestion_
  batch` gibi append-only bir audit izi değil, GÜNCEL bir "durum" kaydı;
  bir backfill script'i aynı dönem için tekrar çağrılabilir, "zaten var"da
  patlamak yerine metni güncellemek daha kullanışlı bulundu.
- **Veri:** 2023-2025'in 36 ayının HEPSİ için 72 satır yazıldı (36×
  `fact_serbest_tuketici`/`(tumu)`/Karar 1 + 36× `fact_uretim`/
  `lisans_durumu=Lisanslı`/Karar 3) — canlı Supabase'e migration doğrudan
  psql/psycopg ile uygulandı (deploy.yml'nin `migrate` job'ı şu an
  `build-push`'a `needs` bağımlılığı üzerinden dolaylı olarak devre dışı
  — `if: false`, Docker/web henüz yok — bu yüzden migration'lar elle
  uygulanıyor, tıpkı 0001-0011'in muhtemelen daha önce uygulandığı gibi).
- **Test:** `worker/tests/test_pipeline_integration.py`'ye
  `kapsam_disi_isaretle()`'nin (a) doğru satırı eklediğini ve (b) aynı
  anahtar için ikinci çağrının UPSERT yaptığını (hata vermediğini,
  sebep/karar_referansi'nin güncellendiğini) doğrulayan testler eklendi.
- **Dashboard/KPI koduna DOKUNULMADI** (bilinçli, kullanıcı talebi) — bu
  tur yalnız mekanizmayı kurdu, Faz 2 dashboard çalışmasında tüketilecek.
- **Commit/push YAPILMADI** — kullanıcı önce gözden geçirecek.

**Yarından devam:**
1. `veri_kapsam_disi`'yi Faz 2 dashboard'una bağlamak (örn. bir ay için
   T13/T1 "bu dönemde mevcut değil" notu göstermek).
2. ~~KPI-25 için hâlâ bir karar gerekiyor.~~ **YAPILDI (2026-09-03, aşağıya
   bkz.)**
3. `word_2023.py`/`word_2024.py`/`word_2025.py` (T4 dahil) için dedike
   pytest regresyon testi hâlâ yok — yalnız script-içi assertion var.
4. 2022 ve öncesi yıllara genişletme.
5. `deploy.yml`'in `migrate` job'ının neden dolaylı olarak devre dışı
   olduğu (build-push'a `needs` bağımlılığı, `if: false`) — Docker/web
   iskeleti gelince gözden geçirilmeli, o zamana kadar migration'lar elle
   uygulanmaya devam edecek.

## 2026-09-03 — KPI-25 düzeltmesi (seçenek b) + yeni KPI-27 metriği (seçenek c)

Yukarıdaki (2026-09-02) 3 seçenekten **b** (KPI-25'i yalnız Sanayi'yi
İÇEREN yıllarla sınırla, KPI-26'daki AYNI disiplin) ve **c** (Sanayi-hariç
ayrı bir metrik) BİRLİKTE uygulandı — biri diğerinin yerine geçmiyor.

**KPI-25 (`worker/analytics.py:yillik_tuketim_serisi_getir`) —
düzeltildi:** sorguya bir alt-sorgu eklendi, yalnız Sanayi grubunu içeren
`dt.yil` değerleri seriye giriyor. Bugün itibarıyla bu tek başına 2026'yı
bırakıyor (2023-2025/Word'de Sanayi hiç yok, Karar 2) — `cagr_seriden_
hesapla()` ≥2 yıl gerektirdiğinden **KPI-25 artık None ('hesaplanamaz')
dönüyor**, önceki yanıltıcı -2,2% YERİNE. 2027+'de ikinci bir Sanayi'li
tam yıl gelince kod değişikliği gerekmeden otomatik seriye girecek.

**KPI-27 (YENİ) — `worker/analytics.py:
yillik_tuketim_sanayi_haric_serisi_getir`:** Sanayi grubu TÜM yıllardan
(2023-2026 dahil) çıkarılıyor (KPI-25'in tersi strateji — yıl filtrelemek
yerine grup filtreleniyor), yalnız TAM yıllar (12 farklı ay,
`dim_tarih.donem_tipi='aylik'` + `ay`) dahil ediliyor — 2026 hâlâ 6 aylık
kısmi olduğundan otomatik dışarıda kalıyor, 12 aya tamamlanınca kod
değişikliği gerekmeden girecek. **KPI-25'İN YERİNE GEÇMİYOR** — resmi
"toplam tüketim" tanımını karşılamıyor (Sanayi hariç), yalnız ek bağlam.

**Canlı sonuç — dikkat, önceki turda bahsedilen +%9,4 (2023↔2024, n=1)
İLE FARKLI bir sayı çıkıyor:** canlı veride 2025 de artık TAM bir yıl
olarak nitelendiğinden (12/12 ay aktif), KPI-27'nin serisi 3 noktaya
(2023, 2024, 2025) çıktı; `cagr_seriden_hesapla()` ilk/son mantığıyla
2023→2025 (n=2) arasını hesaplıyor: **+%6,9**. Bu bir HATA DEĞİL — 2026-
09-02'de yalnız 2 nokta (2023↔2024) vardı, o zamandan beri 2025'in T4
verisi de aktive edildiği (bkz. yukarıdaki "T4 aktivasyon" bölümü) için
fonksiyon şimdi daha fazla nitelikli veriyle daha uzun bir seri
hesaplıyor — tasarım gereği (yeni veri geldikçe otomatik güncellenmesi
İSTENEN davranış), sabit bir sayı değil.

**Test:** `worker/tests/test_analytics_integration.py`'ye 2 yeni test
eklendi — `test_kpi_25_tek_sanayili_yil_hesaplanamaz` (sentinel 2093/2097,
tek Sanayi'li yılla None döndüğünü doğrular) ve `test_yillik_tuketim_
sanayi_haric_serisi_ve_kpi_27_hesaplanir` (sentinel 2094/2095, TAM
formülle +%9,4 üretecek şekilde kurgulanmış değerler + büyük bir Sanayi
"dikkat dağıtıcı" satırı — dışlamanın gerçekten çalıştığını kanıtlıyor).
Var olan `test_yillik_serilerinden_cagr` de güncellendi: (a) her iki
sentinel yıla (2096/2100) bir Sanayi satırı eklendi (aksi halde yeni
filtreyle ikisi de düşer), (b) seri kendi sentinel yıllarına izole edildi
— canlı DB'ye karşı çalıştırıldığında gerçek yılların (2026 artık Sanayi
İÇERDİĞİ için) seriye karışıp ilk/son seçimini bozmasını önlemek için
(CI'nin boş konteynerinde bu risk yok, ama canlı DB'ye karşı denenince
gerçek bir regresyon gibi görünen bir izolasyon açığı ortaya çıkardı —
kök nedeni bulundu, "ortam farkı" denip geçilmedi, aynı izolasyon deseni
yeni testlerle tutarlı hale getirildi).

**Yan bulgu — canlı DB'de test kirliliği bulundu ve temizlendi:** bu
turda KPI-25/27'yi canlı veriyle doğrularken beklenmedik bir `yil=2099`
satırı (445.000 MWh) ortaya çıktı. Kök neden: T4 aktivasyonu sırasında
(2026-09-02) regresyon kontrolü için TÜM pytest paketi (`py -m pytest -v`)
canlı Supabase'e karşı çalıştırılmıştı — `worker/tests/
test_job_worker_integration.py`, `worker/job_worker.py`'nin async
polling yolunu egzersiz ediyor ve bu yol KENDİ commit'lerini yapıyor,
standart `conn` fixture'ının rollback tabanlı izolasyonunu BYPASS ediyor.
Sonuç: sentinel `tarih_id=209912` (yıl 2099) için 4 fact tablosunda
(fact_tuketim: 12, fact_uretim: 14, fact_abone: 12,
fact_serbest_tuketici: 47 satır) + 3 `ingestion_batch` + 3 `source_asset`
+ 1 `dim_tarih` kaydı canlı production DB'de KALICI olarak kalmıştı.
**Temizlik:** 3 turda (ilk deneme FK ihlaliyle güvenle geri alındı, ikinci
tur 4 fact tablosu + ingestion_batch + source_asset'i sildi, üçüncü/geniş
tarama bir yetim `dim_tarih` satırı + ayrı bir üçüncü sızıntı — batch
118/source_asset 116, `test_job_worker_eksik_tablo_retrying_yolu`'ndan —
buldu ve sildi) tamamen temizlendi, geniş bir son taramayla DB'nin
2099/209912 civarında hiç iz kalmadığı doğrulandı. **`audit_log`
satırları (append-only kural gereği) bilinçli olarak SİLİNMEDİ** — sızıntı
batch'lerine referans veren birkaç audit_log kaydı, `tarih_id=209912` ile
kendiliğinden test-ilişkili olduğu belli, zararsız, kalıcı iz olarak
bırakıldı. **Ders:** `test_job_worker_integration.py`'yi canlı DB'ye karşı
çalıştırmak GÜVENLİ DEĞİL (kendi commit'lerini yapıyor) — ileride tüm
paketi tekrar canlıya karşı çalıştırma kararı verilirse bu dosya hariç
tutulmalı ya da ayrı, atılabilir bir Supabase projesine karşı koşulmalı.

**Dokümantasyon:** `04_kpi_sozlesmeleri.md` (KPI-25 satırına KPI-26 ile
aynı formatta not + yeni KPI-27 satırı), `07_word_parser_kapsam.md`
("Yarından devam" listesinde KPI-25 maddesi YAPILDI), `00_INDEX.md`
(özet satırı) güncellendi.

## 2026-09-03 (devam) — Windows Akıllı Uygulama Denetimi (SAC) bulgusu

**Bu makineye özgü, kod/proje sorunu değil:** `epp` conda ortamının
`python.exe`'si ve ardından `numpy`/`pandas`'ın conda-forge derlemeleri
Windows Akıllı Uygulama Denetimi tarafından bloklandı (`worker/tests`
çalıştırılırken `test_fetch_weather.py`'de `ImportError` ve
`test_kpi_faz3.py`'de process'i çökerten bir `Windows fatal exception`
olarak ortaya çıktı).

**Çözüm bulundu:** `numpy`/`pandas`'ı conda-forge yerine
`pip install --force-reinstall --no-cache-dir numpy pandas` ile PyPI
wheel'inden kurmak SAC bloğunu aşıyor — aynı sürümler, farklı derleme,
sorun tamamen çözüldü (`worker/tests/test_kpi_faz3.py` +
`test_fetch_weather.py` ikisi de temiz geçti).

**UYARI — `epp` artık karma (conda + pip) bir ortam:** `conda update`/
`conda install` ileride `numpy`/`pandas`'ı sessizce conda-forge sürümüne
geri alıp bloğu tekrar getirebilir. Bu iki paketi her zaman
`pip install --force-reinstall numpy pandas` ile kur/güncelle, `conda
install`/`conda update` ile DEĞİL.

## 2026-09-04 — `20260819_0002_rls_roles.sql`'in GRANT/RLS kapsamı eksik
çıktı: dashboard `permission denied`/sessiz-boş-sonuç zincirinden geçti,
4 migration'la kapatıldı

**Tetikleyen belirti:** Streamlit dashboard'da (`app/dashboard.py`,
`DATABASE_URL` → `admin` rolüne `SET ROLE`) `donemler_getir()`
`permission denied for table dim_tarih` fırlattı. Kök neden ADR-7'de
("RLS notu, ek bulgu") daha önce not düşülen pooler/`SET ROLE` sorunuyla
KARIŞTIRILDI ama farklı çıktı — `SET ROLE admin` sorunsuz çalışıyordu,
sorun tamamen GRANT eksikliğiydi.

**Kök neden:** `20260819_0002_rls_roles.sql`'in `GRANT`/`ENABLE ROW LEVEL
SECURITY` kapsamı baştan eksikti — yalnız `dim_*` tabloları `viewer`'a
GRANT edilmiş, `data_operator`/`admin` hiç almamıştı; `sistem_parametre`,
`kpi_esik`, `job_status` ise migration'ın GRANT listesinde hiç yoktu
(sıfır rol, `authenticated` dahil hiçbiri). Ayrıca `dim_tarih`, `dim_il`,
`dim_kaynak`, `dim_tuketici_grubu`, `dim_lisans`, `sistem_parametre`,
`kpi_esik`, `job_status`'ta RLS migration DIŞINDA (muhtemelen Supabase
Dashboard'un "Enable RLS" uyarısından) sonradan AÇILMIŞ ama hiç policy
eklenmemişti — bu durumda Postgres, owner/BYPASSRLS dışındaki her role
hatasız ama SESSİZCE 0 satır döndürür (permission denied değil), bu da
`sistem_parametre_getir()`'in boş `{}` dönmesine yol açtı.

**Düzeltme, 4 ayrı migration (whack-a-mole değil, her turda "eksik ne
varsa hepsi" taraması yapılarak):**
1. `20260904_0001_dim_grants_fix.sql` — 5 `dim_*` tablosuna
   `data_operator`+`admin` için `GRANT SELECT`.
2. `20260904_0002_dim_rls_disable.sql` — aynı 5 `dim_*` tablosunda
   policy'siz açık kalmış RLS'i `DISABLE`.
3. `20260904_0003_missing_grants.sql` — 18 public tablonun tamamı
   tarandı, `sistem_parametre`/`kpi_esik`/`job_status` hiç grant almamış
   bulundu; `sistem_parametre`/`kpi_esik` SELECT, `job_status`
   `ingestion_batch` ile aynı desende INSERT/UPDATE (data_operator) +
   DELETE (admin, `worker/ingest.py`/`job_worker.py`'nin gerçek yazma
   deseni doğrulanarak).
4. `20260904_0004_sistem_kpi_job_rls_disable.sql` — 0003 doğrulanırken
   aynı "policy'siz RLS" deseni bu 3 tabloda da bulundu, RLS `DISABLE`.

**Canlıya uygulama notu:** 0001'i uygularken `dim_tarih` üzerinde
`AccessShareLock` tutan, ~8,5 dakikadır idle-in-transaction kalmış bir
oturum (`app_dashboard_service`, sorgusu `donemler_getir()` ile birebir
aynı — muhtemelen bu hatanın kendisine takılıp donmuş bir Streamlit Cloud
oturumu) migration'ı bloklamıştı; kullanıcı onayıyla
`pg_terminate_backend()` ile temizlendi (yalnız SELECT yapıyordu, veri
kaybı yok).

**Doğrulama (gerçek DB'ye karşı, hem `admin` hem `viewer`):**
`dim_tarih` 126, `dim_il` 81, `dim_kaynak` 13, `dim_tuketici_grubu` 5,
`dim_lisans` 2, `sistem_parametre` 4, `job_status` 8 satır (ikisinde de);
`kpi_esik` 0 satır — **bu bir hata değil**, `03_veri_modeli.md`'de
`job_status`'un aksine "Faz 1'de kullanımda" notu yok, yani KPI eşik/
trafik-ışığı config'i henüz UYGULAMA TARAFINDAN TÜKETİLMİYOR, tablo
bilinçli olarak boş; `donemler_getir()` 126 dönem, `sistem_parametre_getir()`
4 anahtarı (hdd_baz_c/cdd_baz_c/hava_norm_yil/tuketim_norm_yil) doğru
döndürüyor. Dashboard'da (Streamlit Cloud "Manage app → Reboot app" ile
`@st.cache_data`/`@st.cache_resource` temizlenerek doğrulandı — sekme
yenilemesi TEK BAŞINA yetmiyor, cache sunucu tarafında, TTL yok) 2026-06
dönemi hatasız yüklendi.

**Ders/gelecek için not:** `20260819_0002_rls_roles.sql` ilk yazıldığında
kapsamı public şemadaki TÜM tablolara göre değil, o anda akla gelen
tablo listesine göre çıkarılmış görünüyor. **İleride yeni bir tablo
eklenirse**, o migration'a GRANT+RLS eklemek "hatırlanması gereken bir
adım" değil, `information_schema.tables` (public şema) ile
`information_schema.role_table_grants`'i karşılaştıran bir kontrolün
(CI'da veya elle) rutine alınması daha güvenli olur — bu tur 4 ayrı
sürprizle (dim_*, sistem_parametre, kpi_esik, job_status) bunun elle
hatırlamaya bırakılamayacağını gösterdi.

Commit'ler: `a78b26d` (0001), migration sırası itibarıyla 0002-0004 aynı
oturumda ayrı commit'lerle push edildi (`047473f` dahil) — tam liste için
`git log --oneline` bu tarih aralığında.

## 2026-09-03 (karar kaydı, geriye taşındı) — Taksonomi kararı: "Ticarethane"/
"Tarımsal Sulama" RENAME olarak kabul edildi

**Bu giriş, silinen `SABAH_OZETI.md`'den bu operasyon günlüğüne taşındı**
(2026-09-04, Aşama 8 temizliği) — tam analiz hâlâ
`dokumanlar/08_word_2016_2022_kapsam.md`'de (Bulgu 5) duruyor, burada
yalnız kısa bir karar kaydı.

**Soru:** 2020 tam yıl + 2021 tam yıl + 2022 Ocak-Nisan, tüketici grubu
etiketlerinde kanonik kümede (`worker/parser.py:GRUP_ESLEME`) olmayan
"Ticarethane" ve "Tarımsal Sulama" kullanıyordu — bu bir yeniden
adlandırma (RENAME) mı, yoksa gerçek bir kapsam/taksonomi değişikliği mi?

**Kanıt 1 (mevsimsellik):** Taksonomi belirsizliği hiç olmayan 2023-2025
verisinde "Tarımsal" grubu Mart→Mayıs arasında zaten 2,79×-4,17×
sıçrıyor — 2021→2022'nin "Tarımsal Sulama"→"Tarımsal Faaliyetler"
arasındaki 2,82× artış bu aralığın İÇİNDE, kapsam değişikliği değil.
**Kanıt 2 (çapraz-doküman, ayrıca doğrulandı):** EPDK'nın kendi
"Dönemler Arası Karşılaştırma" tablosu, aynı takvim döneminin eski/yeni
etiketli değerlerini 12 örnek ayın 10'unda tam 1,0000 oranıyla eşleştirdi.

**Karar: RENAME.** Uygulama: `word_2020/2021/2022.py`'nin
`_GRUP_TAKMA_ADLAR`'ına "Ticarethane"→"Kamu ve Özel Hizmetler",
"Tarımsal Sulama"→"Tarımsal" eklendi. `worker/parser.py:GRUP_ESLEME`
DEĞİŞMEDİ (mimari karar — bkz. Karar 2/3 ile aynı ilke, yıla özel
tarifler kanonik şemayı bozmadan farklılıkları emer).
