# ADR-7 — Sunum Katmanı: Streamlit (Faz 2), Next.js Ertelendi

**Tarih:** 2026-08-30 · **Durum:** Kabul edildi

## Bağlam
dokumanlar/01_kavramsal_tasarim.md §3 (Mimari), sunum katmanını
"Next.js + TypeScript (app/)" olarak tanımlıyordu. Ancak proje halihazırda
çalışan bir `app/dashboard.py` (Streamlit) ile ilerliyordu ve Faz 2
(Dashboard) kapsamı netleştirilirken bilinçli olarak Next.js'e GEÇİLMEDİ,
mevcut Streamlit paneli büyütüldü. Bu ADR, dokümanla gerçek durum
arasındaki bu farkı ve gerekçesini kayıt altına alır.

## Karar
Faz 2'de sunum katmanı **Streamlit** (`app/dashboard.py`) olarak kalır ve
gerçek `worker/analytics.py` sorgularıyla büyütülür. **Next.js + TypeScript'e
geçiş iptal edilmedi** — `dokumanlar/01_kavramsal_tasarim.md` §7'deki
**"Son Faz" (LinkedIn yayını)** öncesine bilinçli olarak ertelendi.

## Gerekçe
- **Hız:** Faz 0/1'de kurulan worker/ katmanı (parser, kpi, ingest, pipeline,
  job_worker) zaten Python. Streamlit aynı süreçte, ek bir API katmanı
  (FastAPI + REST/GraphQL sözleşmesi) veya ayrı bir frontend build zinciri
  kurmadan `worker/*.py` fonksiyonlarını doğrudan çağırabiliyor — Next.js
  bu ayrımı zorunlu kılardı (worker Python, sunum TypeScript; aralarında
  bir API katmanı gerekir).
- **Kapsam eşleşmesi:** Faz 2'nin hedefi "Dashboard (KPI görselleştirme)" —
  çok kullanıcılı, marka kimlikli bir web uygulaması değil, veri
  ekibinin/paydaşların KPI'ları görebileceği tek bir iç panel. Streamlit
  bunun için yeterli ve fazla mühendisliksiz.
- **Erteleme, iptal değil:** Next.js'in asıl gerekçesi (marka kimlikli,
  SEO'lu, halka açık bir dashboard) yalnız **"Son Faz"** (LinkedIn yayını,
  §7) civarında gerçekten gerekli olur — o zamana kadar erteleme, gereksiz
  erken yatırımdan kaçınır.

## Sonuçlar
- `app/dashboard.py` büyümeye devam eder; DB bağlıysa `worker/analytics.py`
  üzerinden gerçek sorgu, yoksa `data/tr_ocak2026.py` statik yedek.
- `worker/` katmanı framework-agnostik kalmalı (Streamlit'e bağımlı kod
  yalnız `app/` içinde) — ileride Next.js'e geçilirse `worker/*.py`
  (parser/kpi/ingest/pipeline/analytics) DEĞİŞMEDEN bir FastAPI katmanının
  arkasına konabilir.
- **RLS notu:** `worker/analytics.py`, `DATABASE_URL` üzerinden doğrudan
  psycopg ile bağlanır — bu genelde RLS'ten muaf bir rol demektir
  (service_role/postgres, bkz. `supabase/migrations/20260819_0002_rls_roles.sql`).
  Faz 2 tek-kullanıcılı geliştirme/iç panel kapsamında bu kabul edilebilir;
  **çok kullanıcılı erişime geçildiğinde** (kullanıcı bazlı auth, dışa açık
  dashboard) `analytics.py`'nin doğrudan `DATABASE_URL` yerine bir Supabase
  `authenticated` istemcisine (kullanıcının oturumuna bağlı, RLS politikaları
  uygulanan) geçmesi gerekir — bu, bu ADR'nin ve Faz 2'nin kapsamı DIŞINDA
  bırakılmıştır, ileride sürpriz olmaması için burada not edilir.

## Değerlendirilen Alternatifler
- **Next.js + TypeScript (şimdi):** Reddedildi — Faz 2 kapsamına göre erken;
  worker/ ile arasına bir API katmanı (FastAPI) kurmayı da gerektirirdi,
  bu da ayrı bir ADR/iş kalemi olurdu.
- **FastAPI + basit HTML/Jinja:** Değerlendirilmedi — Streamlit zaten
  çalışıyordu ve pandas/DataFrame tabanlı KPI gösterimine Jinja'dan daha
  uygun.
