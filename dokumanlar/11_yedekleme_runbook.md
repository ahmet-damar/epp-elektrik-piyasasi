# EPP — Yedekleme + Geri Yükleme Runbook

> **STATUS: ACTIVE (runbook)** — elle çalıştırılan, GERÇEKTEN denenmiş bir
> kurtarma prosedürü. Sayı/durum değişmez, yalnız prosedür değişirse
> güncellenir. 2026-09-07 denetimi (C1).

## Neden bu doküman var

13 dokümanlık dış denetime kadar "backup" kelimesi projede **sıfır kez**
geçiyordu. Elde: 120 ay elle transkribe edilmiş EPDK Word/Excel verisi +
Open-Meteo'nun dokümante edilmemiş saatlik kotası yüzünden **~3 saat**
süren bir hava backfill'i — **tek kopya**, kazayla silinirse yeniden
üretimi saatler alır (hava backfill'i aynı kota engeliyle tekrar
karşılaşabilir).

## Supabase'in kendi yedekleme politikası — bu proje **Free plan**'de

**Doğrulandı (Supabase resmî dokümantasyonu, 2026-09-07):**

| Plan | Otomatik günlük yedek | Saklama | PITR |
|---|---|---|---|
| **Free (bu proje)** | **YOK** | — | — |
| Pro | Var | Son 7 gün | Ek ücretli (~$100/ay, 7 gün) |
| Team | Var | Son 14 gün | Ek ücretli (~$200/ay, 14 gün) |
| Enterprise | Var | 30 güne kadar | Ek ücretli (~$400/ay, 28 gün) |

**Sonuç: Supabase bu proje için HİÇBİR otomatik yedek almıyor.** Tüm
sorumluluk aşağıdaki elle prosedürdedir — bu C1'i projedeki **en yüksek
gerçek operasyonel risk** yapan şey tam olarak bu.

## Yedekleme kapsamı — yalnız VERİ, şema değil

`public` şemasının DDL'i (tablolar/RLS/policy/fonksiyon/rol) zaten
`supabase/migrations/`'da tam olarak version-control altında — sıfırdan
bir Supabase projesine migration'ları sırayla uygulayarak birebir yeniden
üretilebilir (`ci.yml`'in `integration` job'ı bunu her koşuda zaten
kanıtlıyor, bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §9.1). Gerçekten TEK
KOPYASI olan şey VERİDİR. Bu yüzden:

- **Şema** → migration'lardan yeniden kurulur (kod zaten kaynak).
- **Veri** → `worker/scripts/backup.py`'nin ürettiği `pg_dump --data-only`
  dump'ından `pg_restore` ile geri yüklenir.

6 tablo (`dim_il`/`dim_kaynak`/`dim_lisans`/`dim_tuketici_grubu`/
`kpi_esik`/`sistem_parametre`) dump'a DAHİL EDİLMEZ — bunlar seed
migration'ları (`20260819_0004`, `20260905_0001`) tarafından zaten
oluşturulur; dahil edilselerdi restore'da zararsız ama gürültülü
"duplicate key" hatası verirlerdi (ilk denemede gerçekten görüldü, bkz.
aşağıdaki "Gerçek deneme" bölümü). `dim_tarih` DAHİL — o statik bir seed
DEĞİL, ingestion pipeline'ı her ay işledikçe büyür.

## Ortam notu — pg_dump/pg_restore bu makinede yok

Bu proje Windows'ta geliştiriliyor; `pg_dump`/`pg_restore` yerelde PATH'te
YOK (ve Windows Smart App Control geçmişte native paketleri engellemişti,
bkz. §11.5 master doküman). En güvenilir yol: WSL2 içindeki Docker (Docker
Desktop'a değil, WSL'in kendi native Docker Engine'ine bağlı — `docker
ps` WSL içinde doğrudan çalışıyor, `adamar` kullanıcısı `docker` grubunda).

```bash
wsl -d Ubuntu -- bash -c '
  cd /mnt/c/Projeler/epp-elektrik-piyasasi
  DATABASE_URL=$(grep "^DATABASE_URL=" .env | cut -d= -f2- | tr -d "\r")
  mkdir -p ~/epp_yedekler
  docker run --rm -v ~/epp_yedekler:/backup postgres:17 \
    pg_dump "$DATABASE_URL" --schema=public --data-only --no-owner --disable-triggers \
      --exclude-table=public.dim_il --exclude-table=public.dim_kaynak \
      --exclude-table=public.dim_lisans --exclude-table=public.dim_tuketici_grubu \
      --exclude-table=public.kpi_esik --exclude-table=public.sistem_parametre \
      --format=custom --file=/backup/epp_data_$(date -u +%Y%m%dT%H%M%SZ).dump
'
```

(`worker/scripts/backup.py`, tam olarak bu `pg_dump` çağrısını sarmalar —
`pg_dump` PATH'te varsa doğrudan, yoksa yukarıdaki gibi WSL/Docker
içinden bu script'i çağırın: `wsl -d Ubuntu -- python3 ...` ya da dump
dosyasını Windows'a `/mnt/c/...` üzerinden kopyalayıp orada saklayın.)

**Önerilen sıklık:** her büyük backfill/toplu aktivasyon turundan sonra
elle (ör. bu proje 120 ay + 599 satırlık `fact_tuketim_ulke_geneli`
turunu yeni bitirdi — böyle bir turdan hemen sonra bir yedek alınmalı),
aksi halde ayda bir. **Dump dosyası Supabase'in KENDİSİNDEN AYRI bir yerde
saklanmalı** (yerel disk + tercihen ayrıca bulut depolama/harici disk) —
yalnız Supabase'in kendi altyapısında tutmak "tek kopya" riskini gerçekte
azaltmaz.

## Geri yükleme prosedürü — GERÇEKTEN denendi (2026-09-07)

Aşağıdaki adımlar bir kez uçtan uca gerçekten çalıştırıldı (disposable
`postgres:17` container, canlı Supabase'e HİÇBİR YAZMA olmadan — yalnız
`pg_dump` salt-okunur):

1. **Disposable hedef başlat:**
   ```bash
   docker network create epp_restore_net
   docker run -d --name epp_restore_target --network epp_restore_net \
     -e POSTGRES_PASSWORD=test -e POSTGRES_DB=epp_restore postgres:17
   ```
2. **Şemayı migration'lardan kur** (ci.yml'in `integration` job'ıyla
   AYNI sıra — roller bootstrap → 0001 → auth stub → kalan tüm
   migration'lar glob ile, bkz. `10_TEKNIK_MASTER_DOKUMAN.md` §9.1):
   ```bash
   psql "$TARGET_URL" -f supabase/ci-only/01_roles_bootstrap.sql
   psql "$TARGET_URL" -f supabase/migrations/20260819_0001_init_schema.sql
   psql "$TARGET_URL" -f supabase/ci-only/00_auth_stub.sql
   for f in $(ls supabase/migrations/*.sql | sort); do
     [[ "$f" == *20260819_0001_init_schema.sql ]] && continue
     psql "$TARGET_URL" -f "$f"
   done
   ```
3. **Veriyi geri yükle:**
   ```bash
   pg_restore --data-only --no-owner --disable-triggers -d "$TARGET_URL" epp_data_*.dump
   ```
4. **Satır sayılarını canlıyla karşılaştır** (aşağıdaki tablo tam olarak
   bu adımın gerçek çıktısıdır).

### Gerçek deneme sonucu (kanıt)

İlk denemede 6 seed tablosu dump'a dahildi ve pg_restore bunlar için
"duplicate key" hatası verdi (`errors ignored on restore: 6` — zararsız
ama beklenmedik görünüyordu); bu, `backup.py`'ye `--exclude-table`
eklenmesinin doğrudan sebebi oldu. Düzeltmeden sonra **ikinci deneme
sıfır hatayla tamamlandı** ve restore edilen 19 tablonun **TAMAMI** canlı
Supabase'deki gerçek `COUNT(*)` değerleriyle **birebir eşleşti**:

| Tablo | Canlı Supabase | Restore edilen | Eşleşti mi |
|---|---|---|---|
| audit_log | 740 | 740 | ✅ |
| dim_il | 81 | 81 (seed'den) | ✅ |
| dim_kaynak | 13 | 13 (seed'den) | ✅ |
| dim_lisans | 2 | 2 (seed'den) | ✅ |
| dim_tarih | 128 | 128 | ✅ |
| dim_tuketici_grubu | 5 | 5 (seed'den) | ✅ |
| fact_abone | 25.110 | 25.110 | ✅ |
| fact_hava_aylik | 10.368 | 10.368 | ✅ |
| fact_hava_aylik_log | 10.611 | 10.611 | ✅ |
| fact_serbest_tuketici | 9.348 | 9.348 | ✅ |
| fact_tuketim | 44.458 | 44.458 | ✅ |
| fact_tuketim_ulke_geneli | 599 | 599 | ✅ |
| fact_uretim | 56.794 | 56.794 | ✅ |
| ingestion_batch | 503 | 503 | ✅ |
| job_status | 8 | 8 | ✅ |
| kpi_esik | 6 | 6 (seed'den) | ✅ |
| sistem_parametre | 4 | 4 (seed'den) | ✅ |
| source_asset | 503 | 503 | ✅ |
| veri_kapsam_disi | 311 | 311 | ✅ |

**19/19 tablo eşleşti, 0 hata.** Bu, "denenmemiş yedek yedek değildir"
ilkesinin bu proje için gerçekten karşılandığı anlamına gelir — teorik bir
prosedür değil, bir kez gerçekten işlediği kanıtlanmış bir prosedürdür.

## Bilinen sınırlamalar

- Bu drill **yerel/disposable** bir hedefe restore etti, gerçek bir yeni
  Supabase projesine DEĞİL — Supabase projesi oluşturma/env değişkenleri
  güncelleme adımı ayrıca (elle, felaket anında) yapılmalı.
- `auth.users` (Supabase'in kendi Auth tablosu) bu dump'ın KAPSAMI DIŞI —
  kullanıcı hesapları Supabase Auth'un kendi altyapısında; bu runbook
  yalnız `public` şemasındaki iş verisini kapsıyor.
- Otomatik/zamanlı bir yedekleme (ör. cron/GitHub Actions ile günlük)
  henüz KURULMADI — bu tur yalnız elle çalıştırılabilir script + denenmiş
  prosedürü sağladı. Otomasyon C bölümünün ölçek/öncelik kararına bağlı,
  bu turun kapsamı dışında bırakıldı.
