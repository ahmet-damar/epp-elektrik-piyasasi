"""EPP — Faz 1 asenkron worker: job_status kuyruğunu poll'lar, worker/pipeline.py
epdk_isi_kuyruga_al() tarafından oluşturulan işleri işler.

Kaynak: dokumanlar/01_kavramsal_tasarim.md §4, worker/pipeline.py ve
worker/ingest.py modül notları. Harici broker YOK (Redis/Celery/RabbitMQ) —
salt Postgres polling (ingest.is_sahiplen/is_basarili/is_basarisiz), ADR-6'nın
"self-host edilebilir, minimum dış bağımlılık" çizgisiyle tutarlı.

Kullanım:
    python worker/job_worker.py              # kuyrukta ne varsa işler, çıkar (--once, varsayılan; cron/Task Scheduler dostu)
    python worker/job_worker.py --loop        # sürekli poll (Ctrl+C ile durdurulur)
    python worker/job_worker.py --loop --interval 60

Otomatik aktivasyon eşiği (kullanıcı kararı, 2026-08-30): epdk_isi_kuyruga_al()
ile kuyruğa alınan bir iş başarıyla parse+yüklendiğinde, pipeline.
otomatik_onaya_uygun() TUTuyorsa (tüm mutabakat sonuçları False değil VE
hiçbir tabloda red/karantina yok) worker batch_onayla()'yı OTOMATİK çağırır.
Tutmazsa batch 'running'de bırakılır, net bir uyarı basılır (batch_id + hangi
koşulun tutmadığı) — elle batch_onayla() çağrılması beklenir (Faz 0'daki gibi).
Amaç: temiz geçen aylar otomatik aksın, şüpheli olanlar insan gözünden kaçmasın.

Hata durumunda (parse hatası, eksik tablo, DB hatası) is_basarisiz() ile
job_status 'retrying' (üstel geri çekilme) ya da _MAX_DENEME aşılınca
'dead_letter' olur; ingestion_batch.status aynı karara göre senkronize edilir
(job_status'ta hata metni SAKLANMAZ, ingestion_batch.error_summary'ye yazılır).
"""

from __future__ import annotations

import argparse
import os
import socket
import time
from pathlib import Path
from typing import TYPE_CHECKING

import psycopg

from worker import ingest, pipeline

if TYPE_CHECKING:
    from psycopg import Connection

    from worker.ingest import IsKaydi


def _worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _batch_bilgisi_getir(conn: Connection, batch_id: int) -> tuple[str, str, str]:
    """(storage_path, source_period, donem_tipi) döner; batch/source_asset
    bulunamazsa veya storage_path boşsa RuntimeError fırlatır (kalıcı hata —
    is_basarisiz() bunu retry/dead_letter akışına sokar)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sa.storage_path, sa.source_period, sa.donem_tipi
            FROM ingestion_batch b
            JOIN source_asset sa ON sa.source_asset_id = b.source_asset_id
            WHERE b.batch_id = %s
            """,
            (batch_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"batch_id={batch_id} (veya source_asset'i) bulunamadı")
    storage_path, source_period, donem_tipi = row
    if not storage_path:
        raise RuntimeError(f"source_asset.storage_path boş (batch_id={batch_id})")
    return storage_path, source_period, donem_tipi


def _isi_uygula(conn: Connection, job: IsKaydi) -> None:
    """Bir job_status kaydının asıl işi: dosyayı oku, _isle_govde() çağır,
    eksik tablo varsa hata fırlat (kalıcı - retry/dead_letter akışına girer),
    otomatik onay eşiğini değerlendir. Hata fırlatırsa çağıran (_bir_is_isle)
    rollback edip is_basarisiz()'i tetikler."""
    batch_id = int(job.correlation_id)
    storage_path, source_period, donem_tipi = _batch_bilgisi_getir(conn, batch_id)
    icerik = Path(storage_path).read_bytes()
    tarih_id = ingest.tarih_id_from_source_period(source_period, donem_tipi)

    ingest.batch_sahiplen(conn, batch_id)  # defense-in-depth; batch zaten 'queued'
    sonuc = pipeline._isle_govde(
        conn, batch_id, icerik, tarih_id, actor_name="system:job_worker"
    )

    if sonuc.eksik_tablolar:
        raise RuntimeError(f"eksik tablo(lar): {', '.join(sonuc.eksik_tablolar)}")

    uygun, sebep = pipeline.otomatik_onaya_uygun(sonuc)
    if uygun:
        pipeline.batch_onayla(
            conn, sonuc.batch_id, actor_name="system:job_worker-otomatik"
        )
        print(f"[OK] batch_id={batch_id} otomatik aktive edildi")
    else:
        print(
            f"[UYARI] batch_id={batch_id} OTOMATİK AKTİVE EDİLMEDİ ({sebep}) "
            "— elle batch_onayla() bekleniyor"
        )


def _bir_is_isle(conn: Connection, worker_id: str) -> bool:
    """Kuyruktan bir iş sahiplenip işler. İş yoksa False; işlendiyse
    (başarılı/başarısız fark etmez) True döner — --loop modunda "iş var mı"
    sinyali olarak kullanılır."""
    job = ingest.is_sahiplen(conn, worker_id)
    if job is None:
        return False
    # Sahiplenme kalıcı olsun: worker bundan sonra çökerse job 'running' kalır,
    # is_sahiplen()'in bayat-heartbeat kurtarması sonraki bir poll'da onu geri alır.
    conn.commit()

    try:
        _isi_uygula(conn, job)
        conn.commit()
        ingest.is_basarili(conn, job.job_id)
        conn.commit()
    except Exception as e:  # noqa: BLE001 - herhangi bir hata retry/dead_letter akışına girmeli
        conn.rollback()
        durum = ingest.is_basarisiz(conn, job)
        ingest.batch_durumu_guncelle(
            conn,
            int(job.correlation_id),
            "failed" if durum == "dead_letter" else "retrying",
            error_summary=str(e),
        )
        conn.commit()
        print(
            f"[HATA] job_id={job.job_id} correlation_id={job.correlation_id} ({durum}): {e}"
        )
    return True


def calistir_once(conn: Connection, worker_id: str) -> int:
    """Kuyrukta iş kalmayana kadar işler (drain), işlenen iş sayısını döner."""
    islenen = 0
    while _bir_is_isle(conn, worker_id):
        islenen += 1
    return islenen


def calistir_loop(conn: Connection, worker_id: str, interval: int) -> None:
    print(
        f"[job_worker] {worker_id} başladı, {interval}s aralıkla poll ediyor (Ctrl+C ile durdur)"
    )
    while True:
        if not _bir_is_isle(conn, worker_id):
            time.sleep(interval)


def main() -> None:
    ap = argparse.ArgumentParser(description="EPP Faz 1 asenkron worker")
    ap.add_argument(
        "--loop",
        action="store_true",
        help="sürekli poll (varsayılan: --once, kuyruğu boşalt ve çık)",
    )
    ap.add_argument(
        "--interval",
        type=int,
        default=30,
        help="--loop modunda boş kuyrukta bekleme süresi (saniye, varsayılan 30)",
    )
    args = ap.parse_args()

    database_url = os.environ["DATABASE_URL"]
    worker_id = _worker_id()
    with psycopg.connect(database_url) as conn:
        if args.loop:
            calistir_loop(conn, worker_id, args.interval)
        else:
            n = calistir_once(conn, worker_id)
            print(f"[job_worker] {n} iş işlendi, kuyruk boş, çıkılıyor.")


if __name__ == "__main__":
    main()
