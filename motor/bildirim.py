"""İşletme sahibine Telegram bildirimi (yeni randevu, iptal, yetkili çağrısı)."""
import threading

import requests

from .ayarlar import TELEGRAM_BOT_TOKEN

BASLIK = {"yeni": "🗓 Yeni randevu", "iptal": "❌ Randevu iptal edildi", "degisti": "🔁 Randevu değiştirildi"}


def _gonder(chat_id, metin):
    if not (TELEGRAM_BOT_TOKEN and chat_id):
        print(f"[bildirim] (Telegram ayarlı değil) {metin}")
        return

    def _is():
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                          json={"chat_id": chat_id, "text": metin}, timeout=15)
        except requests.RequestException as e:
            print(f"[bildirim] Telegram hatası: {e}")
    threading.Thread(target=_is, daemon=True).start()


def _chat(sirket):
    return (sirket.get("yetkili") or {}).get("telegram_chat_id")


def randevu_bildir(sirket, r, tur):
    metin = (f"{BASLIK.get(tur, 'Randevu')} — {sirket['ad']}\n"
             f"#{r['id']} {r['baslangic']}\n{r['hizmet']}\n👤 {r['ad']} ({r['musteri']})")
    if r.get("kisi_sayisi", 1) and int(r["kisi_sayisi"]) > 1:
        metin += f"\nKişi: {r['kisi_sayisi']}"
    if r.get("notlar"):
        metin += f"\n📝 {r['notlar']}"
    _gonder(_chat(sirket), metin)


def yetkili_cagir(sirket, musteri, sebep, ozet):
    _gonder(_chat(sirket), f"🙋 Yetkili bekleniyor — {sirket['ad']}\nMüşteri: {musteri}\n"
                           f"Sebep: {sebep}\n{ozet}\n\nPanelden sohbete girip cevap verebilirsin.")
