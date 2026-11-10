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
- pre-commit'teki mypy HIZLI BİR YAKLAŞIMDIR, otorite değildir. Otorite
  CI'daki mypy'dir — projenin gerçek bağımlılıklarıyla koşar. 2026-11-10'da
  yerel hook `altair`'ı görmediği için gerçek bir tip hatasını kaçırdı, CI
  yakaladı. Yerel hook'un eksik kalması beklenen bir durumdur; CI yeşil
  olmadan iş bitmiş sayılmaz.
- Kalite kapısındaki her araç (ruff, mypy, prettier, sqlfluff) hem
  `.pre-commit-config.yaml`'da hem `requirements-dev.txt`'te AYNI kesin
  sürüme sabitlenir. Sabitsiz bir araç, kod değişmeden kapıyı kırabilir
  veya iki kapının farklı şeyler görmesine yol açar. 2026-11-10'da bu üç
  ayrı araçta üç kez yaşandı.
