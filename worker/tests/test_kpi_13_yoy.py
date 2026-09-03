"""EPP — worker/kpi.py:kpi_13_yoy() saf fonksiyon testleri.

DB gerektirmez — worker/analytics.py'nin `tuketim_getir()` ile DB'den
çekip bu fonksiyona geçireceği şekilde sentetik DataFrame'ler kurulur.

2026-09-03: kpi_13_yoy() KPI-25/26 ile AYNI "kapsam uyuşmuyorsa
hesaplama" disiplinini uygulayacak şekilde güncellendi (bkz. worker/
kpi.py modül notu — kanıt: 2025-06/2026-06 canlı karşılaştırması,
Sanayi'nin bir tarafta hiç olmaması %+70,9 gibi sahte bir YoY üretmişti,
Sanayi hariç tutulunca %+2,2 çıkıyordu). Bu dosya iki ana senaryoyu
kapsar: (a) grup kümesi aynıysa gerçekten hesaplanır, (b) farklıysa
None ('hesaplanamaz') döner.
"""

from __future__ import annotations

import pandas as pd

from worker import kpi


def _tuketim_df(satirlar: list[tuple[str, float]]) -> pd.DataFrame:
    """(grup, tuketim_mwh) çiftlerinden `tuketim_getir()` şeklinde bir
    DataFrame kurar (yalnız kpi_13_yoy'un kullandığı kolonlar)."""
    return pd.DataFrame(satirlar, columns=["grup", "tuketim_mwh"])


def test_kpi_13_yoy_ayni_grup_kumesi_hesaplanir() -> None:
    """İki dönemin grup kümesi BİREBİR aynıysa (Sanayi dahil ikisinde de)
    gerçek bir YoY hesaplanır — sahte 'hesaplanamaz' üretilmemeli."""
    simdi = _tuketim_df(
        [("Mesken", 120.0), ("Sanayi", 200.0), ("Tarımsal", 30.0)]
    )
    gecen_yil = _tuketim_df(
        [("Mesken", 100.0), ("Sanayi", 180.0), ("Tarımsal", 20.0)]
    )
    # simdi toplam=350, gecen_yil toplam=300 -> %+16.7
    assert kpi.kpi_13_yoy(simdi, gecen_yil) == 16.7


def test_kpi_13_yoy_sanayi_bir_tarafta_yok_hesaplanamaz() -> None:
    """2025-06/2026-06 canlı senaryosunun sentetik eşdeğeri: cari dönem
    Sanayi içeriyor, geçen yılın aynı dönemi içermiyor (Word kaynağının
    Karar 2 kısıtı) — grup kümesi uyuşmuyor, None dönmeli (KAPSAM
    UYUŞMAZLIĞI, gerçek bir düşüş/artış DEĞİL)."""
    simdi = _tuketim_df(
        [("Mesken", 120.0), ("Sanayi", 200.0), ("Tarımsal", 30.0)]
    )
    gecen_yil_sanayisiz = _tuketim_df([("Mesken", 100.0), ("Tarımsal", 20.0)])
    assert kpi.kpi_13_yoy(simdi, gecen_yil_sanayisiz) is None


def test_kpi_13_yoy_grup_kumesi_kismen_farkli_hesaplanamaz() -> None:
    """Sanayi'ye özgü olmayan, GENEL bir kapsam-farkı da (örn. bir dönemde
    Aydınlatma hiç yoksa) aynı şekilde None vermeli — kontrol yalnız
    Sanayi'ye özel sabit kodlanmamış, grup kümesi eşitliğine dayanıyor."""
    simdi = _tuketim_df([("Mesken", 100.0), ("Aydınlatma", 5.0)])
    gecen_yil = _tuketim_df([("Mesken", 90.0)])
    assert kpi.kpi_13_yoy(simdi, gecen_yil) is None


def test_kpi_13_yoy_gecen_yil_yok_hesaplanamaz() -> None:
    """Önceki davranış korunuyor: geçen yılın aynı dönemi hiç aktif
    değilse (None) 'hesaplanamaz'."""
    simdi = _tuketim_df([("Mesken", 100.0)])
    assert kpi.kpi_13_yoy(simdi, None) is None


def test_kpi_13_yoy_gecen_yil_bos_dataframe_hesaplanamaz() -> None:
    """Boş bir DataFrame (ör. o dönem hiç aktif satır yoksa) de None
    vermeli — `.empty` kontrolü `grup` kolonuna erişmeden önce çalışmalı."""
    simdi = _tuketim_df([("Mesken", 100.0)])
    gecen_yil_bos = pd.DataFrame(columns=["grup", "tuketim_mwh"])
    assert kpi.kpi_13_yoy(simdi, gecen_yil_bos) is None
