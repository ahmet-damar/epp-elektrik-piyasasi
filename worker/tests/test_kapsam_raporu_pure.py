"""EPP — `worker/scripts/kapsam_raporu.py` SAF (DB gerektirmeyen)
fonksiyon testleri (2026-09-17). DATABASE_URL şartı YOK — CI'nin
"worker" (unit) job'ında da çalışır. Asıl amaç: sahte/boş veriyle
eksik-ay ve kısmi-ay tespitinin doğru çalıştığını göstermek."""

from __future__ import annotations

from datetime import date

from worker.scripts import kapsam_raporu as kr


def test_ay_ekle_yil_devri() -> None:
    assert kr.ay_ekle(202412, 1) == 202501
    assert kr.ay_ekle(202501, -1) == 202412
    assert kr.ay_ekle(202401, 11) == 202412
    assert kr.ay_ekle(202401, 12) == 202501


def test_beklenen_aylik_takvim_tek_yil() -> None:
    assert kr.beklenen_aylik_takvim(202401, 202404) == [
        202401,
        202402,
        202403,
        202404,
    ]


def test_beklenen_aylik_takvim_yil_devri() -> None:
    assert kr.beklenen_aylik_takvim(202411, 202502) == [
        202411,
        202412,
        202501,
        202502,
    ]


def test_beklenen_aylik_takvim_ayni_ay() -> None:
    assert kr.beklenen_aylik_takvim(202401, 202401) == [202401]


def test_beklenen_aylik_takvim_min_max_ters_bos_doner() -> None:
    assert kr.beklenen_aylik_takvim(202405, 202401) == []


def test_eksik_aylari_bul_bos_veriyle_TUM_takvim_eksik() -> None:
    """Boş veriyle (hiç mevcut ay yok) her ay eksik çıkmalı — kullanıcı
    talimatının vurguladığı asıl senaryo."""
    eksik = kr.eksik_aylari_bul([], 202401, 202403)
    assert eksik == [202401, 202402, 202403]


def test_eksik_aylari_bul_ortadaki_ay_eksik() -> None:
    eksik = kr.eksik_aylari_bul([202401, 202403], 202401, 202403)
    assert eksik == [202402]


def test_eksik_aylari_bul_tam_veriyle_bos_doner() -> None:
    eksik = kr.eksik_aylari_bul([202401, 202402, 202403], 202401, 202403)
    assert eksik == []


def test_eksik_aylari_bul_yil_devrinde_dogru_calisir() -> None:
    eksik = kr.eksik_aylari_bul([202411, 202501], 202411, 202502)
    assert eksik == [202412, 202502]


def test_modal_kardinalite_bul_en_sik_degeri_secer() -> None:
    ay_kardinalite = {
        202401: {"il_kodu": 81},
        202402: {"il_kodu": 81},
        202403: {"il_kodu": 79},  # sapan
    }
    modal = kr.modal_kardinalite_bul(ay_kardinalite, ("il_kodu",))
    assert modal == {"il_kodu": 81}


def test_modal_kardinalite_bul_bos_veriyle_hesaplanamaz() -> None:
    modal = kr.modal_kardinalite_bul({}, ("il_kodu",))
    assert modal == {"il_kodu": None}


def test_kismi_aylari_bul_sapan_ayi_yakalar() -> None:
    ay_kardinalite = {
        202401: {"il_kodu": 81},
        202402: {"il_kodu": 79},
        202403: {"il_kodu": 81},
    }
    modal = {"il_kodu": 81}
    kismi = kr.kismi_aylari_bul(ay_kardinalite, modal)
    assert kismi == {202402: {"il_kodu": (79, 81)}}


def test_kismi_aylari_bul_hepsi_modal_ile_ayniysa_bos_doner() -> None:
    ay_kardinalite = {202401: {"il_kodu": 81}, 202402: {"il_kodu": 81}}
    modal = {"il_kodu": 81}
    assert kr.kismi_aylari_bul(ay_kardinalite, modal) == {}


def test_yil_basina_beklenen_ay_gecmis_yil_12() -> None:
    assert kr.yil_basina_beklenen_ay(2025, date(2026, 9, 17)) == 12


def test_yil_basina_beklenen_ay_gelecek_yil_0() -> None:
    assert kr.yil_basina_beklenen_ay(2027, date(2026, 9, 17)) == 0


def test_yil_basina_beklenen_ay_icinde_bulunulan_yil_bugune_kadar() -> None:
    assert kr.yil_basina_beklenen_ay(2026, date(2026, 9, 17)) == 9


def test_yillik_tamlik_hesapla_tam_yil() -> None:
    aktif = [202501 + i for i in range(12)]  # 202501..202512 (12 ardışık ay)
    sonuc = kr.yillik_tamlik_hesapla("fact_tuketim", aktif, date(2026, 9, 17))
    assert sonuc == [
        {
            "tablo": "fact_tuketim",
            "yil": 2025,
            "beklenen_ay": 12,
            "mevcut_aktif_ay": 12,
            "tam_mi": True,
        }
    ]


def test_yillik_tamlik_hesapla_eksik_yil_ve_aradaki_bos_yil_atlanmaz() -> None:
    """2025 ve 2027'de veri var ama 2026 hiç yok — aradaki yıl SESSİZCE
    atlanmamalı, mevcut_aktif_ay=0 ile satır üretilmeli."""
    aktif = [202501, 202502, 202701, 202702, 202703]
    sonuc = kr.yillik_tamlik_hesapla("fact_uretim", aktif, date(2028, 1, 1))
    yillar = {s["yil"]: s for s in sonuc}
    assert set(yillar) == {2025, 2026, 2027}
    assert yillar[2025]["mevcut_aktif_ay"] == 2
    assert yillar[2025]["tam_mi"] is False
    assert yillar[2026]["mevcut_aktif_ay"] == 0
    assert yillar[2026]["beklenen_ay"] == 12
    assert yillar[2026]["tam_mi"] is False
    assert yillar[2027]["mevcut_aktif_ay"] == 3
    assert yillar[2027]["beklenen_ay"] == 12


def test_yillik_tamlik_hesapla_bos_veriyle_bos_liste_doner() -> None:
    assert kr.yillik_tamlik_hesapla("fact_tuketim", [], date(2026, 9, 17)) == []


def test_yillik_tamlik_hesapla_yillik_kayitlar_haric_tutulur() -> None:
    """ay=0 (YYYY00, yıllık kayıt) aylık tamlık hesabına KARIŞMAMALI."""
    aktif = [202500, 202501, 202502]
    sonuc = kr.yillik_tamlik_hesapla("fact_tuketim", aktif, date(2026, 1, 1))
    assert len(sonuc) == 1
    assert sonuc[0]["yil"] == 2025
    assert sonuc[0]["mevcut_aktif_ay"] == 2


def test_tarih_id_okunabilir_aylik_ve_yillik() -> None:
    assert kr.tarih_id_okunabilir(202609) == "2026-09"
    assert kr.tarih_id_okunabilir(202500) == "2025 (yıllık)"


def test_tablo_adini_dogrula_bilinmeyen_tablo_reddedilir() -> None:
    import pytest

    with pytest.raises(ValueError, match="Beklenmeyen tablo adı"):
        kr._tablo_adini_dogrula("sahte_tablo_injection_denemesi")


def test_csv_satirlari_olustur_tum_tablolarin_yillik_tamligini_birlestirir() -> None:
    rapor = kr.KapsamRaporu(
        olusturulma_zamani_iso="2026-09-17T00:00:00+00:00",
        veri_kapsam_disi=[],
        tablolar=[
            kr.TabloRaporu(
                tanim=kr.TABLOLAR[0],
                min_tarih_id=202501,
                max_tarih_id=202502,
                yillik_tamlik=[
                    {
                        "tablo": "fact_tuketim",
                        "yil": 2025,
                        "beklenen_ay": 12,
                        "mevcut_aktif_ay": 2,
                        "tam_mi": False,
                    }
                ],
            ),
            kr.TabloRaporu(tanim=kr.TABLOLAR[1], min_tarih_id=None, max_tarih_id=None),
        ],
        bulgu_j_kontrolu={
            "tablo": "fact_uretim_il_geneli",
            "tarih_id": 202402,
            "bulundu": False,
        },
    )
    satirlar = kr.csv_satirlari_olustur(rapor)
    assert len(satirlar) == 1
    assert satirlar[0]["tablo"] == "fact_tuketim"


def test_markdown_olustur_bulgu_j_bulunamadi_uyarisi_gorunur() -> None:
    """Kullanıcı talimatı: 202402 bulunamazsa SESSİZCE geçilmemeli, açıkça
    işaretlenmeli."""
    rapor = kr.KapsamRaporu(
        olusturulma_zamani_iso="2026-09-17T00:00:00+00:00",
        veri_kapsam_disi=[],
        tablolar=[
            kr.TabloRaporu(tanim=t, min_tarih_id=None, max_tarih_id=None)
            for t in kr.TABLOLAR
        ],
        bulgu_j_kontrolu={
            "tablo": "fact_uretim_il_geneli",
            "tarih_id": 202402,
            "bulundu": False,
        },
    )
    metin = kr.markdown_olustur(rapor, "2026-09-17")
    assert "BEKLENEN KAYIT BULUNAMADI" in metin
    assert "hesaplanamaz" in metin  # min_tarih_id=None olan tablolar için


def test_markdown_olustur_bulgu_j_bulundu_onayi_gorunur() -> None:
    rapor = kr.KapsamRaporu(
        olusturulma_zamani_iso="2026-09-17T00:00:00+00:00",
        veri_kapsam_disi=[],
        tablolar=[
            kr.TabloRaporu(tanim=t, min_tarih_id=None, max_tarih_id=None)
            for t in kr.TABLOLAR
        ],
        bulgu_j_kontrolu={
            "tablo": "fact_uretim_il_geneli",
            "tarih_id": 202402,
            "bulundu": True,
        },
    )
    metin = kr.markdown_olustur(rapor, "2026-09-17")
    assert "Beklenen kayıt bulundu" in metin
    assert "BEKLENEN KAYIT BULUNAMADI" not in metin
