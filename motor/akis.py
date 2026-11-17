"""Mesaj akışı: gelen mesaj -> kaydet -> (bekle, birleştir) -> beyin -> gönder."""
import threading

from . import beyin, kvkk, whatsapp
from . import veritabani as db
from .ayarlar import BEKLEME_SN, PUBLIC_URL
from .sirketler import sirket as sirket_getir

_zamanlayicilar: dict[tuple, threading.Timer] = {}
_kilitler: dict[tuple, threading.Lock] = {}
_genel_kilit = threading.Lock()

MEDYA_ETIKET = {"audio": "sesli mesaj", "image": "fotoğraf", "video": "video", "document": "belge", "sticker": "çıkartma"}


def _kilit(anahtar):
    with _genel_kilit:
        return _kilitler.setdefault(anahtar, threading.Lock())


def _bilgilendirme_ekle(s, musteri, cevap, taban_url):
    """Müşterinin aldığı ilk cevaba KVKK/dijital asistan bilgilendirmesi eklenir."""
    if db.bot_mesaj_sayisi(s["id"], musteri) == 0:
        return f"{cevap}\n\n{kvkk.ilk_bilgilendirme(s, taban_url)}"
    return cevap


def demo_mesaj(sirket_id, musteri, metin, ad=None, taban_url=None) -> str | None:
    """Web demo ekranı için: anında (beklemeden) cevap döner."""
    s = sirket_getir(sirket_id)
    if not s:
        raise KeyError(sirket_id)
    with _kilit((sirket_id, musteri)):
        db.mesaj_ekle(sirket_id, musteri, "musteri", kvkk.hassas_maskele(metin), kanal="demo", ad=ad)
        if (db.sohbet(sirket_id, musteri) or {}).get("insan_modu"):
            return None  # yetkili devraldı, bot susar
        cevap = _bilgilendirme_ekle(s, musteri, beyin.yanitla(s, musteri, taban_url), taban_url)
        db.mesaj_ekle(sirket_id, musteri, "bot", cevap)
        return cevap


def whatsapp_mesaj(sirket, kayit):
    """Webhook'tan gelen tek mesaj. Kısa süre bekler; müşteri yazmaya devam ederse birleştirir."""
    sid, musteri = sirket["id"], kayit["musteri"]
    whatsapp.okundu_yap(sirket, kayit["wa_id"])

    metin = kayit["metin"]
    if kayit.get("medya_id"):
        etiket = MEDYA_ETIKET.get(kayit["tur"], kayit["tur"])
        cozum = ""
        if kayit["tur"] in ("audio", "image"):
            indirilen = whatsapp.medya_indir(sirket, kayit["medya_id"])
            if indirilen:
                cozum = beyin.medya_metne(indirilen[0], indirilen[1], "ses" if kayit["tur"] == "audio" else "gorsel")
        metin = f"[{etiket}] {cozum or '(içerik okunamadı)'}" + (f" — açıklama: {kayit['metin']}" if kayit["metin"] else "")

    db.mesaj_ekle(sid, musteri, "musteri", kvkk.hassas_maskele(metin), kanal="whatsapp", ad=kayit.get("ad"))

    anahtar = (sid, musteri)
    with _genel_kilit:
        eski = _zamanlayicilar.pop(anahtar, None)
        if eski:
            eski.cancel()
        t = threading.Timer(BEKLEME_SN, _cevapla, args=(sid, musteri))
        t.daemon = True
        _zamanlayicilar[anahtar] = t
        t.start()


def _cevapla(sid, musteri):
    with _genel_kilit:
        _zamanlayicilar.pop((sid, musteri), None)
    s = sirket_getir(sid)  # panelden değişmiş olabilir, taze oku
    with _kilit((sid, musteri)):
        if (db.sohbet(sid, musteri) or {}).get("insan_modu"):
            return
        cevap = _bilgilendirme_ekle(s, musteri, beyin.yanitla(s, musteri, PUBLIC_URL), PUBLIC_URL)
        db.mesaj_ekle(sid, musteri, "bot", cevap)
        whatsapp.metin_gonder(s, musteri, cevap)


def yetkili_mesaji(sirket_id, musteri, metin):
    """Panelden işletme sahibinin elle yazdığı mesaj."""
    s = sirket_getir(sirket_id)
    db.mesaj_ekle(sirket_id, musteri, "yetkili", metin)
    kanal = (db.sohbet(sirket_id, musteri) or {}).get("kanal")
    if kanal == "whatsapp":
        return whatsapp.metin_gonder(s, musteri, metin)
    return True  # demo kanalında ekran zaten yokluyor
