"""Randevu takvimi: müsait saat hesabı, oluşturma, iptal, değiştirme.

Her şirketin `randevu` ayarı:
  slot_dk            -> saatler kaçar dakika arayla önerilsin (örn. 30)
  kapasite           -> aynı anda kaç randevu alınabilir (koltuk / masa / usta sayısı)
  varsayilan_sure_dk -> hizmette süre yazmıyorsa
  en_az_kac_saat_once, kac_gun_ileri
"""
from datetime import datetime, timedelta

from . import veritabani as db
from .ayarlar import GUN_ADLARI, GUNLER, simdi

BICIM = "%Y-%m-%d %H:%M"


def _ayar(sirket):
    r = {"aktif": True, "slot_dk": 30, "kapasite": 1, "varsayilan_sure_dk": 30,
         "en_az_kac_saat_once": 1, "kac_gun_ileri": 30}
    r.update(sirket.get("randevu") or {})
    return r


def _araliklar(sirket, tarih: datetime):
    """O günün çalışma aralıkları [(bas, bit), ...]; kapalıysa boş liste."""
    if tarih.strftime("%Y-%m-%d") in (sirket.get("tatil_gunleri") or []):
        return []
    metin = (sirket.get("calisma_saatleri") or {}).get(GUNLER[tarih.weekday()])
    if not metin:
        return []
    sonuc = []
    for parca in str(metin).split(","):
        bas, bit = [p.strip() for p in parca.split("-")]
        g = tarih.strftime("%Y-%m-%d")
        sonuc.append((datetime.strptime(f"{g} {bas}", BICIM), datetime.strptime(f"{g} {bit}", BICIM)))
    return sonuc


def hizmet_bul(sirket, hizmet_adi):
    if not hizmet_adi:
        return None
    a = hizmet_adi.lower().strip()
    hizmetler = sirket.get("hizmetler") or []
    for h in hizmetler:
        if h["ad"].lower() == a:
            return h
    for h in hizmetler:
        if a in h["ad"].lower() or h["ad"].lower() in a:
            return h
    return None


def _sure(sirket, hizmet_adi):
    h = hizmet_bul(sirket, hizmet_adi)
    return int((h or {}).get("sure_dk") or _ayar(sirket)["varsayilan_sure_dk"])


def _doluluk(sirket, bas, bit, haric_id=None):
    """[bas, bit) aralığıyla çakışan randevuların toplam kişi/birim sayısı yerine adedi."""
    adet = 0
    for r in db.gunun_randevulari(sirket["id"], bas.strftime("%Y-%m-%d")):
        if r["id"] == haric_id:
            continue
        rb, rbit = datetime.strptime(r["baslangic"], BICIM), datetime.strptime(r["bitis"], BICIM)
        if rb < bit and bas < rbit:
            adet += 1
    return adet


def _uygun_mu(sirket, bas, sure_dk, haric_id=None):
    ayar = _ayar(sirket)
    bit = bas + timedelta(minutes=sure_dk)
    if bas < simdi() + timedelta(hours=float(ayar["en_az_kac_saat_once"])):
        return False, "Bu saat çok yakın ya da geçmiş."
    if bas.date() > (simdi() + timedelta(days=int(ayar["kac_gun_ileri"]))).date():
        return False, f"En fazla {ayar['kac_gun_ileri']} gün ileriye randevu alınabiliyor."
    araliklar = _araliklar(sirket, bas)
    if not araliklar:
        return False, f"{GUN_ADLARI[bas.weekday()]} günü kapalıyız."
    if not any(a <= bas and bit <= b for a, b in araliklar):
        return False, "Bu saat çalışma saatlerimizin dışında (ya da hizmet kapanışa sığmıyor)."
    if _doluluk(sirket, bas, bit, haric_id) >= int(ayar["kapasite"]):
        return False, "Bu saat dolu."
    return True, ""


def musait_saatler(sirket, tarih_str, hizmet_adi=None):
    ayar = _ayar(sirket)
    try:
        gun = datetime.strptime(tarih_str, "%Y-%m-%d")
    except (TypeError, ValueError):
        return {"hata": "Tarih YYYY-AA-GG biçiminde olmalı."}
    sure = _sure(sirket, hizmet_adi)
    araliklar = _araliklar(sirket, gun)
    if not araliklar:
        return {"tarih": tarih_str, "gun": GUN_ADLARI[gun.weekday()], "durum": "kapalı", "saatler": []}
    saatler = []
    for a, b in araliklar:
        t = a
        while t + timedelta(minutes=sure) <= b:
            if _uygun_mu(sirket, t, sure)[0]:
                saatler.append(t.strftime("%H:%M"))
            t += timedelta(minutes=int(ayar["slot_dk"]))
    return {"tarih": tarih_str, "gun": GUN_ADLARI[gun.weekday()], "hizmet_suresi_dk": sure,
            "saatler": saatler, "durum": "açık" if saatler else "boş yer yok"}


def randevu_olustur(sirket, musteri, tarih, saat, hizmet, ad, kisi_sayisi=1, notlar=""):
    if not _ayar(sirket)["aktif"]:
        return {"hata": "Bu işletme WhatsApp üzerinden randevu almıyor."}
    try:
        bas = datetime.strptime(f"{tarih} {saat}", BICIM)
    except (TypeError, ValueError):
        return {"hata": "Tarih YYYY-AA-GG, saat SS:DD biçiminde olmalı."}
    if not ad:
        return {"hata": "Randevu için müşterinin adı gerekli."}
    sure = _sure(sirket, hizmet)
    tamam, sebep = _uygun_mu(sirket, bas, sure)
    if not tamam:
        alternatif = musait_saatler(sirket, tarih, hizmet).get("saatler", [])[:8]
        return {"hata": sebep, "ayni_gun_bos_saatler": alternatif}
    bit = bas + timedelta(minutes=sure)
    rid = db.randevu_ekle(sirket["id"], musteri, ad, hizmet or "", bas.strftime(BICIM),
                          bit.strftime(BICIM), int(kisi_sayisi or 1), notlar or "")
    db.ad_kaydet(sirket["id"], musteri, ad)
    return {"basarili": True, "randevu": db.randevu(rid),
            "gun": GUN_ADLARI[bas.weekday()]}


def _musterinin_mi(sirket, musteri, rid):
    r = db.randevu(int(rid)) if str(rid).isdigit() else None
    if not r or r["sirket_id"] != sirket["id"] or r["musteri"] != musteri or r["durum"] != "onayli":
        return None
    return r


def randevu_iptal(sirket, musteri, rid):
    r = _musterinin_mi(sirket, musteri, rid)
    if not r:
        return {"hata": "Bu numaraya ait böyle aktif bir randevu bulunamadı."}
    db.randevu_iptal(r["id"])
    return {"basarili": True, "iptal_edilen": r}


def randevu_degistir(sirket, musteri, rid, tarih, saat):
    r = _musterinin_mi(sirket, musteri, rid)
    if not r:
        return {"hata": "Bu numaraya ait böyle aktif bir randevu bulunamadı."}
    try:
        bas = datetime.strptime(f"{tarih} {saat}", BICIM)
    except (TypeError, ValueError):
        return {"hata": "Tarih YYYY-AA-GG, saat SS:DD biçiminde olmalı."}
    sure = _sure(sirket, r["hizmet"])
    tamam, sebep = _uygun_mu(sirket, bas, sure, haric_id=r["id"])
    if not tamam:
        return {"hata": sebep, "ayni_gun_bos_saatler": musait_saatler(sirket, tarih, r["hizmet"]).get("saatler", [])[:8]}
    db.randevu_iptal(r["id"])
    yeni = db.randevu_ekle(sirket["id"], musteri, r["ad"], r["hizmet"], bas.strftime(BICIM),
                           (bas + timedelta(minutes=sure)).strftime(BICIM), r["kisi_sayisi"], r["notlar"])
    return {"basarili": True, "eski": r, "yeni": db.randevu(yeni), "gun": GUN_ADLARI[bas.weekday()]}
