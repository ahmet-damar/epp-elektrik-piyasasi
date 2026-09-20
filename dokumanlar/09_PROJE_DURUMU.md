# 09 — Proje Durumu (GÜNCEL, DB'den doğrulandı — 2026-09-04, 2026-09-07'de
fact_tuketim_ulke_geneli eklemesiyle, 2026-09-08'de Aşama 1 kapanışıyla
güncellendi)

> **STATUS: LIVE (güncel durum)** — bu dosya ve `10_TEKNIK_MASTER_
> DOKUMAN.md`, değişen sayı/durumun YAŞADIĞI tek iki yerdir; diğer
> `dokumanlar/` dosyaları yalnız değişmeyen sözleşmeyi tutar (bkz.
> `10_TEKNIK_MASTER_DOKUMAN.md` → "Doküman Yönetim Kuralı" bölümü).

**Bu dosya, canlı Supabase'e karşı salt-okunur sorgularla ve `pytest`
çalıştırılarak bu turda TAZE DOĞRULANMIŞ bulgulara dayanır — önceki
(2026-09-03 tarihli) sürümün sayıları devralınmadı, hepsi yeniden
sorgulandı. Aradan geçen sürede tamamlanan iş kalemleri (regresyon
testleri, GRANT/RLS düzeltme zinciri, dashboard entegrasyonu) aşağıda
yansıtıldı.**

## TL;DR

- **T11 (fact_tuketim, tüketim):** 2016-01 → 2025-12 arası **120/120 ay
  aktif**, sıfır eksik.
- **T10 (fact_abone, abone sayısı):** yalnız **2021-11'den itibaren**
  aktif (2016-2020 tam yıllar + 2021 Ocak-Ekim, kaynakta il×grup kırılımı
  YAPISAL OLARAK yok). 2021-11 → 2025-12 arası **50/50 ay aktif**.
- **T4 (fact_uretim, lisanssız kurulu güç):** 120 aydan yalnız **2022-07
  eksik** (kalıcı kaynak hatası). **119/120 ay aktif.**
- **`veri_kapsam_disi` artık 2016-2025'in TAMAMINI kapsıyor** (önceki
  turda yalnız 2023-2025'ti) — `fact_serbest_tuketici` 120 kayıt (Karar 1,
  T13 hiçbir Word yılında yok), `fact_uretim` 121 kayıt (120×Lisanslı +
  1×2022-07 Lisanssız, Karar 3), `fact_abone` 70 kayıt (T10'un yapısal
  eksikliği).
- **Regresyon testleri — TAMAMLANDI (bugün kapandı).** `word_2016.py`'den
  `word_2025.py`'ye kadar **10 yılın 10'unda da** dedike pytest testi var
  (`worker/tests/test_word_2016.py` … `test_word_2025.py`) — önceki
  turda "2023-2025 eksik" denen açık madde bugün 36 yeni testle kapandı.
- **GRANT/RLS düzeltme zinciri — TAMAMLANDI.** `public` şemasındaki 18
  tablonun **hiçbiri artık grant'sız değil** (`viewer`/`data_operator`/
  `admin`), **hiçbir tabloda RLS-açık-ama-policy-yok deseni kalmadı**
  (4 migration: `20260904_0001`-`0004`) — panel artık admin/viewer
  girişiyle gerçekten çalışıyor (önceden `permission denied`/sessiz
  boş-sonuç veriyordu).
- **`veri_kapsam_disi` dashboard'a bağlandı** — seçili dönem için
  "kaynakta yok" işaretli veri varsa panel artık sessiz boşluk yerine
  açıklayıcı bir bilgi kutusu gösteriyor.
- **KPI-25/KPI-27 — TAMAMLANDI, kaynak kararı uygulandı (2026-09-08,
  Aşama 2/C5).** KPI-25 (resmi "toplam tüketim" CAGR) TAMAMEN
  `fact_tuketim_ulke_geneli`'ye taşındı (tam yıl + 5/5 grup şartı, il
  bazlı `fact_tuketim` ile ASLA karıştırılmıyor) — artık canlıda GERÇEK
  bir değer üretiyor: **+%3,1** (2017→2025, n=8; 2016 kasıtlı hariç —
  2016-12 Tarımsal kaynakta hiç yüklenmedi). Önceden sürekli
  'hesaplanamaz' dönüyordu, bu GERÇEK bir fonksiyonel iyileştirme. KPI-27
  (Sanayi-hariç, il bazlı `fact_tuketim`, DEĞİŞMEDİ) canlıda **+%3,8**
  (2016→2025, n=9). Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §7.5/§11.2.
- **pytest** (`worker/tests`, 6 `*_integration.py` hariç): temiz bir
  ortamda (`env -i`, DB env değişkeni yok) **227/227 geçti**, 0 hata —
  bkz. "Test durumu" bölümü ve `10_TEKNIK_MASTER_DOKUMAN.md` §9.4
  (v1.1'de 227 vs 230 karışıklığı çözüldü).
- **fact_tuketim_ulke_geneli — TAMAMLANDI (2026-09-07).** EPDK T11
  tablosunun kendi "Genel Toplam" satırından, il kırılımı olmayan,
  Sanayi DAHİL tüm grupların ülke geneli serisi. 2016-2025'in 120 ayının
  TAMAMI aktif (599 satır) — yalnız 2016-12 4/5 grupla (Tarımsal o ay
  kaynakta negatif çıktığı için hiç yüklenmedi, kullanıcı onayıyla kabul
  edildi). İlk backfill'de 39 ay mutabakat "uyumsuz" görünmüştü — kök
  neden bulundu (veri hatası DEĞİL, `dogrula_tuketim()`'in negatif değer
  reddi il vs ülke seviyesinde bağımsız uygulanmasının beklenen sonucu),
  `worker/scripts/mutabakat_ulke_geneli.py` ile kalıcı olarak düzeltildi.
  Detay: `06_canli_veri_operasyon_gunlugu.md` 2026-09-05/07 ve 2026-09-07
  kayıtları.
- **Sanayi'nin Word kaynağında neden T11'e girmediği sorusu — KAPANDI.**
  Cevap: T11'in kendi Genel Toplam satırı zaten Sanayi dahil tüm
  grupların ülke geneli değerini veriyor (yukarıdaki madde) — `07_word_
  parser_kapsam.md`'deki "ileride araştırılabilir" notu artık geçerli
  değil, kapatıldı.
- **Aşama 1 (operasyonel güvenlik, 2026-09-07) — TAMAMLANDI (C2/B2/C1/
  C3/C4).** Prod DB'ye karşı test guard'ı kod seviyesinde eklendi (C2),
  CI/deploy migration asimetrisi kapatıldı (B2, gerçek CI koşusuyla
  doğrulandı), yedekleme runbook'u GERÇEK bir restore drill'iyle
  doğrulandı (C1 — Supabase Free plan'de otomatik yedek YOK, bkz.
  `11_yedekleme_runbook.md`), scheduled-refresh sessiz başarısızlığa
  karşı iki katman savunma kazandı (C3), **8 tabloda RLS geri açıldı ve
  canlıya uygulandı** (C4 — `dim_*`×5 + `sistem_parametre`/`kpi_esik`/
  `job_status`; `02_srs_ozet.md`'nin "TÜM tablolarda RLS zorunlu" kuralı
  artık belgelenmemiş istisnasız gerçeğe uyuyor; istisnasız bir tamlık
  kontrolü — `worker/validate_role_access.py` — hem gerçek CI'da hem
  canlıda doğrulandı: 19/19 tablo RLS+policy). C4 uygulaması sırasında
  3+ saattir açık kalmış terk edilmiş bir Streamlit bağlantısı
  `pg_terminate_backend()` ile temizlendi (veri kaybı riski yoktu, salt-
  okunurdu) — detay `06_canli_veri_operasyon_gunlugu.md` 2026-09-07
  kaydı. Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §8.2/§8.5/§9.1/§9.3/§9.4,
  Sürüm Geçmişi v1.3-v1.7.
- **Kapsam dışı bırakılan (ayrı karar):** C5 (KPI-25/27'nin
  `fact_tuketim_ulke_geneli`'yi kullanıp kullanmayacağı) ve C6'daki diğer
  öneriler — Aşama 2'ye bırakıldı.
- **Aşama 1 kapanışı (2026-09-08) — C1'in eksik yarısı + C4'ün yan
  etkisi giderildi.** `.github/workflows/scheduled-backup.yml` eklendi
  (haftalık `pg_dump`, artifact `retention-days: 90`) — repo PUBLIC
  olduğu ve `audit_log`'da hassas veri OLMADIĞI doğrulanarak (bkz.
  `11_yedekleme_runbook.md`) şifrelemeden saklanmasına bilinçli karar
  verildi. `app_dashboard_service`'e `idle_in_transaction_session_
  timeout=30min` **canlıya uygulandı** (2026-09-07'deki 3+ saatlik kilit
  olayının TEKRARINA karşı) — gerçek bir kısa-timeout testiyle
  doğrulandı, normal kullanım etkilenmedi. (`app/dashboard.py`'nin bu
  hatayı otomatik yakalamadığı o turda bilinen bir sınırlama olarak not
  edilmişti — **2026-09-08'de Aşama 2'de KÖKÜNDEN düzeltildi, aşağıya
  bkz.**) **`scheduled-backup.yml` artık GERÇEK koşuyla UÇTAN UCA
  doğrulandı (2026-09-08, PAT'e `workflow` izni eklendikten sonra) — bu
  madde KAPANDI.** 2 gerçek CI hatası bulunup düzeltildi (pg_dump 16→17
  sürüm uyumsuzluğu, PATH sırası); üçüncü koşu başarılı oldu, artifact
  indirilip `pg_restore --list` ile içeriği incelendi, disposable
  postgres:17'ye (canlı Supabase'in kendi major sürümü) restore edilip
  **19/19 tablo canlı Supabase'in `COUNT(*)` değerleriyle birebir
  eşleşti**; 100 KB eşiği de ayrıca test edildi (gerçekten FAIL
  ettirildi, sonra geri alındı). Detay: `10_TEKNIK_MASTER_DOKUMAN.md`
  §8.2/§8.5/§9, Sürüm Geçmişi v1.8-v1.9.
- **Aşama 2 (2026-09-08) — TAMAMLANDI (C5).** KPI-25 TAMAMEN
  `fact_tuketim_ulke_geneli`'ye taşındı, KPI-27 il bazlı `fact_tuketim`'de
  kaldı (yukarıya bkz.) — karışık kaynak KPI'sı tasarımından bilinçli
  olarak kaçınıldı. `app/dashboard.py`'nin idle-in-transaction KÖK
  NEDENİ düzeltildi (`autocommit=True` + ölü bağlantıyı sessizce
  yeniden kuran `_baglanti_saglikli_mi()` mantığı) — canlıda GERÇEK
  testlerle kanıtlandı (2s timeout + 3s bekleme sonrası ikinci sorgu
  artık hata VERMİYOR; kasıtlı kapatılan bağlantı doğru tespit edilip
  saklanan JWT claim'iyle sessizce yeniden bağlandı). Yedekleme
  runbook'undaki restore hedefi `postgres:16`'dan canlı Supabase'in
  kendi sürümü `postgres:17`'ye düzeltildi, tatbikat yeniden koşuldu:
  19/19 tablo yine eşleşti, önceki turdaki tek zararsız uyarı (PG17
  `transaction_timeout` GUC'u) de ortadan kalktı. Detay:
  `10_TEKNIK_MASTER_DOKUMAN.md` §7.5/§8.2/§8.5/§11.2, Sürüm Geçmişi
  v1.10-v1.12.
- **Aşama 3 (boş KPI'ları açma) — ADIM 1-3'ün TAMAMI (kod + canlı)
  TAMAMLANDI (2026-09-08/09), Bulgu C/D kararları verilip uygulandı, ADIM
  5 (KPI bağlama, KPI-01..07'nin TAMAMI — KPI-04 dahil) TAMAMLANDI
  (2026-09-09), ADIM 4 (Word 2016-2025 üretim parser'ı) 2026-09-13'te
  BAŞLADI — 2025/2024/2023/2022/2021/2020/2019/2018'in "Excel'e en yakın
  8 yıl" fazı TAMAMLANDI (T2+T3 Lisanslı yüklendi, Lisanssız TÜM Word
  yılları için kapsam dışı — Bulgu D/L, iki açık karar 2024-02/2022-T6
  sayıyla ölçülüp kapatıldı, bkz. Bulgu I/J/K/L/M/N/O). ADIM 4'ün TAMAMI
  (10 yıl, 2025-2016, 120 ay) 2026-09-16'da BİTTİ — 2016 BESPOKE bir
  `t2_oku()` ile tamamlandı. **AYNI GÜN, Ahmet'in onayıyla CANLI BACKFILL
  UYGULANDI** — 120 ay canlıya yüklendi, mutabakat aktivasyondan ÖNCE
  çalıştırıldı, 119/120 ay aktive edildi (202402 established mekanizmayla
  kendiliğinden bloklandı, BEKLENEN). **Backfill SONRASI kritik bir bulgu
  çıktı ve AYNI oturumda düzeltildi:** KPI-07 (Lisanssız pay) Word
  yılları için sessizce yanlış '%0' döndürüyordu ('hesaplanamaz' YERİNE)
  — `kpi_07_lisanssiz_pay()`'e zorunlu bir `lisanssiz_kapsam_disi`
  parametresi eklenip düzeltildi, canlıda yeniden ölçülüp doğrulandı.
  **ADIM 4 TAMAMEN BİTTİ — kod, disposable-doğrulama VE canlı uygulama.**
  **Aynı gün (2026-09-16, devam) bir dashboard incelemesinde 3 madde
  daha bulunup düzeltildi:** (1) KPI-11/12 "Sanayi dikişi" — canlı
  KPI-12 (2026-06) sahte +%92,9 gösteriyordu, ölçülüp doğrulandı (Sanayi
  payı %40,2), `_il_tuketim_hava_getir()` her iki taraf da Sanayi-hariç
  yapılarak düzeltildi (1. seçenek il-bazlı regresyon mimarisiyle
  ÇAKIŞTI, 2. seçenek uygulandı), düzeltme sonrası +%15,4; (2)
  job_status id=11 (8 gündür asılı) araştırılıp GERÇEK bir iş OLMADIĞI
  (erken bir test kontaminasyonu artığı) bulundu, dead_letter'a alındı,
  YAPISAL olarak dashboard'a "worker çalıştırılmayı bekliyor" uyarısı
  eklendi; (3) KPI-26 açıklaması Karar 3'e referans verecek şekilde
  düzeltildi. Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.28, Sürüm Geçmişi
  v1.43, `06_canli_veri_operasyon_gunlugu.md` 2026-09-16 (devam) kaydı.
  **Aynı gün, ayrıca iki küçük iş kapandı:** KPI-11/12 kart başlıklarına
  "Sanayi Hariç" + Karar 2 referanslı kapsam notu eklendi (metin, hesap
  değişmedi); `kpi_esik`'in KPI-12 eşiği (yeşil≤5/sarı≤10) HİÇBİR
  ampirik gerekçesi olmadığı bulunup canlıya karşı ölçülen gerçek
  dağılımla (81 il×5 ay, n=403, medyan=%19,1, p90=%31,0) yeniden kalibre
  edildi (`yesil_alt=15,0`/`sari_alt=30,0`, migration `20260916_0001`,
  canlıya uygulandı). Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.29, Sürüm
  Geçmişi v1.44.
  **2026-09-17'de bir DOĞRULAMA TURU yapıldı** (`dokumanlar/kapsam_
  raporu_2026-09-16.md`'nin 5 maddesini ölçerek kesin sonuca bağlamak,
  commit `8b0da0f`) — 4 madde KANITLANDI (batch 732'nin mutabakat
  tarafından gerçekten/doğru bloklandığı, Adıyaman+Kahramanmaraş'ın
  2023-01/02'de EPDK'nın kendi mücbir-sebep dipnotuyla gerçekten eksik
  olduğu — deprem, 2022-07'nin zaten kayıtlı olduğu), 1 madde (kaynak_id
  sapması) monotonik-genişleme hipotezini çürüttü ama tam kapsamda
  belirsiz kaldı. YENİ kalıcı script: `worker/scripts/running_batch_
  kontrolu.py`. Detay orada, bu dosyada tekrarlanmıyor (D kuralı).
  **2026-09-18'de İş A (source_asset dedup) + İş C (mutabakat_reddedildi
  terminal durum) yapıldı** (`Claude outputs/PROMPT_A_C_2026-09-17.md`,
  kapanış raporu `Claude outputs/kapanis_2026-09-18_A_C.md` — BUNDAN
  SONRA kapanış raporları sohbete değil dosyaya yazılıyor, bkz. `.github/
  copilot-instructions.md`). İş A: canlıda 126 mükerrer `file_hash`
  grubu ÖLÇÜLDÜ, DURULDU (kullanıcı talimatı gereği — 125'i beklenen
  mimari, 1'i zaten temizlenmiş eski bir bug artığı), dedup migration'ı
  UYGULANMADI, 3 seçenek Ahmet'e sunuldu. İş C TAMAMLANDI: `ingestion_
  batch.status`'a 7. terminal durum (`mutabakat_reddedildi`) eklendi
  (migration `20260918_0001`, yalnız disposable'da), blok yolları
  (`aktive_et_uretim_word.py`/`backfill_uretim_excel.py`) artık status
  SET edip `audit_log_yaz()` çağırıyor, geri dönülebilirlik uçtan uca
  kanıtlandı. **CANLIYA HİÇBİR ŞEY UYGULANMADI** — bkz. "Açık madde"
  ve kapanış raporundaki sıralı uygulama planı.
  Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.30/§6.1/§14 madde 5, Sürüm
  Geçmişi v1.45.
  **2026-09-19'da Ahmet canlı-yazma izni verdi, İş C'nin ADIM 1'i
  (migration, 7. durum) CANLIYA UYGULANDI** (taze yedek + durum
  fotoğrafı doğrulanarak, sonrası 0 fark). **ADIM 2'de BEKLENMEDİK bir
  bulgu çıktı:** batch 732 dışında **5 GERÇEK, tamamlanmış batch (4-8,
  2026-02..06 Excel)** ~19 gündür elle onay bekliyor — kök nedeni
  FARKLI (`otomatik_onaya_uygun()`'un iç mutabakatı), talimat gereği
  ADIM 3 (batch 732) bu turda ÇALIŞTIRILMADI, batch 4-8'e dokunulmadı.
  **İş A kararı (Seçenek 3) kayda geçti, henüz uygulanmadı.** Detay:
  §5.31, Sürüm Geçmişi v1.46, `Claude outputs/kapanis_2026-09-19_
  canli_C.md`.
  **Aynı gün (devam), batch 4-8 ölçüldü — KAPANDI, aksiyon gerekmiyor**
  (2026-02..06 gerçekten iki kez yüklenmiş, aktif veri ikinci
  yüklemeden geliyor, batch 4-8 zararsız/ölü, kök nedeni 2026-08-31'de
  zaten belgeliydi — EPDK şablon değişikliği + bilinçli ertelenen T7
  formatı). **ADIM 3 (batch 732) de bu turda CANLIYA UYGULANDI:**
  `mutabakat_reddedildi`, audit_log +1, fact tablolarında 0 fark. **İş C
  TAMAMEN KAPANDI.** Detay: §5.32, Sürüm Geçmişi v1.47, `Claude
  outputs/kapanis_2026-09-19_batch_4_8.md`.
  (bkz. "Sonraki Oturum Devam Noktası" — tam liste orada).
  ADIM 1: Excel T11'in Genel Toplam satırı KÜMÜLATİF,
  6/6 ay (202601-202606) gerçek dosyaya karşı test edildi — de-kümülatif
  edilince T7 ile 4/6 ay birebir, 2/6 ay <%0,02 fark; **T7 değil T11
  seçildi** (2016-2025 Word ile TEK tanım). ADIM 2: `fact_tuketim_
  ulke_geneli` 2026-01..06'ya genişletildi (629 aktif satır — 599+30),
  gerçek bir de-kümülatif bug'ı bulunup düzeltildi (regresyon testiyle).
  **KPI-13 artık gerçek değer üretiyor:** 2026-06↔2025-06 için **+%7,1**
  (önceden hep 'hesaplanamaz'). ADIM 3 madde 1: ADIM 2'nin "en son
  batch'i al" düzeltmesi bile N-1'in SONRADAN değişmesine karşı sessiz
  kalıyordu — migration `20260908_0002` ile `kumulatif_tuketim_mwh`
  kolonu eklendi, yeni kalıcı script `tutarlilik_ulke_geneli_kumulatif.py`
  bu durumu AÇIKÇA yakalıyor (gerçek bir superseding senaryosuyla
  kanıtlandı). Canlıya uygulandı, mevcut 30 satır yeniden doğrulandı
  (`tuketim_mwh` değişmedi), mutabakat+tutarlılık canlıda YEŞİL. Detay:
  `10_TEKNIK_MASTER_DOKUMAN.md` §5.5-5.6, Sürüm Geçmişi v1.15-v1.16.
- **Yan olay (2026-09-08):** yukarıdaki doğrulama sırasında `worker/tests/
  conftest.py`'nin canlı-DB koruması 2026-09-02'deki İLE AYNI şekilde
  atlandı (`.env`'in kontrolden SONRA yüklenmesi) ve pytest paketi yine
  canlıya karşı çalışıp `tarih_id=209912` test kirliliği bıraktı — TESPİT
  EDİLDİ, TEMİZLENDİ (85 fact + 3 batch + 3 source_asset + 1 dim_tarih,
  audit_log korundu), koruma kalıcı düzeltilip canlıda reprodüksiyonla
  doğrulandı. Detay: `06_canli_veri_operasyon_gunlugu.md` 2026-09-08
  (devam) kaydı, Sürüm Geçmişi v1.17.

## Tablo — Yıl × Tablo Aktivasyon Durumu

| Yıl | T11 fact_tuketim | T10 fact_abone | T4 fact_uretim |
|---|---|---|---|
| 2016 | 12/12 aktif | 0/12 (kaynakta yok — tablo hiç basılmamış) | 12/12 aktif |
| 2017 | 12/12 aktif | 0/12 (kaynakta yok — il-only) | 12/12 aktif |
| 2018 | 12/12 aktif | 0/12 (kaynakta yok — il-only) | 12/12 aktif |
| 2019 | 12/12 aktif | 0/12 (kaynakta yok — il-only) | 12/12 aktif |
| 2020 | 12/12 aktif | 0/12 (kaynakta yok — il-only) | 12/12 aktif |
| 2021 | 12/12 aktif | 2/12 (yalnız Kas-Ara; Oca-Eki kaynakta yok) | 12/12 aktif |
| 2022 | 12/12 aktif | 12/12 aktif | 11/12 aktif (Temmuz kaynakta yok) |
| 2023 | 12/12 aktif | 12/12 aktif | 12/12 aktif |
| 2024 | 12/12 aktif | 12/12 aktif | 12/12 aktif |
| 2025 | 12/12 aktif | 12/12 aktif | 12/12 aktif |

Tüm "kaynakta yok" hücreleri `veri_kapsam_disi` tablosunda açık sebep
metniyle işaretli VE artık panelde (Aşama 7 entegrasyonu) kullanıcıya
görünür şekilde açıklanıyor.

## Regresyon testleri — tam liste (10/10 yıl)

| Dosya | Kapsam |
|---|---|
| `test_word_2016.py` … `test_word_2022.py` | Önceki oturumlarda yazıldı |
| `test_word_2023.py` (13 test) | Bugün eklendi — 4 "Kamu/Özel" varyantı, ADIYAMAN* dipnotu, HAKKÂRİ inceltme işareti |
| `test_word_2024.py` (11 test) | Bugün eklendi — tek şablon, Linyit dahil kaynak kolonları |
| `test_word_2025.py` (12 test) | Bugün eklendi — tek şablon, Nisan 2025 Aydınlatma deseni notu |

Hepsi `grup_esle_zorunlu`/`kaynak_esle_zorunlu`/`t11_oku`/`t10_oku`/
`t4_oku` düzeyinde, synthetic in-memory docx tablolarıyla, `DATABASE_URL`
bağımsız — CI'nin 'Worker' job'ında (canlı DB yok) da çalışır.

## GRANT/RLS düzeltme zinciri (2026-09-04, 4 migration)

`20260819_0002_rls_roles.sql`'in GRANT/RLS kapsamı baştan eksikti — canlı
kullanımda (Streamlit Cloud'da admin girişiyle) `permission denied for
table dim_tarih` ve ardından sessiz sıfır-satır sonuçları olarak ortaya
çıktı. 4 ayrı migration'la kapatıldı:
- `20260904_0001` — 5 `dim_*` tablosuna `data_operator`/`admin` için
  eksik `GRANT SELECT`.
- `20260904_0002` — aynı 5 tabloda policy'siz açık kalmış RLS `DISABLE`.
- `20260904_0003` — `sistem_parametre`/`kpi_esik`/`job_status` için
  (hiç grant almamışlardı) eksik GRANT'lar.
- `20260904_0004` — bu 3 tabloda da bulunan AYNI policy'siz-RLS deseni
  `DISABLE`.

Doğrulandı (bu turda yeniden sorgulandı): `public` şemasındaki 18
tablonun hiçbiri artık ne grant'sız ne RLS-açık-policy'siz. Detay:
`dokumanlar/06_canli_veri_operasyon_gunlugu.md`, 2026-09-04 girdisi.

## Test durumu (2026-09-07'de temiz bir kabukta yeniden doğrulandı)

```
env -i PATH=... HOME=/root python -m pytest worker/tests --collect-only -q
# 19 non-integration dosya TEK BAŞINA:
227 tests collected
```

**Not (bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §9.4/v1.1):** Bu oturumun daha
önceki bir WSL koşusunda görülen "230 passed" rakamı **yanlış değildi ama
genel bir sabit de değildi** — o koşuda `test_auth_integration.py`
(`DATABASE_URL_DASHBOARD` tanımlı olduğu için) yanlışlıkla dışlanmadan
gerçekten çalışmış ve 3/3 geçmişti (227 yerel + 3 gerçek Supabase Auth
çağrısı = 230). README Ek D kuralına göre **6** `*_integration.py`
dosyasının tamamı normal koşuda hariç tutulur; standart/ortam-bağımsız
rakam **227**'dir.

(2026-09-04'teki 205'ten artış: `test_word_ulke_geneli.py` (7),
`test_auth.py`'ye eklenen rate-limit testleri (6), ve aradaki diğer
turlarda eklenen testler — tam kırılım doğrulanmadı, yalnız toplam 227
`--collect-only` ile teyit edildi.)

## Sıradaki adımlar (teknik borç DEĞİL — ürün/kapsam kararları)

1. **2022 ve öncesi yıllara Word genişletmesi tamamlandı** — genişleme
   listesinde teknik olarak kalan bir yıl yok (2016-2025 hepsi aktif).
2. **Faz 4 (Tahminleme) / Faz 5 (EPİAŞ)** — daha önce ertelenmişti,
   artık 10 yıl gerçek veri var, karar gözden geçirilebilir.
3. **Sanayi'nin ülke geneli serisi — TAMAMEN TAMAMLANDI** (`fact_tuketim_
   ulke_geneli`, 120/120 ay aktif, yukarıya bkz.). KPI-25/27'nin bu
   tabloyu kullanıp kullanmayacağı kararı da **2026-09-08'de (Aşama
   2/C5) verildi ve uygulandı** — yukarıdaki TL;DR maddesine bkz., bu
   madde artık açık değil.
4. **Gerçek internete açık bir deploy** — Streamlit Cloud denemesi
   yapıldı (GRANT/RLS sorunları bu turda çözüldü), kalıcı/otomatik bir
   deploy akışı (`deploy.yml`'in şu an devre dışı `build-push` job'ı)
   hâlâ Docker/web iskeleti bekliyor.

## Güvenilirlik notu

Bu dosyadaki sayılar birden fazla turda canlı Supabase'e karşı
çalıştırılan salt-okunur SQL sorgularından (`fact_tuketim`/`fact_abone`/
`fact_uretim`/`veri_kapsam_disi`/`information_schema.role_table_grants`/
`pg_policies`) ve gerçek `pytest` çalıştırmalarından geliyor — hiçbir
sayı körlemesine önceki dokümandan devralınmadı, her turda yeniden
sorgulandı:

- **2026-09-04 turu:** GRANT/RLS düzeltme zinciri (4 migration) + 36 yeni
  regresyon testi (2016-2022 için) canlıda doğrulandı; bu turda hiçbir
  batch aktive edilmedi.
- **2026-09-05/07 turu:** `fact_tuketim_ulke_geneli` migration'ı canlıya
  uygulandı, 120 aylık backfill çalıştırıldı; ilk mutabakat kontrolünde
  81/120 ay aktive edilebildi, 39 ay `running` bırakılıp kullanıcıya
  rapor edildi (bkz. `06_canli_veri_operasyon_gunlugu.md` 2026-09-05/07
  kaydı) — bu, **geçici bir ara durumdu**, kalıcı sonuç değil.
- **2026-09-07 turu:** 39 aylık uyumsuzluğun kök nedeni bulundu (veri
  hatası değil — `dogrula_tuketim()`'in negatif değer reddinin il vs
  ülke seviyesinde bağımsız uygulanmasının beklenen sonucu), mutabakat
  sorgusu kalıcı olarak düzeltildi (`worker/scripts/mutabakat_ulke_
  geneli.py`), kalan 39 ay (2016-12 hariç 4/5 grupla) aktive edildi →
  **120/120 ay aktif, 599 satır**. RLS admin+viewer JWT ile yeniden
  doğrulandı. Ayrıca 13-dokümanlık dış denetim (Aşama 0) ve Aşama 1'in
  büyük kısmı (C2/B2/C1/C3/C4) bu günde tamamlandı.
- **2026-09-08 turu (son, GÜNCEL durum):** Aşama 1 kapatıldı — zamanlanmış
  yedek workflow'u + `app_dashboard_service` idle timeout canlıya
  uygulandı (yukarıya bkz.). Bu turda hiçbir fact/dim tablosu
  değişmedi, yalnız CI/CD + rol config'i.

---

## SONRAKİ OTURUM DEVAM NOKTASI

**Bu bölümü önce oku — bir sonraki oturum yalnız bunu okuyup kaldığı
yerden devam edebilmeli.**

**GÜNCEL (2026-09-20, gece) — en üst özet, aşağıdaki eski tarihli
özetlerin YERİNE geçer:**
- **Veri bütünlüğü arkı KAPANDI:** İş C (`mutabakat_reddedildi`)
  canlıda tam uygulandı; batch durum makinesi artık 9 değerde
  (`onay_bekliyor`/`onaylanmadi` dahil), batch 4-8 canlıda kapatıldı,
  `running_batch_kontrolu.py` TAMAMEN temiz (bkz. `10_TEKNIK_MASTER_
  DOKUMAN.md` §5.33, `Claude outputs/kapanis_2026-09-19_batch_durum.md`).
- **Toplama katmanı + Zaman Serisi UI TAMAMLANDI** (commit `7ac2cc9`,
  `a65b2b7`, `6e5b079` — `Claude outputs/kapanis_2026-09-19_toplama_
  katmani.md` + `kapanis_2026-09-20_ui_zaman_serisi.md`, §15/§5.34/§5.35):
  4 view + `worker/toplama.py` (8 fonksiyon) + dashboard'a "📈 Zaman
  Serisi" bölümü (mevcut sayfa BOZULMADI) — Altair ile çoklu-seri
  grafik, eksik-dönem işaretleme, dikiş etiketi.
- **JIT bulgusu:** v1.49'un "tek seferlik JIT" iddiası ÖLÇÜLÜP
  ÇÜRÜTÜLDÜ (amortisman YOK, her koşuda tekrarlanıyor) — karar: `worker/
  toplama.py`'nin TÜM sorgularına `SET LOCAL jit = off` eklendi (8×
  hızlanma, disposable'da ~830ms→~100ms).
- **"Hiç çalışmayan kontrol" denetimi + test idempotentliği KAPANDI**
  (§16, §16.3): sqlfluff pre-commit + `.pre-commit-config.yaml`'ın hiç
  çağrılmaması + `validate_rls_static.py`'nin donmuş dosya listesi
  bulundu (ATEŞLEYEMEZ, düzeltme ÖNERİLDİ, uygulanmadı — ayrı tur
  gerektiriyor); test paketinin KENDİSİ durum sızdırıyordu (`job_worker`
  testleri), teşhis edilip düzeltildi — paket artık İKİ ardışık koşuda
  (rebuild olmadan) BİREBİR aynı sonucu veriyor (idempotent). Kalıcı
  kurallar `.github/copilot-instructions.md`'ye eklendi.
- **Açık maddeler:**
  1. **İş A / Seçenek 3 dedup** — TANIMLI (Şart 1: batch 19'un
     error_summary'si audit_log'a taşınmadan silinmesin; Şart 2:
     storage_path NOT NULL tercih kuralı), ERTELENDİ, migration henüz
     yazılmadı. Ön koşulu: `parser_version` bump disiplininin yazılı
     kural hâline getirilmesi.
  2. **Harita turu** — Ahmet'ten karar bekleniyor: GeoJSON kaynağı
     (hangi il sınırı dosyası), TÜİK il nüfusu (kişi başı normalizasyon
     için mi), ve varsayılan ölçü (hangi KPI/metrik haritada gösterilecek).
     Bu kararlar gelmeden harita turu BAŞLAYAMAZ.
  3. **`validate_rls_static.py`'nin dinamik hale getirilmesi** ve
     **CI'ya paketi 2 kez çalıştıran bir idempotentlik kontrolü**
     eklenmesi — ikisi de ÖNERİLDİ, uygulanmadı, ayrı birer tur.

### Bugün/bu gece (2026-09-07/08/09) ne kapandı — tek satır özet
13-dokümanlık dış denetimin **tamamı** kapandı (2026-09-07/08, Aşama 0/1/2
+ D kuralı). 2026-09-08 içinde Aşama 3 ADIM 1-2 + ADIM 3 madde 1 kapandı
(commit `1232cb3`, `df616e6`). 2026-09-09 gecesi (gözetimsiz çalışma)
ADIM 3'ün TAMAMI (madde 0-4, kod+disposable) + ADIM 5'in araştırma
hazırlığı kapandı (commit'ler `a230614`→`cf5c9a1`, `7b76e3c`). **Aynı gün
(2026-09-09) kullanıcı onayıyla ADIM 3 madde 2-4 CANLIYA UYGULANDI**
(migration `20260909_0001` + `backfill_uretim_excel.py`, commit `2b3ecac`)
ve **Bulgu C/D kararları verilip uygulandı** (migration `20260909_0002` +
`veri_kapsam_disi` 48 satır + KPI-07 regresyon testi) — detay `10_TEKNIK_
MASTER_DOKUMAN.md` §5.11. **Sonra ADIM 5 (KPI-02/03/05/06/07 bağlama)
TAMAMLANDI** (commit `8afe19c`, §5.13) ve hemen ardından bir kontrol
turunda **KPI-04'ün de aynı kaynağa (yeniden) bağlanması gerektiği
bulunup düzeltildi** (bkz. "Açık madde" altındaki ADIM 5 kaydı ve §5.14) —
Aşama 3'ün "boş KPI'ları aç" hedefi artık KPI-01..07'nin TAMAMI için
gerçekleşmiş durumda (yalnız 2026-01'den itibaren; Word yılları ADIM 4'te).

### Açık madde

**GÜNCEL (2026-09-19, devam) — en öncelikli açık maddeler bunlar,
aşağıdaki ADIM 3/4 tarihçesi TAMAMEN kapalı, yalnız referans için
duruyor:**
1. ~~**batch 4-8 — Ahmet'in kararı gerekiyor**~~ — **TAMAMEN KAPANDI
   (2026-09-19, batch durum makinesi turu), hem VERİ hem DURUM düzeyinde.**
   Ölçüldü: 2026-02..06 GERÇEKTEN iki kez yüklenmiş, canlıdaki AKTİF veri
   İKİNCİ (düzeltilmiş parser'lı) yüklemeden geliyor, batch 4-8'in TÜM
   satırları TÜM tablolarda `is_active=false` — zararsız, ölü bir iz. Kök
   neden 2026-08-31'de ZATEN tam belgeliydi (EPDK şablon değişikliği, T7'nin
   bilinçli ertelenmiş formatı `otomatik_onaya_uygun()`'da yanlış-pozitif
   üretiyor, kullanıcı `onayla.py` ile bilerek elle onayladı — audit_log +
   ops log'da tam iz var). **Bu turda CANLIDA `ingestion_batch.status`
   `'onaylanmadi'`ya (YENİ 9. terminal durum) geçirildi** (5 batch, her
   birinde yerine geçen batch_id + gerekçe `error_summary`'de, 1
   `audit_log` satırı/batch) — `running_batch_kontrolu.py` artık batch 4-8'i
   de DAHİL hiçbir şey bulmuyor, TAMAMEN temiz. Fact satırlarına
   DOKUNULMADI (0 fark). Bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §5.32/§5.33,
   `Claude outputs/kapanis_2026-09-19_batch_4_8.md` +
   `Claude outputs/kapanis_2026-09-19_batch_durum.md`. Yalnız T7 çoklu-ay
   format düzeltmesi hâlâ ayrı, ertelenmiş bir teknik borç olarak kalıyor
   (düşük öncelik, mutabakat kontrolünü etkiliyor ama fact verisini
   etkilemiyor).
2. ~~**İş C ADIM 3 (batch 732) bekliyor**~~ — **KAPANDI (2026-09-19,
   devam).** Madde 1 netleştikten sonra dry-run → gerçek koşu yapıldı:
   `batch 732.status='mutabakat_reddedildi'`, `audit_log`'a +1 satır,
   fact tablolarında 0 fark (119+120 ayın tamamı doğrulandı).
   `running_batch_kontrolu.py` artık yalnız batch 4-8'i buluyor. **İş C
   TAMAMEN KAPANDI** (kod + migration + canlı uygulama).
3. **İş A — source_asset dedup, KARAR VERİLDİ (Seçenek 3), UYGULANMADI:**
   Ahmet Seçenek 3'ü (source_asset'i 1 dosya=1 satır yapma) seçti, iki
   şartla (Şart 1: batch 19'un error_summary'si audit_log'a taşınmadan
   silinmesin; Şart 2: "storage_path NOT NULL tercih, eşitlikte min(id)"
   kuralı, ham min(id) değil) — bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §5.31.
   Migration henüz YAZILMADI/uygulanmadı.
4. **Madde 4'ün tam kapsamı BELİRSİZ:** `fact_uretim_kaynak_geneli`
   kaynak_id sapmasının 15 aralığından yalnız 1'i doğrudan kaynak
   dosyasıyla doğrulandı — isteğe bağlı, aksiyon gerektirmiyor (bilgi
   amaçlı açık madde).
5. **YENİ (2026-09-19, batch durum makinesi turu — Görev 4) — yazılı
   `parser_version` bump disiplini YOK, İş A Seçenek 3'ün ÖN KOŞULU:**
   Ölçüldü: batch 4-8→10-15 geçişinde ikinci (aktif, düzeltilmiş) yükleme
   `parser_version`'ı **`'0.1'`'den `'0.3'`'e bump edilmiş** (KANITLANDI —
   canlı veriden doğrudan okundu). Ama repoda (`dokumanlar/`, `.github/
   copilot-instructions.md`) "parser davranışı değişince `parser_version`
   bump edilir" diye YAZILI bir kural YOK — yalnız geçmiş `parser_version`
   değerlerinin tanımlayıcı kaydı var, hiçbir yerde ZORUNLU bir disiplin
   olarak yazılmamış (bu turda bump'ın kendisi ŞANSA/insan alışkanlığına
   bağlıydı, kurala değil). **Öneri (UYGULANMADI, yalnız öneri):**
   `.github/copilot-instructions.md`'ye (kod yazma kuralları bölümüne) tek
   satırlık bir madde: "Bir parser fonksiyonunun çıktısını etkileyen HER
   davranış değişikliğinde `parser_version` ARTIRILIR — aynı `parser_
   version` iki farklı çıktı üretemez (P0-5'in `UNIQUE(source_asset_id,
   parser_version, schema_version)` varsayımı buna dayanıyor)." **Neden
   İş A Seçenek 3'ün ön koşulu:** Seçenek 3, "1 fiziksel dosya = 1
   `source_asset` satırı" mimarisine geçtiğinde, `parser_version` ARTIK
   TEK ayırt edici kolon olacak (bugünkü gibi `source_asset_id` DEĞİL) —
   bu kural yazılı olmadan dedup sonrası bir parser düzeltmesi SESSİZCE
   aynı `parser_version`'la tekrar yüklenirse, `BatchZatenTerminalHatasi`
   (İş A4, bkz. yukarı) devreye girip düzeltmeyi YANLIŞLIKLA reddedebilir.

---

Dış denetim listesinin (A/B/C bölümleri) hiçbir maddesi açık değil.
**Aşama 3 (boş KPI'ları açma) — ADIM 3'ün madde 1-4'ünün TAMAMI (kod +
canlı) TAMAMLANDI, ADIM 5 (KPI bağlama, KPI-04 dahil) DE TAMAMLANDI —
yalnız ADIM 4 (Word yılları) AÇIK:**
- **ADIM 3 madde 1** (batch bağımlılığı düzeltmesi) — TAMAMLANDI, canlıda
  (2026-09-08, commit `df616e6`).
- **ADIM 3 madde 2** (`fact_uretim_kaynak_geneli`/`fact_uretim_il_geneli`
  migration'ı) — TAMAMLANDI, **canlıya UYGULANDI** (2026-09-09).
- **ADIM 3 madde 3** (`mutabakat_uretim.py`, aktivasyonu engelleyen
  `periyot_aktivasyona_uygun_mu()`) — TAMAMLANDI (commit `9c3c236`,
  güvenlik düzeltmesi `dbe610e`), canlıda 12/12 uyumlu doğrulandı.
- **ADIM 3 madde 4** (Excel backfill) — TAMAMLANDI, **canlıya UYGULANDI**
  (2026-09-09): 6/6 ay yüklendi, mutabakat 6/6 UYGUN, 6/6 aktive edildi
  (`fact_uretim_kaynak_geneli` 101 satır, `fact_uretim_il_geneli` 942
  satır, hepsi aktif — canlı sonuç disposable ile birebir eşleşti).
- **Bulgu C/D kararları — VERİLDİ VE UYGULANDI (2026-09-09):**
  - **Bulgu C:** Word'ün Lisanssız için sunduğu zengin il×kaynak veri
    **KULLANILMAYACAK** (Word-Excel sınırında tanım kırılması riski) —
    yalnız doküman kararı, kod/veri değişikliği yok.
  - **Bulgu D (Karar 4):** 2016-2017 Lisanssız üretim **KAPSAM DIŞI** —
    migration `20260909_0002` (`veri_kapsam_disi.fact_tablosu` CHECK
    genişletildi) + `pipeline.kapsam_disi_isaretle()` ile 48 satır
    (canlıda 48/48 doğrulandı). KPI-07 için ileriye dönük şart `04_kpi_
    sozlesmeleri.md`'ye yazıldı + `kpi_07_lisanssiz_pay()`'in boş/tüm-NaN
    girdide `None` döndüğü yeni bir regresyon testiyle SABİTLENDİ.
  Detay: `05_kaynak_dosya_sozlesmesi.md`, `12_word_uretim_envanteri.md`.
- **Yan bulgu (canlıya özgü, kod DEĞİŞTİRİLMEDİ):** `validate_role_
  access.py`'nin `SET ROLE` adımı canlıda "permission denied" verdi —
  `postgres` rolünün `viewer`/`data_operator`/`admin`/`app_dashboard_
  service`'e üyeliği `WITH INHERIT FALSE, SET FALSE` (PG16+ özelliği,
  Supabase'in native rolleri — anon/authenticated/service_role — `SET
  TRUE` ile granted, fark BURADA) — bu turun migration'larıyla İLGİSİZ,
  ÖNCEDEN VAR OLAN bir canlı-ortam karakteristiği (disposable'da AYNI
  script sorunsuz geçti). `validate_rls_static.py` (21/21) canlıda
  YEŞİL — dinamik SET ROLE testi ayrı bir araştırma konusu, kod/veri
  değişikliği GEREKTİRMEZ, sonraki bir oturumda değerlendirilebilir.
- **ADIM 5 (asıl KPI bağlama, KPI-02/03/06/07/05) — TAMAMLANDI (2026-09-09,
  ADIM 4'ten ÖNCE yapıldı, yalnız 2026 Excel verisiyle):**
  - `worker/analytics.py:uretim_kaynak_geneli_getir()` → KPI-02 (yalnız
    Lisanslı, formül gereği)/03/06/07 (kombine).
  - `worker/analytics.py:kapasite_faktoru_girdisi_getir()` → KPI-05, pay
    VE payda AYNI lisans (Lisanslı) filtresiyle — sessiz-hata riski
    testle sabitlendi (filtresiz/doğru yol GERÇEKTEN farklı çıktığı
    kanıtlandı, sonra doğru yol pinlendi).
  - Canlı 2026-01..06: KPI-02 23,9-31,3 TWh, KPI-03 %39,7-72,0, KPI-05
    %32,0-42,3 (makul aralık), HHI 0,175-0,246, KPI-07 %3,5-12,4.
  - `dashboard.py` kartlarına kaynak/kapsam notu eklendi. KPI-01
    BİLİNÇLİ dokunulmadı (`fact_uretim`, kurulu güç, STOK).
  - Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.13, Sürüm Geçmişi v1.27;
    `06_canli_veri_operasyon_gunlugu.md` 2026-09-09 (devam) kaydı.
- **KPI-04 kontrolü — DÜZELTİLDİ (2026-09-09, ADIM 5'in hemen ardından,
  kullanıcının "bu kapsam dışı denmesi doğru görünmüyor" itirazı üzerine):**
  ADIM 5'in ilk turunda KPI-04 raporda "hâlâ veri yok, kapsam dışı"
  olarak bırakılmıştı — bu YANLIŞ bir karakterizasyondu, gerçek bir kapsam
  kararı değil, o turun talimat kapsamının (yalnız KPI-02/03/06/07) dışında
  kaldığı için atlanmıştı. Formülü (`Σ uretim(kaynak)/Σ uretim`) KPI-03/06
  ile YAPISAL OLARAK AYNI — kaynak DEĞİŞTİRİLİP `uretim_kaynak_geneli`'ye
  bağlandı (`app/dashboard.py`, `kpi.kpi_04_kaynak_payi(uretim_kaynak_
  geneli)`). Canlı 2026-01..06 kaynak payları toplamı 6/6 ayda ~%100
  (99,9-100,2 — 1 ondalık yuvarlamadan kaynaklanan beklenen sapma)
  doğrulandı. Yeni regresyon assertion'ı `test_uretim_kaynak_geneli_
  getir_sekil_ve_lisans_gorunumu`'a eklendi (payların toplamı %100'e
  yakın olmalı). Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.14.
- **🟢 ADIM 4 devam ediyor (2026-09-13) — 2025 (T2+T3 Lisanslı + T5/T6
  Lisanssız kararı) TAMAMLANDI:**
  - Bulgu E bu turda 2025'in TAMAMI (12/12 ay) için KESİN doğrulandı:
    T6 (Lisanssız, il bazında marjinal) tablosu **HİÇ YOK**.
  - T2 (Lisanslı kaynak) + T3 (Lisanslı il) `word_2025.py`'ye eklendi,
    disposable postgres:17'ye 12/12 ay yüklendi, `mutabakat_uretim.py`
    T2↔T3 çapraz kontrolü **12/12 uyumlu**. 2 gerçek format sürprizi
    bulunup regresyona dönüştürüldü (T2'nin dönem satırı sırası/büyük-
    harfi T10'dan farklı; T3'te 2025-01 Kilis satır olarak hiç
    görünmüyor). +19 test (`test_word_2025.py`), 122/122 mevcut Word
    yılı regresyonu hâlâ yeşil. Detay: `10_TEKNIK_MASTER_DOKUMAN.md`
    §5.15, `06_canli_veri_operasyon_gunlugu.md` 2026-09-13 (devam) kaydı.
  - **✅ T5/T6 KARARI VERİLDİ VE UYGULANDI (Bulgu H — 10 yılın TAMAMI
    tarandı, 120 ay, tek yıla bakılmadan):** desen KARIŞIK (2016-2022
    çoğunlukla var — 2022 Haziran'dan itibaren "İhtiyaç Fazlası Satın
    Alınan" diye yeniden adlandırılıp tanım riski taşıyor —, 2023 yıl-içi
    bölünmüş: Ocak-Haziran var/Temmuz-Aralık yok, 2024-2025 tamamen yok).
    Önceden verilen kural gereği: 2025 için Lisanssız (T5+T6) HER İKİ
    tabloda da (`fact_uretim_kaynak_geneli` + `fact_uretim_il_geneli`)
    `pipeline.kapsam_disi_isaretle()` ile kapsam dışı işaretlendi
    (`nitelik='lisans_durumu=Lisanssız'`, Karar 4'ün genişlemesi) —
    mutabakat kontrolüne İSTİSNA EKLENMEDİ, T5 SİMETRİ için yüklenmedi.
    Disposable postgres:17: 24 satır (2×12 ay) eklendi, mutabakat hâlâ
    12/12 uyumlu. KPI-07 için Word-genelinde dışlama GEREKMEDİ (desen
    "hiçbir yılda yok" değil, `kpi_07_lisanssiz_pay()` yalnız kaynak
    tablosuna bağımlı). **GÜNCELLEME (Bulgu L, aynı gün):** 2018-2022'nin
    T6'sı AYRICA ölçüldü — "rename öncesi normal görünen başlık" tek
    başına kanıt DEĞİLMİŞ, T6 var olduğu HER yıl "Brüt" değil "İhtiyaç
    Fazlası" ölçüyor, TÜM Word yılları için kapsam dışı (bkz. aşağıdaki
    Bulgu L maddesi). Detay: `dokumanlar/12_word_uretim_envanteri.md`
    Bulgu H/L, `10_TEKNIK_MASTER_DOKUMAN.md` §5.16/§5.19, Sürüm Geçmişi
    v1.30/v1.33.
  - **✅ 2024 TAMAMLANDI (2026-09-13):** T2+T3 (Lisanslı) yüklendi,
    Lisanssız (Bulgu H'nin 2024 satırı zaten "YOK") kapsam dışı
    işaretlendi. 2 gerçek bulgu: **Bulgu I** (3 satırlık bölünmüş T2
    başlığı, Mayıs/Kasım/Aralık — parser hatası, düzeltildi + 2 regresyon
    testi). **Bulgu J** (2024-02'nin T3'ü GERÇEKTEN hatalı — EPDK'nın
    kendi belgesinde Ocak'ın stale kopyası, dosya hash'leri farklı yani
    kod/manifest hatası DEĞİL — `mutabakat_uretim.py` %11,45 farkla
    doğru şekilde yakaladı, ZORLA GEÇİRİLMEDİ, 202402 Lisanslı
    aktive edilmeden bırakıldı). Disposable: 12/12 ay yüklendi, mutabakat
    **11/12 uyumlu**. +5 test, 249/249 unit test yeşil. Detay: `12_word_
    uretim_envanteri.md` Bulgu I/J, `10_TEKNIK_MASTER_DOKUMAN.md` §5.17,
    Sürüm Geçmişi v1.31.
    - **⚠️ Canlı backfill öncesi açık madde:** 202402'nin T3 verisi için
      karar gerekecek (olduğu gibi mi kabul, yoksa EPDK'nın olası bir
      düzeltmesini mi bekle) — bu turda karar VERİLMEDİ, yalnız
      belgelendi.
  - **✅ 2023 TAMAMLANDI (2026-09-13):** T2+T3 (Lisanslı) yüklendi,
    Lisanssız'ın TAMAMI (12/12 ay, T6 yıl-içi bölünmüş olduğu için güvenli
    taraf seçildi) kapsam dışı işaretlendi. **Bulgu K:** yeni kaynak türü
    'LPG' bulundu (12 ayda hep 0,00 MWh — atla sayıldı, `t2_oku()`'nun
    Genel Toplam kontrolü güvence). 'Motorin'in gerçek üretimi (Kasım
    473,77 / Aralık 1.833,41 MWh) için YENİ bir değişiklik GEREKMEDİ —
    `worker/parser.py`/`dim_kaynak` ikisi de 2026-08-19'dan beri hazırdı
    (ilk yazılan migration taslağı redundant çıkıp silindi). Disposable:
    12/12 ay yüklendi, mutabakat **12/12 uyumlu** (2024'ün Bulgu J'si gibi
    bir sorun YOK). +4 test, 255/255 unit test yeşil. Detay: `12_word_
    uretim_envanteri.md` Bulgu K, `10_TEKNIK_MASTER_DOKUMAN.md` §5.18,
    Sürüm Geçmişi v1.32.
  - **✅ Her iki açık karar SAYIYLA ölçülüp KAPATILDI (2026-09-13):**
    - **2024-02 (Bulgu J):** ÖLÇÜLDÜ — T2 (kaynak) Ocak/Şubat'ta 11/11
      kaynakta TAMAMEN FARKLI (sağlam), T3 (il) 81/81 ilde BİREBİR AYNI
      (stale). Uygulandı: Şubat için yalnız T2 yükleniyor, T3 o ay için
      AYRICA kapsam dışı işaretlendi — mutabakata istisna YOK, beklenen
      sonuç doğrulandı (`'bir_taraf_eksik'`, önceki %11,45 sayısal
      uyumsuzluktan farklı, bilinçli kararın doğal sonucu).
    - **2022 T6 tanım sınırı (Bulgu L):** ÖLÇÜLDÜ (2022 Mart-Ağustos +
      2020 Ocak/Haziran kontrolü) — rename sınırında SIÇRAMA YOK ama T6
      VAR OLDUĞU HER AY (2020 dahil, rename'den 2 yıl önce) "Brüt"
      DEĞİL "İhtiyaç Fazlası" ölçüyor. **Bulgu H'nin "2022 Haziran'dan
      itibaren tanım riski" ifadesi YETERSİZ kaldı, düzeltildi: T6 var
      olduğu HER yıl (2016-2023 Haziran) KAPSAM DIŞI**, istisnasız.
      `05_kaynak_dosya_sozlesmesi.md`'ye yazıldı. Lisanssız stratejisi
      artık TÜM Word yılları için NET, yıl yıl yeniden değerlendirme
      gerekmiyor.
  - **✅ 2022 TAMAMLANDI (2026-09-13):** T2+T3 (Lisanslı) yüklendi,
    Lisanssız (Bulgu L kararıyla) TÜM yıl kapsam dışı. 12 ayın TAMAMI
    temiz (2024'ün Bulgu I/J'sine benzer bir sürpriz YOK). Disposable:
    12/12 ay yüklendi, mutabakat **12/12 uyumlu**. +6 test (2 Bulgu J
    pinlemesi + 4 `test_word_2022.py`), 260/260 unit test yeşil. Detay:
    `10_TEKNIK_MASTER_DOKUMAN.md` §5.19, Sürüm Geçmişi v1.33.
  - **✅ 2021 TAMAMLANDI (2026-09-13):** T2+T3 (Lisanslı) yüklendi,
    Lisanssız (Bulgu L kararıyla) TÜM yıl kapsam dışı. Tek format
    sürprizi: **Bulgu M** — Nisan 2021'in T2'si `"RÜZGÂR"` (inceltmeli,
    tüm-büyük) yazıyor, diğer 11 ay â'sız `"RÜZGAR"` — `word_2021.py`'nin
    `_KAYNAK_TAKMA_ADLAR`'ına eklendi. Disposable: 12/12 ay yüklendi,
    mutabakat **12/12 uyumlu**. +6 test (`test_word_2021.py`), 266/266
    Word-parser unit test yeşil. Ayrıca bu turda bir ORTAM bulgusu
    (kod DEĞİL) bulunup kalıcı çözüldü: sahte/dinleyicisiz bir
    `DATABASE_URL` ile tam `pytest worker/tests` koşusu asılı kalıyordu
    (psycopg'in reddedilen bağlantıya karşı anormal beklemesi — WSL
    köprüsü ayrıca ölçülüp SAĞLIKLI bulundu); `pytest-timeout` güvenlik
    ağı olarak eklendi. Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.20,
    Sürüm Geçmişi v1.34, `06_canli_veri_operasyon_gunlugu.md` 2026-09-13
    (devam).
  - **✅ 2020 TAMAMLANDI (2026-09-13):** T2+T3 (Lisanslı) yüklendi,
    Lisanssız (Bulgu L kararıyla) TÜM yıl kapsam dışı (2020 zaten Bulgu
    L'nin ölçüm aralığındaydı, yeniden ölçüm gerekmedi). 12 ayın TAMAMI
    kod yazmadan ÖNCE dry-run ile tarandı — Bulgu I/M sınıfı bir
    sürpriz YOK, tüm-büyük kaynak etiketleri (DOĞAL GAZ/İTHAL KÖMÜR/
    HİDROLİK/RÜZGAR/GÜNEŞ/JEOTERMAL/BİYOKÜTLE/LİNYİT/ASFALTİT/TAŞ
    KÖMÜRÜ/MOTORİN) hiçbiri yeni takma ad gerektirmedi. Disposable:
    12/12 ay yüklendi, mutabakat **12/12 uyumlu**. +4 test
    (`test_word_2020.py`). Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.21,
    Sürüm Geçmişi v1.35.
  - **✅ 2024-02 kararı yeniden CANLI doğrulandı (2026-09-13):** kod
    hâlâ mevcut (`_STALE_IL_AYLAR`, commit `a103a03`), fresh disposable'a
    2024'ün 12 ayı yeniden yüklenip `mutabakat_kontrol_et()` çıktısı
    doğrudan sorgulandı — `{'tarih_id': 202402, 'durum':
    'bir_taraf_eksik', 'il_toplami': None, 'kaynak_toplami':
    25615763.19}`, beklenenle BİREBİR aynı. Bekleyen bir uygulama adımı
    YOKTU.
  - **✅ 2019 TAMAMLANDI (2026-09-13):** T2+T3 (Lisanslı) yüklendi,
    Lisanssız (Bulgu L kararıyla) TÜM yıl kapsam dışı. **Bulgu N:**
    Ocak-Kasım'ın T2'si Hidrolik'i `"AKARSU"`+`"BARAJLI HİDROLİK"` diye
    İKİ AYRI satıra bölüyor (Aralık tek satır) — kod yazmadan ÖNCE tam
    T2 dökümüyle tespit edildi, `t2_oku()` artık T4'ün established
    "TOPLA" ilkesiyle aynı kaynağa eşlenen satırları biriktirip TEK
    satır üretiyor (aksi halde `UNIQUE(tarih_id, kaynak_id, lisans_id,
    batch_id)` kısıtı ihlal edilirdi). Disposable: 12/12 ay yüklendi
    (UNIQUE ihlali YOK), mutabakat 2024 ile birlikte 24 çift kontrol
    etti, **23/24 uyumlu** (tek uyumsuz beklenen 202402). +3 test
    (`test_word_2019.py`). Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.22,
    Sürüm Geçmişi v1.36.
  - **✅ 2018 TAMAMLANDI (2026-09-13):** T2+T3 (Lisanslı) yüklendi,
    Lisanssız (Bulgu L kararıyla) TÜM yıl kapsam dışı. Kod yazmadan
    ÖNCE tam T2/T3 dökümüyle tarandı — iki desen bulundu, İKİSİ DE
    bilinen sınıflardan: Bulgu I sınıfı (Temmuz-Aralık'ın T2'si
    3-satırlık bölünmüş başlık, established while-loop çözdü) ve
    Bulgu N (12 ayın TAMAMINDA — Aralık dahil — Hidrolik "AKARSU"+
    "BARAJLI HİDROLİK" ikiye bölünmüş, aynı toplama çözümü). T3'ün il
    sayısı ay ay değişti (78/79/80, established Bulgu G, kod
    değişikliği gerekmedi). Disposable (fresh, tek başına — üç yılın
    art arda yüklenmesi established sequence-drift kontaminasyonuna
    yol açtığı için rebuild edildi): 12/12 ay yüklendi, mutabakat
    **12/12 uyumlu**. +4 test (`test_word_2018.py`). Detay:
    `10_TEKNIK_MASTER_DOKUMAN.md` §5.23, Sürüm Geçmişi v1.37.
  - **🏁 ADIM 4'ün "Excel'e en yakın 8 yıl" fazı TAMAMLANDI (2025+2024+
    2023+2022+2021+2020+2019+2018) — hepsi YALNIZ disposable
    postgres:17'de, canlıya HİÇBİRİ UYGULANMADI.**
  - **✅ 2016-2017 GENİŞLETİLMİŞ dry-run taraması BİTTİ (2026-09-13,
    KOD YAZILMADI — Bulgu O):** 24 ayın TAMAMI için T2/T3 varlığı,
    başlık metni, satır/kolon yapısı, il sayısı, kaynak etiketleri
    dökümlendi.
    - Görünüşte "tablo yok" olan 4 ay (2016 Oca/Şub, 2017 Kas/Ara)
      araştırıldı — İKİSİ DE gerçek yokluk DEĞİL: 2016 Oca/Şub
      başlıkta "Lisanslı" kelimesi eksik; 2017 Kas/Ara'da EPDK ayrıca
      bir YTD/kümülatif tablo ekleyip arama metnini belirsizleştiriyor.
    - **En önemli bulgu:** 2016'nın T2'si TÜM 12 ay TEK-DÖNEM 3-kolonlu
      format — 2017-2025'in 6-kolonlu dönemler-arası formatından
      TAMAMEN FARKLI, `hedef_donem_kolonu_bul()` KULLANILAMAZ, bespoke
      bir `t2_oku()` gerekecek.
    - Bulgu N (Hidrolik ikiye bölünmüş) her iki yılda da var (2017
      "BARAJLI HİDROLİK" yeni alias gerekir; 2016 yalnız "BARAJLI"
      zaten tanınıyor ama YİNE DE toplama gerekiyor).
    - Bulgu I sınıfı yalnız 2017 Ekim'de, yeni/tanınmayan kaynak türü
      YOK, T3 il sayısı established Bulgu G deseniyle tutarlı,
      Lisanssız (T5/T6) zaten Bulgu D ile kapsam dışı.
    - Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.24, Sürüm Geçmişi v1.38,
      `12_word_uretim_envanteri.md` Bulgu O (özet tablosu dahil).
  - **✅ 2017 TAMAMLANDI (2026-09-16):** Ahmet'in önceki onayıyla
    (2026-09-13) 2016-2017'ye başlandı, önce 2017 (az sürprizli).
    T2+T3 (Lisanslı) yüklendi, Bulgu O'nun ÖNGÖRDÜĞÜ desenler BİREBİR
    doğrulandı — YENİ sürpriz YOK: Bulgu N (12 ayın TAMAMINDA Hidrolik
    "AKARSU"+"BARAJLI HİDROLİK" ikiye bölünmüş, alias+toplama ile
    çözüldü), Bulgu I sınıfı (yalnız Ekim'de bölünmüş başlık,
    established while-loop çözdü), Kasım/Aralık arama ambiguity'si
    (EPDK'nın YTD kümülatif tablosu, `icermez=["Ocak-"]` ile çözüldü —
    Ocak'ın kendi ayı yanlışlıkla dışlanmadığı doğrulandı). Lisanssız
    (T5/T6) Bulgu L kararıyla TÜM yıl kapsam dışı. Disposable: 12/12 ay
    yüklendi, mutabakat **12/12 uyumlu**. +5 test (`test_word_2017.py`).
    Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.25, Sürüm Geçmişi v1.40.
  - **✅ 2016 TAMAMLANDI (2026-09-16) — ADIM 4'ün 10 yılı da BİTTİ:**
    Bulgu O'nun en önemli öngörüsü (T2'nin tek-dönem 3-kolonlu formatı,
    diğer yılların `hedef_donem_kolonu_bul()` mantığı işlemiyor) BİREBİR
    doğrulandı — BESPOKE bir `t2_oku()` yazıldı (`hedef_ay_yil`
    parametresi YOK). Bulgu N burada da geçerli ("Barajlı", â'sız kısa
    biçim — YENİ alias gerekmedi, toplama gerekti). YENİ küçük bulgu:
    "Üretim" kolon başlığı ay ay case-değişiyor, `normalize_label()` ile
    çözüldü. Önceki Word genişlemesinden bilinen İstanbul-bölünmüş-
    satır/Adana-kayıp sınıfı sürprizler T2/T3'te (üretim) AYRICA kontrol
    edildi — GÖRÜLMEDİ (yalnız T11'e/tüketime özgüydü). Disposable:
    12/12 ay yüklendi, mutabakat **12/12 uyumlu**. +7 test
    (`test_word_2016.py`). Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.26,
    Sürüm Geçmişi v1.41.
  - **🏁 ADIM 4 KAPANIŞI — 10 yılın TAMAMI (120 ay) tek disposable'da
    tek turda doğrulandı (2026-09-16):** fresh rebuild, 2016→2025
    sırasıyla yeniden yüklendi. `mutabakat_uretim.py`: **120 çift
    kontrol etti, 119 uyumlu, 1 BEKLENEN istisna (202402, `bir_taraf_
    eksik`, Bulgu J)**. `fact_uretim_kaynak_geneli`: 1.393 satır
    (120/120 ay). `fact_uretim_il_geneli`: 9.639 satır (119/120 ay).
    TÜM 120 batch `status='running'`, TÜM fact satırları
    `is_active=false` (gece-boyu kural — aktivasyon HİÇ çağrılmadı).
    Bulgu tamlığı doğrulandı: A'dan O'ya 15 bulgu, hepsi kararla
    kapatıldı ya da established desenle çözüldü, AÇIK bulgu YOK. Tam
    yıl-yıl özet tablosu `12_word_uretim_envanteri.md`'nin "ADIM 4
    KAPANIŞI" bölümünde.
  - **✅ CANLI BACKFILL UYGULANDI (2026-09-16, Ahmet'in onayıyla) — ADIM
    4 TAMAMEN BİTTİ:** 120 ay canlıya yüklendi, mutabakat aktivasyondan
    ÖNCE çalıştırıldı (132 çift — 120 Word + 12 önceden aktif Excel-era
    —, 131 uyumlu + 1 beklenen istisna), 119/120 ay aktive edildi
    (202402 established mekanizmayla kendiliğinden bloklandı, istisna
    EKLENMEDİ). Canlı satır sayıları disposable'la BİREBİR eşleşti.
    **Backfill SONRASI kritik bulgu, AYNI oturumda düzeltildi:** KPI-07
    Word yılları için sessizce yanlış '%0' döndürüyordu — `kpi_07_
    lisanssiz_pay()`'e zorunlu `lisanssiz_kapsam_disi` parametresi
    eklenip düzeltildi, canlıda yeniden ölçülüp doğrulandı. KPI-03/06
    kontrol edildi, düzeltme gerekmedi (Lisanslı-only kapsamı captioned).
    Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.27, Sürüm Geçmişi v1.42,
    `06_canli_veri_operasyon_gunlugu.md` 2026-09-16 (devam) kaydı (tam
    komut çıktıları/sayılar dahil).
  - Sonrası Faz 4 (Tahminleme) — aşağıda "Faz 4 (Tahminleme)" bölümüne
    bkz.

### ✅ Kapandı — Test izolasyonu: paket idempotent hâle getirildi (2026-09-20, gece)

`Claude outputs/PROMPT_TEST_IZOLASYON_2026-09-20.md`, kapanış raporu
`Claude outputs/kapanis_2026-09-20_test_izolasyon.md`. Tam detay
`10_TEKNIK_MASTER_DOKUMAN.md` §16.3.

Önceki turun teşhisi sırasında disposable kirlendi, art arda iki
tam-paket koşusu FARKLI testlerde patladı — **projenin dördüncü
"yazılmış ama ateşleyemez kontrol" vakası**: kalite kapısı "fresh
disposable'da yeşil" diyordu ama yeşillik koşullara bağlıydı, doğruluğa
değil. Ölçüldü: ikinci koşuda TAM OLARAK 3 test bozuluyordu
(`test_is_kuyruk_atomik_sahiplenme`, `test_is_sahiplen_bayat_heartbeat_
geri_alir`, `test_job_worker_temiz_batch_otomatik_aktive_eder`). Kök
neden KANITLANDI: `test_job_worker_eksik_tablo_retrying_yolu` bir job'ı
kasıtlı `'retrying'` bırakıyor (gerçek commit gerektiriyor, rollback
edilemiyor), bu kalıcı satır ikinci koşuda `job_status` SIRASINI
kaydırıyordu (Postgres sequence'ları transaction-dışı). Düzeltme:
`test_job_worker_integration.py`'nin `conn` fixture'ına, o dosyanın
sentinel periyoduna bağlı HER ŞEYİ temizleyen bir teardown eklendi.
**Kanıt:** düzeltme sonrası iki ardışık koşu (aynı DB, rebuild yok)
BİREBİR aynı sonucu verdi (`426 passed, 3 deselected` — iki kez).

Ayrıca `test_onay_bekleyen_batch_uyarisi_gorunur`'un (önceki turdan
kalan açık madde) GERÇEK kök nedeni bulundu — DB kirliliğiyle İLGİSİZ:
`app/dashboard.py:donemler_getir()` boş dönerse script `st.stop()` ile
hemen duruyordu, testin fixture'ı hiç `fact_tuketim` satırı eklemiyordu.
Düzeltildi, artık fresh disposable'da güvenilir şekilde geçiyor.

**Kalıcı kural eklendi** (`.github/copilot-instructions.md` + §16.3):
test paketi idempotent olmalı. CI'ya paketi 2 kez çalıştıran bir
doğrulama adımı ÖNERİLDİ (maliyet/değer tartışıldı), UYGULANMADI.

**CANLIYA HİÇBİR ŞEY UYGULANMADI.**

### ✅ Kapandı — "Hiç çalışmayan kontrol" taraması (2026-09-20, akşam)

`Claude outputs/PROMPT_KONTROL_DENETIMI_2026-09-20.md`, kapanış raporu
`Claude outputs/kapanis_2026-09-20_kontrol_denetimi.md`. Tam detay
`10_TEKNIK_MASTER_DOKUMAN.md` §16.

Projede AYNI arıza (yazılmış ama hiç çalışmayan kontrol) 3 kez tesadüfen
bulunmuştu — tam envanter çıkarıldı (workflow'lar, pre-commit, DB
kısıtları, kapı fonksiyonları), her biri KANITLI ATEŞLER / SINANMAMIŞ /
ATEŞLEYEMEZ diye işaretlendi. **2 YENİ ATEŞLEYEMEZ vaka bulundu, ikisi
de kasıtlı bozuk örnekle KANITLANDI:**
1. **`.pre-commit-config.yaml`'ın TÜMÜ (8 hook grubu)** — `.git/hooks/
   pre-commit` hiç kurulmamış, `pre-commit` CLI kurulu değil, hiçbir CI
   job'ı çağırmıyor. Konfigürasyon var ama SIFIR koruma sağlıyor.
2. **`worker/validate_rls_static.py`** — `SCHEMA_PATHS` 2026-08-19
   tarihli 3 dosyaya DONMUŞ, o tarihten sonraki 30+ migration'ı hiç
   okumuyor. `GRANT ALL ... TO anon` gibi açık bir ihlal bile
   `20260920_0001`'e eklenince script yine "passed" bastı.

Ayrıca `vw_toplama_*` view'lerinin `security_invoker=true` iddiası
sınandı — ilke DOĞRU (view sahibi BYPASSRLS'li) ama BU projenin rol
tasarımında (view+tablo grant'i her zaman birebir) ölçülebilir bir fark
YARATMADIĞI da kanıtlandı — "kısmen doğrulandı" olarak raporlandı.

**Kalıcı kural eklendi:** yeni bir otomatik kontrol, kasıtlı bozuk bir
örnekle ateşlediği gösterilmeden tamamlanmış sayılmaz
(`.github/copilot-instructions.md` + §16).

**Küçük borç kapatıldı:** "onay bekleyen batch" dashboard uyarısının
`AppTest` tabanlı testi yazıldı (`worker/tests/test_dashboard_
integration.py`) — 2 tur önce "Streamlit test altyapısı yok" gerekçesiyle
atlanmıştı, artık geçersiz.

**CANLIYA HİÇBİR ŞEY UYGULANMADI** (sınamalar disposable'da, deneme
sonrası geri alındı).

### ✅ Kapandı — JIT düzeltmesi + sqlfluff pre-commit + Zaman Serisi UI (2026-09-20, devam)

`Claude outputs/PROMPT_UI_ZAMAN_SERISI_2026-09-20.md`, kapanış raporu
`Claude outputs/kapanis_2026-09-20_ui_zaman_serisi.md`. Tam detay
`10_TEKNIK_MASTER_DOKUMAN.md` §15.8/§15.10/§5.35.

**Bölüm 1 — performans iddiası sınandı, ÇÜRÜTÜLDÜ:** önceki turun
"~715ms tek seferlik JIT derleme maliyeti" iddiası 5 AYRI bağlantıda
ölçüldü — JIT açıkken TUTARLI ~805-1280ms, `SET jit=off` ile TUTARLI
~102ms, 8× fark HER koşuda tekrarlanıyor (amortisman YOK). Canlıda da
(salt okuma) aynı yön doğrulandı. `worker/toplama.py`'ye `SET LOCAL
jit = off` eklendi, sonuç ~95-108ms'e düştü.

**Bölüm 2 — sqlfluff pre-commit:** hook zaten VARDI ama `files` deseni
bu repodaki gerçek yolla hiç eşleşmiyordu (önceki turun ilk push'ının
CI'de yakalanma kök nedeni) — düzeltildi, artık yerelde de çalışıyor.

**Bölüm 3 — Zaman Serisi UI:** dashboard'a yeni bir bölüm eklendi,
mevcut sayfa BOZULMADI. Altair KANITLANDI mevcut (streamlit'in kendi
bağımlılığı, YENİ bağımlılık YOK). Çözünürlük+aralık BAĞIMSIZ kontrol,
R12 açma/kapama, eksik-dönem görsel işaretleme, 2025→2026 dikiş
etiketi. `AppTest` (Streamlit'in resmi headless test aracı) ile uçtan
uca doğrulanırken 2 GERÇEK bug bulunup düzeltildi: namedtuple string-
indeksleme hatası VE aralık sınırının canlıda dar olan `fact_tuketim`'e
sabitlenmiş olması (YENİ `worker/toplama.py:veri_seti_tarih_araligi_
getir()` ile çözüldü, testle kanıtlandı). Ekran görüntüsü bu ortamda
ALINAMADI (tarayıcı otomasyonu yok).

Doğrulama: tam `worker/tests` (fresh disposable, 34/34 migration): 428
test, 427 geçti (tek beklenen `test_auth_integration.py`).
`ruff`/`mypy`/`bandit`/`sqlfluff` temiz. **CANLIYA YAZMA YOK** (yalnız
Bölüm 1'in salt-okuma ölçümü canlıda çalıştırıldı).

### ✅ Kapandı — Toplama katmanı (agregasyon), veri katmanı (2026-09-20)

`Claude outputs/PROMPT_TOPLAMA_KATMANI_2026-09-19.md` Bölüm 2, kapanış
raporu `Claude outputs/kapanis_2026-09-19_toplama_katmani.md`. Tam
detay `10_TEKNIK_MASTER_DOKUMAN.md` §15 (sözleşme) / §5.34 (özet).

Dashboard'un tek-ay sınırını aşıp çeyreklik/yıllık/uzun-dönem grafik
üretebilmesi için agregasyon katmanı — **yalnız veri katmanı, UI AYRI
bir tur.** 4 `vw_toplama_*` view (migration `20260920_0001`,
`security_invoker=true`, MATERIALIZED DEĞİL) + `worker/toplama.py` (7
fonksiyon: 4 tablo toplama + R12 + yenilenebilir oranı + dikiş bayrağı).
PROMPT'un 9 tasarım kararının TAMAMI uygulandı (itiraz yok); kapsam
bayrağının "kırılım-düzeyi mi tablo-düzeyi mi" ayrımı (2016-12 Tarımsal
vs Motorin/Nafta örneklerini uzlaştırmak için) BAĞIMSIZ bir mühendislik
kararıydı. Ölçüm: en pahalı sorgu (disposable, gerçekçi hacim) ~830ms
(JIT hariç ~130ms) — materialize etmeye GEREK YOK.

Doğrulama: tam `worker/tests` (fresh disposable, 34/34 migration): 426
test, 425 geçti (tek beklenen `test_auth_integration.py`). +17 yeni
test, madde 2/4/5/6/7'nin HER biri en az bir testle KANITLANDI.
`ruff`/`mypy` temiz, `bandit` 0 bulgu. **CANLIYA HİÇBİR ŞEY
UYGULANMADI.**

### ✅ Kapandı — Batch durum makinesinin kapatılması: `onay_bekliyor`/`onaylanmadi` + batch 4-8 CANLIDA kapatıldı (2026-09-19, batch durum turu)

`Claude outputs/PROMPT_BATCH_DURUM_2026-09-19.md`, kapanış raporu
`Claude outputs/kapanis_2026-09-19_batch_durum.md`. Tam detay
`10_TEKNIK_MASTER_DOKUMAN.md` §5.33.

Önceki turda (bkz. aşağıdaki "İş C" kaydı) bulunan İKİNCİ, KARDEŞ boşluk
kapatıldı: `pipeline.otomatik_onaya_uygun()` `False` döndüğünde
`job_worker.py` batch'i artık kalıcı bir duruma geçiriyor
(`'onay_bekliyor'`, TERMİNAL DEĞİL) + `audit_log`'a yazıyor — önceden
yalnız konsola yazıp `running`de bırakıyordu (gerçek örnek: batch 4-8, 19
gün fark edilmedi). Önerilen tasarıma (`onay_bekliyor`+`yerine_gecildi`)
gerekçeli KISMİ itiraz edildi: `dead_letter` reuse REDDEDİLDİ (job_status
coupling invariant'ı bozardı), durum sayısı 9'da kaldı ama dar
`yerine_gecildi` yerine genel `onaylanmadi` seçildi. CANLIDA: migration
`20260919_0001` uygulandı, batch 4-8 → `onaylanmadi` (5 audit_log satırı,
fact satırlarına DOKUNULMADI, 0 fark), dashboard'a `onay_bekliyor` uyarısı
eklendi. **Asıl başarı ölçütü sağlandı:** `running_batch_kontrolu.py`
artık TAMAMEN temiz (0 takılı, 0 onay bekleyen). Ayrıca (Görev 4, salt
okuma): `parser_version` bump disiplini için yazılı kural YOK bulgusu —
İş A Seçenek 3'ün ön koşulu olarak açık madde 5'e işlendi (yukarı bkz.).

Doğrulama: Tam `worker/tests` (fresh disposable, 33/33 migration): 409
test, 408 geçti (tek beklenen `test_auth_integration.py`). `ruff`/`mypy`
temiz, `bandit` 0 bulgu.

### ✅ Kapandı — Doğrulama turu (2026-09-17) + ⏳ İş A/İş C (2026-09-18, İş C kapandı, İş A açık)

**2026-09-17 — Doğrulama turu (commit `8b0da0f`):** `dokumanlar/kapsam_
raporu_2026-09-16.md`'nin 5 maddesi SALT OKUMA + gerçek EPDK .docx
dosyaları açılarak ölçüldü. Tam bulgu/sayılar orada ("Doğrulama Turu"
eki) — burada yalnız özet (D kuralı, tekrar yazılmaz):
- Madde 1 (batch 732): **KANITLANDI** — mutabakat gerçekten çalıştı,
  doğru sebeple bloke etti; ama audit_log'da bu kararın izi YOKTU (yalnız
  yükleme olayı kayıtlıydı), UNIQUE kısıtı yeniden yüklemeyi şema
  seviyesinde engellemiyordu, durum makinesinde "mutabakat reddetti"
  için terminal durum YOKTU — üçü de İş C'de kapatıldı (aşağıya bkz.).
- Madde 2 (fact_tuketim 2023-01/02, 79/81 il) [ÖNCELİKLİ]: **KANITLANDI**
  — eksik iller Adıyaman + Kahramanmaraş, EPDK'nın kendi dipnotu
  (06/02/2023 depremi, Akedaş mücbir sebep bildirimi) doğruladı, parser
  hatası DEĞİL.
- Madde 3 (mutabakat neden yakalamadı): **KANITLANDI** — tolerans
  boyutu sorun DEĞİL, yapısal bir kör nokta (iki karşılaştırılan değer
  de aynı eksik kaynaktan türüyor). YENİ kardinalite kontrolü eklendi
  (`mutabakat_ulke_geneli.il_kardinalite_kontrol_et()`), toleransa
  dokunulmadı.
- Madde 4 (kaynak_id sapması, 52 ay): monotonik-genişleme hipotezi
  **ÇÜRÜTÜLDÜ**; temsili kaynak kontrolü (1/15 aralık) parser hatası
  olmadığını gösterdi, TAM kapsamda **BELİRSİZ** kaldı.
- Madde 5 (fact_uretim 2022-07): **KANITLANDI, KAYITLI** — zaten
  `veri_kapsam_disi`de spesifik bir EPDK kopyala-yapıştır hatası
  gerekçesiyle.
- YENİ kalıcı script: `worker/scripts/running_batch_kontrolu.py`.

**2026-09-18 — İş A (source_asset dedup) + İş C (mutabakat_reddedildi
terminal durum)** (`Claude outputs/PROMPT_A_C_2026-09-17.md`, kapanış
raporu artık DOSYADA: `Claude outputs/kapanis_2026-09-18_A_C.md` — bkz.
YENİ çalışma kuralı, `.github/copilot-instructions.md`):

- **İş A — A1'de DURDURULDU, mükerrer bulundu (kullanıcı talimatı
  gereği A2/A3'e geçilmedi, A4 BAĞIMSIZ uygulandı):** canlıda **126
  mükerrer `file_hash` grubu** ölçüldü. 125'i established mimarinin
  BEKLENEN sonucu (1 fiziksel dosya → 4 farklı `parser_version` geçişi,
  her biri kendi `source_asset` satırını açıyor). 1'i GERÇEK (aynı hash +
  aynı parser_version) tekrar — ama bu 2026-08-31'de ZATEN belgelenip
  temizlenmiş bir idempotency-bug artığı (batch_id=19, sıfır aktif
  çift-satır kaldı). **Sonuç:** önerilen `UNIQUE(file_hash) WHERE
  file_hash IS NOT NULL` tasarımı mevcut mimariyle UYUMSUZ (125
  legitimate grubu da bloklardı) — dedup migration'ı (A2/A3) UYGULANMADI,
  3 tasarım seçeneği Ahmet'e sunuldu (bkz. kapanış raporu). **A4
  (dedup'tan bağımsız bir soru — bugünkü `batch_olustur()` davranışı)
  UYGULANDI:** artık TERMİNAL bir batch'e (succeeded/failed/dead_letter/
  mutabakat_reddedildi) denk gelirse SESSİZCE dönmüyor,
  `BatchZatenTerminalHatasi` fırlatıyor — dedup geldiğinde gerçek hâle
  gelecek bir riski ÖNCEDEN kapatıyor.
- **İş C — TAMAMLANDI (kod+test+disposable, CANLIYA UYGULANMADI):**
  `ingestion_batch.status`'a 7. terminal durum `'mutabakat_reddedildi'`
  eklendi (migration `20260918_0001`). `mutabakat_uretim.
  mutabakat_reddini_kaydet()` (YENİ) hem status SET eder hem
  `audit_log_yaz()` çağırır. `aktive_et_uretim_word.py` +
  `backfill_uretim_excel.py`'nin blok yolları TARANDI ve güncellendi
  (`onayla.py`/`toplu_onayla_word.py` mutabakat'a hiç bakmıyor, insan
  kararı — dokunulmadı; `job_worker.py:otomatik_onaya_uygun()` FARKLI/
  GEÇİCİ bir kavram, BİLİNÇLİ OLARAK yeni statüye dahil edilmedi). Geri
  dönülebilirlik (farklı `file_hash`li revize dosyayla aynı dönemin
  yeniden aktive olabilmesi) uçtan uca kanıtlandı.

Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.30/§6.1/§14 madde 5, Sürüm
Geçmişi v1.45. **CANLIYA HİÇBİR ŞEY UYGULANMADI** (migration/kod yalnız
disposable'da doğrulandı) — sıralı uygulama planı `Claude outputs/
kapanis_2026-09-18_A_C.md`'de, Ahmet onaylayacak.

### ✅ Kapandı — İki küçük iş: KPI-11/12 kart etiketi + `kpi_esik` (KPI-12) yeniden kalibrasyon (2026-09-16, devam)

Dashboard incelemesindeki 3 maddenin (bkz. aşağıdaki bölüm) hemen
ardından bulunan iki küçük ama gerçek iyileştirme. Tam detay/sayılar
`06_canli_veri_operasyon_gunlugu.md` 2026-09-16 (devam, "İki küçük iş")
kaydında.

1. **KPI-11/12 kart etiketi/kapsam notu:** Sanayi dikişi düzeltmesi
   canlıda doğrulanmıştı ama kartlar hâlâ yalnız "Arındırılmış Tüketim
   (KPI-11)" diyordu — Sanayi DAHİL KPI-08 (24,10 TWh) ile yan yana kafa
   karıştırıcı. Başlıklara "Sanayi Hariç" + Karar 2 referanslı tek
   cümlelik gerekçe eklendi (hem il-bazlı hem "Türkiye Geneli" kartlar).
   Hesaplama DEĞİŞMEDİ, yalnız metin.
2. **`kpi_esik` (KPI-12) MİSKALİBRE bulundu, yeniden kalibre edildi:**
   2026-09-05 seed'i KPI-12 için hiçbir ampirik gerekçe içermiyordu
   (diğer KPI'ların aksine) — aynı günün canlı ölçümü zaten %52-81
   aralığında değerler göstermişti, yani veriye bakılmadan seçilmiş.
   Sanayi dikişi düzeltmesi SONRASI canlıya karşı ölçülen gerçek dağılım
   (81 il × 5 ay, n=403): medyan=%19,1, p90=%31,0 — eski eşikle (yeşil≤5,
   sarı≤10) gözlemlerin ~%90'ı "kırmızı" gösteriyordu. Yeni eşik:
   `yesil_alt=15,0`, `sari_alt=30,0` (KPI-13/25/27'nin izlediği
   ampirik-persentil yöntemi). Migration `20260916_0001_kpi_esik_kpi12_
   yeniden_kalibrasyon.sql` — kilit ön kontrolü temiz, disposable'da
   (31/31) doğrulanıp **canlıya uygulandı**, canlıda `('KPI-12','v1',
   15.000,30.000,None,'alcelik')` teyit edildi. KPI-11'i girdi alan
   başka bir eşik YOK (kontrol edildi) — KPI-11 için ayrı bir değişiklik
   gerekmedi.

Doğrulama: kod değişikliği yalnız metin (dashboard.py) + config veri
(migration) — KPI-11/12'nin hesaplama mantığı DEĞİŞMEDİ, mevcut
regresyon testleri zaten onu pinliyor, yeni test gerekmedi. `ruff`/
`mypy` temiz. Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.29, Sürüm Geçmişi
v1.44.

### ✅ Kapandı — Dashboard incelemesinde bulunan 3 madde (2026-09-16, devam)

Canlı backfill'in AYNI GÜN sonrasında yapılan bir dashboard
incelemesinde 3 madde bulundu, üçü de ölçülüp düzeltildi. Tam detay/
sayılar `06_canli_veri_operasyon_gunlugu.md` 2026-09-16 (devam) kaydında
("Dashboard incelemesinde bulunan 3 madde" başlığı).

1. **KPI-11/12 "Sanayi dikişi" (ÖNCELİKLİ, gerçek hataydı):** canlıda
   KPI-12 (2026-06) sahte +%92,9 gösteriyordu. Kök neden ÖLÇÜLDÜ:
   `worker/analytics.py:_il_tuketim_hava_getir()` Sanayi'yi tutarsız
   kapsıyordu (Word yıllarında hiç yok — Karar 2 —, 2026'da var, ölçülen
   pay %40,2). Tercih sırasının 1. seçeneği (`fact_tuketim_ulke_
   geneli`'ye taşıma) il-bazlı β/γ regresyon mimarisiyle GERÇEKTEN
   ÇAKIŞTI (il kırılımı yok) — 2. seçenek (her iki taraf Sanayi-hariç)
   uygulandı. Düzeltme SONRASI KPI-12 +%15,4'e düştü. +2 test.
2. **job_status id=11 (8 gündür "retrying"de asılı):** araştırıldı —
   `correlation_id=118` hiçbir zaman gerçek bir `ingestion_batch`'e
   karşılık gelmiyordu, `locked_by='test-worker-1'` erken bir test
   kontaminasyonu artığı olduğunu gösteriyordu. Yeniden çalıştırmak
   yalnız 3 boşa retry'a yol açardı — doğrudan `dead_letter`'a alındı,
   `audit_log`'a tam gerekçeyle yazıldı. **Yapısal düzeltme:** YENİ
   `worker/analytics.py:gecmis_kalan_isleri_bul()` + dashboard'da
   expander'ın DIŞINDA görünür bir `st.warning()` — aynı sessiz-bekleme
   deseni artık görünmez kalmıyor. +6 yeni test (`test_analytics_pure.py`).
3. **KPI-26 açıklaması düzeltildi:** "henüz yeterli geçmiş (backfill)
   yüklenmemiş olabilir" YANLIŞTI — gerçek neden YAPISAL/KALICI (Karar
   3, Word yıllarında T1/Lisanslı hiç yok). Dashboard'a Karar 3'e AÇIKÇA
   referans veren ayrı bir kapsam notu eklendi (KPI-25/27'nin zaten
   sahip olduğu desene uyumlu). Kod hesaplama mantığı DEĞİŞMEDİ, yalnız
   METİN.

Doğrulama: `ruff`/`mypy` temiz, `bandit` yalnız 4 önceden var olan/
ilgisiz bulgu, tam `worker/tests` (fresh disposable) 363 test → 362
geçti (tek beklenen `test_auth_integration.py`). Streamlit canlıya karşı
başlatılıp HTTP 200 + sunucu loglarında hata OLMADIĞI doğrulandı (tam
interaktif/browser testi bu ortamda yapılamadı — dashboard'un kullandığı
TÜM hesaplama fonksiyonları doğrudan çağrılarak canlı veriyle AYRICA
doğrulandı). Detay: `10_TEKNIK_MASTER_DOKUMAN.md` §5.28, Sürüm Geçmişi
v1.43.

### ✅ Kapandı — CANLI BACKFILL ÖN-UÇUŞ PLANI, UYGULANDI (2026-09-16)

**Bu bölüm ARTIK UYGULANDI (aşağıdaki 5 madde BİREBİR takip edildi) —
tarihsel referans olarak bırakıldı, yeniden aksiyon gerektirmiyor.**

**1) Eksik migration var mı?** **HAYIR.** ADIM 4'ün Word üretim
backfill'i için gereken TÜM şema zaten canlıda: `fact_uretim_kaynak_
geneli`+`fact_uretim_il_geneli` (migration `20260909_0001`) ve
`veri_kapsam_disi.fact_tablosu` CHECK genişletmesi (migration
`20260909_0002`) — ikisi de 2026-09-09'da canlıya UYGULANDI (bkz.
`10_TEKNIK_MASTER_DOKUMAN.md` v1.25). Bu iki migration'dan SONRA (ADIM
4'ün TAMAMI boyunca) `supabase/migrations/`'a HİÇBİR yeni dosya
eklenmedi (`git log -- supabase/migrations/` ile doğrulandı, 30 dosya
sabit kaldı) — Motorin/LPG gibi yeni kaynak türleri bile ÖNCEDEN var
olan `dim_kaynak` seed'leriyle (migration `20260819_0007`) çözüldü,
YENİ migration gerekmedi. **Sonuç: canlı backfill saf VERİ yüklemesi,
DDL değişikliği YOK.**

**2) Kaç ay/satır yüklenecek, hangi aylar kapsam dışı/aktive edilmeyecek?**
Disposable'daki 120-ay doğrulama turunun BİREBİR AYNISI canlıda
tekrarlanacak:
- **Yüklenecek:** `fact_uretim_kaynak_geneli`'ne 120 ay (2016-01 →
  2025-12, ~1.393 satır), `fact_uretim_il_geneli`'ne 119 ay (2024-02
  HARİÇ, ~9.639 satır).
- **Kapsam dışı (Lisanssız, T5/T6):** 120 ayın TAMAMI, HER İKİ tabloda
  — Bulgu D/L kararı (`karar_referansi='Bulgu L (2026-09-13, ölçümle
  doğrulandı)'` veya yıla göre `'Karar 4 genişletildi'`), `nitelik=
  'lisans_durumu=Lisanssız'`.
- **Kapsam dışı (Lisanslı, TEK istisna):** 2024-02'nin `fact_uretim_il_
  geneli` verisi — Bulgu J (`karar_referansi='Bulgu J (2026-09-13, EPDK
  kaynak belge hatası)'`, `nitelik='lisans_durumu=Lisanslı'`) — T3'ün o
  ay Ocak'ın birebir kopyası olduğu ÖLÇÜLEREK doğrulandı, T2 (kaynak)
  sağlam, yalnız T2 yüklenecek.
- **Aktive EDİLMEYECEK aylar:** hiçbiri otomatik aktive edilmeyecek —
  aşağıdaki madde 3'e bkz. (mutabakat kontrolü aktivasyondan ÖNCE
  şart).

**3) Mutabakat kontrolünün aktivasyondan ÖNCE çalışacağının teyidi:**
`worker/scripts/mutabakat_uretim.py:periyot_aktivasyona_uygun_mu()`
zaten (ADIM 3 madde 3'te, 2026-09-09'da) canlıda doğrulanmış bir
mekanizma — `otomatik_onaya_uygun()`/manuel `onayla.py` akışı bu
fonksiyonu ÇAĞIRMADAN bir (tarih_id, lisans_id) çiftini aktive ETMEZ.
Backfill script'lerinin KENDİSİ (`word_20XX.py --uretim-geneli`)
`pipeline.batch_onayla()`'yı HİÇ ÇAĞIRMIYOR (gece-boyu kural, TÜM
batch'ler bilinçli olarak `running`/`is_active=false` bırakılıyor) —
yani yükleme adımı ile aktivasyon adımı ZATEN AYRI, aktivasyon YALNIZ
mutabakat kontrolü 202402 DIŞINDAKİ TÜM aylarda "uyumlu" derse elle/
ayrı bir adımda tetiklenecek. **Önerilen sıra:** (a) 120 ayı yükle →
(b) `mutabakat_uretim.py`'yi canlıya karşı çalıştır, disposable'daki
119/120 sonucunu BİREBİR doğrula → (c) YALNIZ uyumlu aylar için
aktivasyon (202402 zaten kapsam dışı olduğundan `bir_taraf_eksik`
durumu aktivasyonu DOĞAL olarak engeller, `periyot_aktivasyona_uygun_
mu()` onu reddeder).

**4) Geri alma yolu (bir şey ters giderse):** Yükleme adımı (batch
oluşturma + fact satırları yazma) `running`/`is_active=false` bırakır —
**bu adım kendiliğinden GERİ ALINABİLİR risk taşımıyor**, çünkü hiçbir
mevcut canlı sorgu/dashboard `is_active=false` satırları GÖRMEZ (RLS/
sorgu katmanı zaten yalnız aktif satırları döndürüyor — ADIM 3'ten beri
established davranış). Eğer yükleme YARIDA kalırsa: (a) o ayın batch'i
`running` kalır, sonraki koşu `[ATLA] ... zaten işlenmiş` diyerek
GÜVENLE atlar (idempotent, established pattern — TÜM `word_20XX.py`
script'lerinde `ingestion_batch` üzerinde `source_period`+
`parser_version` kontrolü var); (b) eğer bir batch YANLIŞ veri içeriyor
tespit edilirse, aktivasyon TEK bir transaction içinde yapıldığından
(`pipeline.batch_onayla()`, ADIM 3'te canlıda doğrulanmış davranış) HENÜZ
aktive edilmemiş satırlar zaten "canlı görünürlükte" DEĞİL — düzeltme
yalnız o batch'i `failed` işaretleyip yeniden çalıştırmak. **Aktivasyon
SONRASI bir sorun bulunursa** (nadir, çünkü mutabakat+kapsam-dışı
kontrolleri önceden koşuyor): `is_active=false` yaparak GERİ ALINABİLİR
— şema `ON CONFLICT`/`is_active` sütunu üzerinden çalışıyor, DELETE
GEREKMİYOR (established pattern, ADIM 3 madde 4'ün canlı uygulamasında
KULLANILMADI ama mekanizma migration `20260909_0001`'de zaten mevcut).

**5) Kilit riski — Streamlit bağlantısı ön kontrolü:** 2026-09-07'de
`C4` migration'ı (`20260907_0001`), `app_dashboard_service` rolüyle
Supavisor üzerinden 3+ saattir "idle in transaction" kalmış TERK
EDİLMİŞ bir Streamlit oturumunun `job_status` üzerindeki kilidi yüzünden
`QueryCanceled: statement timeout` ile durmuştu (bkz.
`06_canli_veri_operasyon_gunlugu.md` 2026-09-07 kaydı) — bağlantı
yalnız salt-okunur bir SELECT çalıştırdığı için `pg_terminate_backend()`
ile güvenle sonlandırılmıştı. **Backfill YALNIZ veri yazıyor (DDL/ALTER
TABLE YOK), o yüzden AYNI sınıf lock-timeout riski DAHA DÜŞÜK** ama
YİNE DE ön kontrol önerilir: backfill'e başlamadan önce
```sql
SELECT pid, usename, state, state_change, query
FROM pg_stat_activity
WHERE state = 'idle in transaction' AND state_change < now() - interval '10 minutes';
```
ile uzun süredir asılı kalmış bağlantı VAR MI kontrol edilmeli — varsa,
2026-09-07'deki AYNI karar kuralı uygulanır (yalnız salt-okunur/eski bir
oturumsa `pg_terminate_backend()` ile güvenle sonlandırılır, YAZMA
işlemi yapan bir bağlantıysa DOKUNULMAZ, araştırılır).

**Özet — canlı backfill'in sırası (onay SONRASI, bu turun kapsamı
DIŞINDA):** ön kontrol (madde 5) → 120 ayı yükle (madde 2) →
`mutabakat_uretim.py`'yi canlıya karşı çalıştır, disposable'daki 119/120
sonucunu doğrula (madde 3) → yalnız uyumlu aylar için aktivasyon →
canlı KPI-02/03/06/07'nin Word yılları için de doğru değer ürettiğini
spot-check et (ADIM 5'in wiring'i zaten `tarih_id` parametrik, ekstra
kod GEREKMEZ) → `09_PROJE_DURUMU.md`/ops log'a sonucu yaz.
  - **ADIM 5'in wiring'i sırasında bulunan, ADIM 4'ü ucuzlatan notlar
    (hâlâ geçerli):**
  - `lisans_id` çözümü: **DOĞRULANDI, 2025 için ÇALIŞTI** — `t2_oku()`/
    `t3_oku()`/`t5_oku()` `"lisans"` alanını ("Lisanslı"/"Lisanssız")
    kendi çıktılarına doğrudan gömüyor, `ingest.fact_uretim_kaynak_
    geneli_yukle()`/`fact_uretim_il_geneli_yukle()` bunu (Excel'deki
    AYNI şekilde) `dim_lisans_id_bul()` ile çözüyor — YENİ bir mekanizma
    gerekmedi, tahmin doğru çıktı.
  - **✅ KPI-07 'hesaplanamaz' geçişi — TAMAMLANDI ve DÜZELTİLDİ
    (2026-09-16).** Bu maddenin ORİJİNAL (2026-09-09) hali YANLIŞ bir
    varsayım içeriyordu: "`uretim_kaynak_geneli_getir()` kapsam dışı
    yıllarda BOŞ DataFrame döner, `kpi_07_lisanssiz_pay()` zaten `None`
    döner" diyordu. Canlı backfill SONRASI ÖLÇÜLDÜ — YANLIŞTI: Word
    yıllarında Lisanslı veri VAR (boş DEĞİL), yalnız Lisanssız satırları
    HİÇ YOK — eski kod bunu YAKALAMIYOR, sessizce yanlış bir '%0'
    üretiyordu. Düzeltme: `kpi_07_lisanssiz_pay()` artık zorunlu
    `lisanssiz_kapsam_disi` parametresi alıyor, `app/dashboard.py` bunu
    `veri_kapsam_disi`'den (`analytics.kapsam_disi_getir()`) HER ZAMAN
    hesaplayıp geçiriyor. Detay: `06_canli_veri_operasyon_gunlugu.md`
    2026-09-16 (devam) kaydı, `04_kpi_sozlesmeleri.md` KPI-07 notu.
  - `kapasite_faktoru_girdisi_getir()` Word yılları için de OLDUĞU GİBİ
    çalışır (SQL sorguları `tarih_id` parametrik, tabloya Word verisi
    hangi batch'ten gelirse gelsin AYNI filtre mantığı geçerli) — ADIM
    4'te KPI-05 için ayrı bir wiring GEREKMEZ, yalnız veri dolunca
    otomatik doğru değer üretir.
- **Sonrası — Faz 4 (Tahminleme):** ADIM 4 bittikten SONRA gündemde,
  kapsam kararı HÂLÂ bekliyor (aksiyon gerektirmiyor) — detay aşağıda
  "Faz 4 (Tahminleme)" bölümünde.
- **Kontrol edildi, açık madde DEĞİL:** `conftest.py` canlı-DB koruması
  regresyon testi (`worker/tests/test_conftest_guard.py`) 2026-09-09
  gecesinde zaten eklenmişti — bu turda yeniden doğrulandı, hâlâ mevcut
  ve ✅ Kapandı olarak aşağıda listeli, tekrar açık madde değil.

### ✅ Kapandı — `conftest.py` canlı-DB koruması artık kendi regresyon testine sahip (2026-09-09, gece çalışması MADDE 0)
Aynı koruma (`worker/tests/conftest.py:pytest_configure()`) daha önce
**iki kez** atlanmıştı: 2026-09-02'de ilk kez (koruma o zaman hiç yoktu)
ve 2026-09-08'de İKİNCİ kez (koruma VARDI ama `.env`'in `load_dotenv()`
ile kontrolden SONRA yüklenmesi yüzünden atlandı — bkz. `06_canli_veri_
operasyon_gunlugu.md` 2026-09-08 (devam) kaydı, düzeltme commit
`df616e6`). **2026-09-09'da `worker/tests/test_conftest_guard.py`
eklendi** (ayrı dosya, `conftest.py`'nin İÇİNE değil — kendini test
ederken kendini bypass etmesin diye): gerçek `conftest.py`'nin GÜNCEL
kaynağını izole bir sahte projeye kopyalayıp subprocess olarak çalıştırır,
3 senaryo doğrular — (1) `DATABASE_URL` doğrudan sahte-canlı bir URL'e
set edilince `exit code 3`, (2) 2026-09-08 bug'ının BİREBİR
reprodüksiyonu: `DATABASE_URL` kabukta YOK, yalnız `.env`'de var, yine de
`exit code 3` (bu senaryo eski/buggy koda karşı BİLİNÇLİ olarak
çalıştırılıp GERÇEKTEN yakaladığı kanıtlandı — geçici olarak eski koda
dönülüp test'in kırıldığı görüldü, sonra düzeltme geri alındı), (3)
`ALLOW_DESTRUCTIVE_TESTS=true` kaçış kapısı hâlâ çalışıyor. Üçüncü bir
sessiz atlama artık pytest seviyesinde kilitli.

### C6 — ertelenmiş/değerlendirilmiş küçük maddeler (yalnız referans, aksiyon BEKLEMİYOR)
- **MFA / merkezi rate-limit:** ertelendi (tek admin kullanıcı var).
- **Veri girişi UI'ı + admin rol-atama UI'ı:** ertelendi (2026-09-05
  kararı, `data_operator`'ın RLS altyapısı hazır ama UI'ı yok, yeni
  kullanıcı eklemek hâlâ elle/Supabase Dashboard'dan).
- **HDD/CDD çok noktalı il temsili:** Faz 4 öncesi bir kez ölçülüp
  karara bağlanacak, şimdi değil (tek nokta/il varsayımı şu an bilinçli
  bir metodolojik sınırlama olarak duruyor).
- **`deploy.yml`'in `build-push` job'ı:** hâlâ `if: false` ile devre
  dışı (`web/` klasörü ve Dockerfile'lar henüz yok) — `migrate`/
  `deploy-ssh`/`smoke` job'ları buna `needs` bağlı olduğundan fiilen hiç
  çalışmıyor.
- **Yeni bir KPI numarası gerekirse KPI-29'dan başla** — KPI-28 slotu
  `05_kaynak_dosya_sozlesmesi.md`'de zaten rezerve (tanımlı ama
  implemente edilmemiş), çakışma olmasın.
- Diğerleri (Strategy Pattern, `word_20XX.py` refactor'ü vb.) zaten
  REDDEDİLDİ/KAPANDI — yeniden açılmasın.

### Faz 4 (Tahminleme) — Aşama 3'ten SONRA, henüz başlamadı
Kapsam kararı bekliyor. **Öneri (karar verilmedi, yalnız öneri):**
Eskişehir pilotu + seasonal-naive baseline ile başla — küçük, tek-il
kapsamlı bir kanıt-of-concept, tam bir tahminleme motoruna atlamadan
önce. 10 yıl gerçek veri artık var (2016-2025), bu kararı gözden
geçirmek için önceki turlarda "erken" denen gerekçe artık geçerli değil.

### ✅ Kapandı — İlk gerçek cron koşusu doğrulandı (2026-09-13)
`scheduled-backup.yml`'in cron'u (`0 3 * * 0`) 2026-09-13 Pazar günü
İLK KEZ `schedule` tetikleyicisiyle (elle `workflow_dispatch` DEĞİL)
gerçekten koştu — run `34747084899`, `success`, artifact `epp-backup-
34747084899` (1.657.776 bayt, retention tam 90 gün). Tek dikkat çeken
nokta: 03:00 UTC yerine 08:11:52 UTC'de tetiklendi (~5s11dk gecikme) —
GitHub'ın dokümante edilmiş `schedule` gecikme davranışı (yoğun yük
dönemlerinde dakikalar-saatler mertebesinde), repo hareketsizliğiyle
İLGİSİZ (bu repoda güncel commit aktivitesi var). Detay: `06_canli_veri_
operasyon_gunlugu.md` 2026-09-13 kaydı. Açık madde YOK, tekrar kontrol
gerekmiyor (mekanizma kanıtlandı).
