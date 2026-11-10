# Kapanış — 2026-11-10: Altyapı + Dashboard Bulguları

Bu dosya `Claude outputs/` dizininde — bilinçli olarak `.gitignore`'da
tutulan diğer prompt dosyalarının AKSİNE bu dosya git'e işlendi (bkz.
`09_PROJE_DURUMU.md` madde 9 — önceki prompt dosyalarının bir kısmı
commit edilmediği için yeni bir klonda bulunamıyordu, bu turda bu
tekrarlanmadı).

## 1) "Sanayi hariç" etiketi ile seri çelişkisi — ÇÖZÜLDÜ

**Ölçüm:** `app/dashboard.py:1301`'deki "Tüketim (il×grup, Sanayi
hariç)" veri setinin kaynağı `vw_toplama_tuketim_aylik`
(`supabase/migrations/20260920_0001_toplama_katmani_views.sql:54-69`).
View'in SQL'i okundu: `grup_adi`/`grup_id` üzerinde HİÇBİR WHERE/filtre
yok — `fact_tuketim`'de ne varsa aynen döner. Yani kod Sanayi'yi
filtrelemiyor DEĞİL çünkü filtrelemesi gerekmiyordu: `worker/toplama.py`
madde 8 (`donem_araligi_dikis_iceriyor_mu()` docstring'i) ve
`app/dashboard.py:738-739`'daki yorum bunu doğruluyor — Sanayi, Word
yıllarında (2016-2025) il kırılımında hiç yoktu (Karar 2), 2026'dan
itibaren (Excel dönemi) fiilen seriye giriyor. Bu YAPISAL bir geçiş,
filtre hatası değil.

**Sonuç:** İhtimal (a) doğru çıktı — etiket eskimiş, veri doğruluğu
hatası YOK, öncelik yükseltilmedi.

**Değişiklik:** `app/dashboard.py:1301` etiketi "Tüketim (il×grup,
Sanayi hariç)" → **"Tüketim (il×grup, 2016-2025 Sanayi hariç)"**
yapıldı — artık 2026+ için yanlış bir evrensel iddia taşımıyor. Var
olan 2025↔2026 dikiş dipnotu (`app/dashboard.py:1455-1460`) sınır-aşan
seçimlerde bu geçişi zaten ayrıca açıklıyor; bu iki bilgi birbirini
tamamlıyor, çakışmıyor.

## 2) Kapsam uyarısı yanlış sebep gösteriyor — ÇÖZÜLDÜ

**Ölçüm:** `worker/toplama.py:_kapsam_ve_deger_df()` — `tam_mi =
(beklenen_donem_sayisi = mevcut_donem_sayisi) AND (il_sayisi_min =
BEKLENEN_IL_SAYISI=81 ise)`. Bayrak koşulu okundu: dönem sayısı VE il
kardinalitesi olmak üzere İKİ AYRI şart var. Dashboard'un eski mesaj
kodu (`app/dashboard.py`, eksik-dönem uyarısı) yalnız
`mevcut_donem_sayisi`/`beklenen_donem_sayisi`'ni yazıyordu —
`il_sayisi_min` hiç gösterilmiyordu. "Kamu ve Özel Hizmetler: 1/1
dönem" örneğinde dönem şartı zaten sağlanıyor (1=1); bayrağı düşüren
TEK ihtimal il kardinalitesi şartıdır — bu da DOĞRULADI: bayrak doğru
çalışıyor, mesaj yanlış sebep gösteriyor (anlatım hatası, kod hatası
değil).

**Değişiklik:** `app/dashboard.py`'de `_zs_eksik_sebebi()` adlı yardımcı
fonksiyon eklendi. Mesaj artık hangi şart(lar) düştüyse onu açıkça
yazıyor, örnek: `"2026-07 (Kamu ve Özel Hizmetler: 78/81 il)"` (dönem
şartı zaten sağlanıyorsa onu hiç yazmıyor, sağlanmıyorsa "X/Y dönem"
ekliyor — iki şart aynı anda düşebilir, ikisi de yazılır).
`il_sayisi_min` kolonu yalnız `il_kirilimi_var_mi=True` olan veri
setlerinde (tüketim il×grup, üretim il toplamı) var; diğer ikisinde
(`tuketim_ulke_geneli`, `uretim_kaynak_geneli`) yok — kod bunu
`"il_sayisi_min" in zs_df.columns` ile kontrol ediyor, olmayan kolona
erişmeye çalışmıyor.

## 3) Lejant iki kez çiziliyor — ÇÖZÜLDÜ

**Ölçüm:** `_zs_grafik_ciz()` iki katmanı AYNI alanı (`kirilim_kolonu`)
renklendiriyor: `cizgi` → `color=alt.Color(f"{kirilim_kolonu}:N",
title="Kırılım")`, `noktalar_tam` → `color=f"{kirilim_kolonu}:N"` (kısa
yazım, başlıksız). Fonksiyonun son satırı
`.resolve_scale(color="independent")` çağırıyordu. Sentetik veriyle
gerçek Vega-Lite spec'i üretilip incelendi (`chart.to_dict()`):

- `resolve_scale(color="independent")` VARKEN: spec'te
  `"resolve": {"scale": {"color": "independent"}}` anahtarı oluşuyor —
  bu, Vega-Lite'a iki katmanın renk skalasını BİRLEŞTİRME diyor, sonuç
  iki ayrı skala/lejant.
- Bu satır KALDIRILINCA: `"resolve"` anahtarı spec'te hiç yok —
  Vega-Lite varsayılan olarak aynı alanı kodlayan katmanları TEK
  paylaşılan skalada birleştiriyor.

Fonksiyonun diğer katmanları (`noktalar_eksik` kırmızı üçgen, dikiş
çizgisi/metni) rengi `.encode()` içinde değil mark seviyesinde SABİT
(`color="#d62728"`, `color="#ff7f0e"`) veriyor — bunlar hiç skala/lejant
üretmiyor, `resolve_scale` çağrısına ihtiyaçları yok. Git geçmişi
kontrol edildi (`git log -S"resolve_scale"`): satır 2026-09-20'de
eklenmiş, HİÇ gerekçe yorumu yok, o zamandan beri değişmemiş — bilinçli
bir karar değil, muhtemelen alışkanlıktan eklenmiş gereksiz bir çağrı.

**Değişiklik:** `.resolve_scale(color="independent")` satırı kaldırıldı,
yerine gerekçeyi açıklayan bir yorum eklendi. `app/dashboard.py:656`.

## Kalite kapısı (yerelde, commit öncesi)

`pre-commit run --files app/dashboard.py .gitattributes` → **temiz**
(ruff, ruff-format, mypy, mixed-line-ending dahil tüm hook'lar Passed).

## Part 3 kanıtı: pre-commit hook'ları GERÇEKTEN engelliyor

Bu turda TAZELENDİ (önceki turda sözlü olarak doğrulanmıştı, bu kez
rapora da geçirildi): repoya iki geçici, kasıtlı bozuk dosya eklendi
(`_pc_proof_scratch.md` — başlık altında boş satır YOK;
`_pc_proof_scratch.py` — kullanılmayan `import os`), `git add` ile
staged edildi, gerçek bir `git commit` denendi:

```
exit=1
ruff (legacy alias)......................................................Failed
- hook id: ruff
- files were modified by this hook
Found 1 error (1 fixed, 0 remaining).

ruff format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook

prettier.................................................................Failed
- hook id: prettier
- files were modified by this hook
```

Commit **gerçekleşmedi** (exit 1) — hem ruff hem prettier hook'u
dosyaları otomatik düzeltti AMA bu yüzden commit'i durdurdu (pre-commit
kuralı: bir hook dosya değiştirirse o koşu "Failed" sayılır, değişiklik
yeniden stage edilip commit TEKRAR denenmelidir). Bu sırada staged
OLMAYAN gerçek değişikliklerim (`app/dashboard.py`, iki doküman)
pre-commit tarafından otomatik stash'lenip işlem sonunda hiçbir kayıp
olmadan geri getirildi (`[INFO] Stashing unstaged files...` /
`[INFO] Restored changes...`). Kanıt sonrası iki geçici dosya
`git reset` ile unstage edilip silindi — repoda hiçbir iz kalmadı.

## Bugünün altyapı işleri (tarih çapalı, `09_PROJE_DURUMU.md`'ye işlendi)

- **(2026-11-10) pre-commit yerelde çalışıyor** — Python 3.12.10
  (winget) + `pre-commit` 4.7.0, hem `pre-commit` hem `commit-msg` hook
  tipi kayıtlı. `09_PROJE_DURUMU.md` madde 10.
- **(2026-11-10) `.gitattributes`'a `eol=lf` eklendi** —
  `core.autocrlf=true` (sistem seviyesi, bu makineye özgü) ile
  `mixed-line-ending` hook'u arasındaki çelişki 167 dosyada tekrarlayan
  gürültüye yol açıyordu; çözüm repoya yazıldı (makineye değil).
  `09_PROJE_DURUMU.md` madde 12, commit `3b60f20`.
- **(2026-11-09/10) prettier local hook + stabil 3.9.10** — arşivlenmiş
  `mirrors-prettier` yerine `repo: local` ile doğrudan npm'den gerçek
  stabil sürüm. `09_PROJE_DURUMU.md` madde 13, commit `09ace8c`.
- **(2026-11-09) ruff sürümü sabit** — `requirements-dev.txt` artık
  `.pre-commit-config.yaml` ile birebir aynı (`==0.16.6`).
  `09_PROJE_DURUMU.md` madde 13, commit `0328938`.
- **(2026-11-09) Yedek cron günlük** — `0 3 * * *`, 24 saatlik
  tazelik kapısıyla artık uyumlu. `09_PROJE_DURUMU.md` madde 6 (zaten
  önceki turda çözülmüştü, değişmedi).

## Canlı erişim

Yok — tüm iş kod okuma + yerel kalite kapısı koşusuydu. Hiçbir DDL/DML
canlıya uygulanmadı.
