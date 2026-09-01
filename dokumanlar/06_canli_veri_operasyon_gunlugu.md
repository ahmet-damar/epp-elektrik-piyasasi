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
