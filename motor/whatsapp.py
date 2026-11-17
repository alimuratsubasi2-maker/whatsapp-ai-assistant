"""Meta WhatsApp Cloud API: mesaj gönderme, medya indirme, webhook ayrıştırma."""
import hashlib
import hmac

import requests

from .ayarlar import WA_API_SURUM, WA_APP_SECRET, WA_TOKEN

GRAPH = f"https://graph.facebook.com/{WA_API_SURUM}"


def _token(sirket):
    # Her şirket kendi Meta hesabını bağlarsa kendi token'ı, yoksa ortak token
    return (sirket.get("whatsapp") or {}).get("token") or WA_TOKEN


def imza_dogru(govde: bytes, imza_basligi: str | None) -> bool:
    if not WA_APP_SECRET:
        return True
    if not imza_basligi or not imza_basligi.startswith("sha256="):
        return False
    beklenen = hmac.new(WA_APP_SECRET.encode(), govde, hashlib.sha256).hexdigest()
    return hmac.compare_digest(beklenen, imza_basligi[7:])


def metin_gonder(sirket, alici, metin) -> bool:
    pid = (sirket.get("whatsapp") or {}).get("phone_number_id")
    if not pid or not _token(sirket):
        print(f"[whatsapp] {sirket['id']} için numara/token yok, gönderilmedi")
        return False
    r = requests.post(f"{GRAPH}/{pid}/messages",
                      headers={"Authorization": f"Bearer {_token(sirket)}"},
                      json={"messaging_product": "whatsapp", "to": alici, "type": "text",
                            "text": {"body": metin[:4096], "preview_url": True}}, timeout=20)
    if r.status_code != 200:
        print(f"[whatsapp] gönderim hatası {r.status_code}: {r.text[:300]}")
    return r.status_code == 200


def okundu_yap(sirket, wa_mesaj_id):
    pid = (sirket.get("whatsapp") or {}).get("phone_number_id")
    if not pid:
        return
    try:
        requests.post(f"{GRAPH}/{pid}/messages", headers={"Authorization": f"Bearer {_token(sirket)}"},
                      json={"messaging_product": "whatsapp", "status": "read", "message_id": wa_mesaj_id},
                      timeout=10)
    except requests.RequestException:
        pass


def medya_indir(sirket, medya_id) -> tuple[bytes, str] | None:
    h = {"Authorization": f"Bearer {_token(sirket)}"}
    try:
        bilgi = requests.get(f"{GRAPH}/{medya_id}", headers=h, timeout=15).json()
        dosya = requests.get(bilgi["url"], headers=h, timeout=30)
        return dosya.content, bilgi.get("mime_type", "application/octet-stream")
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"[whatsapp] medya indirilemedi: {e}")
        return None


def webhook_mesajlari(govde: dict):
    """Webhook gövdesindeki gelen mesajları sadeleştirir.
    Döner: [{phone_number_id, musteri, ad, wa_id, tur, metin, medya_id}]"""
    sonuc = []
    for entry in govde.get("entry", []):
        for change in entry.get("changes", []):
            v = change.get("value", {})
            pid = v.get("metadata", {}).get("phone_number_id")
            adlar = {c.get("wa_id"): c.get("profile", {}).get("name") for c in v.get("contacts", [])}
            for m in v.get("messages", []):
                tur = m.get("type")
                kayit = {"phone_number_id": pid, "musteri": m.get("from"), "ad": adlar.get(m.get("from")),
                         "wa_id": m.get("id"), "tur": tur, "metin": "", "medya_id": None}
                if tur == "text":
                    kayit["metin"] = m["text"]["body"]
                elif tur in ("audio", "image", "video", "document", "sticker"):
                    kayit["medya_id"] = m[tur].get("id")
                    kayit["metin"] = m[tur].get("caption", "")
                elif tur == "location":
                    loc = m["location"]
                    kayit["metin"] = f"[konum gönderdi] {loc.get('name', '')} {loc.get('address', '')} ({loc.get('latitude')},{loc.get('longitude')})"
                elif tur == "button":
                    kayit["metin"] = m["button"].get("text", "")
                elif tur == "interactive":
                    i = m["interactive"]
                    kayit["metin"] = (i.get("button_reply") or i.get("list_reply") or {}).get("title", "")
                elif tur == "reaction":
                    continue  # emoji tepkilerine cevap verme
                else:
                    kayit["metin"] = f"[{tur} türünde mesaj]"
                sonuc.append(kayit)
    return sonuc
