# EPP — Çalışma kuralları

## Dil ve üslup

- Türkçe yaz. Kısa ve net ol, gereksiz uzatma.
- "Muhtemelen" yazma. Bir şey kanıtlandıysa "kanıtlandı", çürütüldüyse
  "çürütüldü", bilinmiyorsa "belirsiz" yaz.

## Canlı veritabanı

- Bu makinede .env YOK. Canlıya hiçbir yazma işlemi yapma.
- Canlı DDL/DML her zaman açık onay gerektirir. Varsayılan --dry-run.

## Veri bütünlüğü

- Sahte KPI üretilmez. Hesaplanamayan değer NULL döner, uydurma 0 değil.
- "Kaynak satırı yok" ile "veri yok" aynı şey değildir (veri_kapsam_disi).
- Kümülatif kolon asla toplanmaz. Oranlarda önce topla, sonra oranla.

## Belgeleme

- Tarih çapası: her sayı bir tarihe bağlanır.
- D kuralı: durum ve sayılar yalnız 09_PROJE_DURUMU.md ve
  10_TEKNIK_MASTER_DOKUMAN.md içinde yaşar.
- Payda her zaman dinamik hesaplanır, sabit sayı yazılmaz.

## Kontroller

- Bir kontrol, kasıtlı bozuk bir örnekle ateşlediği gösterilmeden
  tamamlanmış sayılmaz.
- Kalite kapısı: ruff, mypy, bandit, sqlfluff temiz. Test paketi aynı
  veritabanında iki kez birebir aynı sonucu vermeli.
