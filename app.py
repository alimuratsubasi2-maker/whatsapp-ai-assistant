"""NovaDijitalTR WhatsApp Otomasyonu — web sunucusu.

  /                    demo şirket listesi
  /demo/<sirket_id>    WhatsApp görünümlü test ekranı (müşteriye canlı sunum)
  /panel               işletme yönetim paneli (sohbetler, randevular, bilgiler)
  /webhook             Meta WhatsApp Cloud API webhook adresi
"""
import json
import threading
import time
from functools import wraps

from flask import Flask, abort, jsonify, request, send_from_directory

from motor import akis, kvkk, whatsapp
from motor import veritabani as db
from motor.ayarlar import (GEMINI_UCRETLI, KOK, PANEL_SIFRE, PORT, WA_APP_SECRET,
                           WA_VERIFY_TOKEN, simdi)
from motor.sirketler import (demo_sirketleri_hazirla, numaradan_sirket, sektorler,
                             sektor_sablonundan_sirket, sirket, sirket_kaydet, tum_sirketler)

WEB = KOK / "web"
app = Flask(__name__)
demo_sirketleri_hazirla()
kvkk.saklama_temizligini_baslat()


def _ozet(s):
    return {"id": s["id"], "ad": s["ad"], "sektor": s.get("sektor"), "asistan_adi": s.get("asistan_adi"),
            "demo": bool(s.get("demo")), "whatsapp_bagli": bool((s.get("whatsapp") or {}).get("phone_number_id"))}


# ---------------- sayfalar ----------------

@app.get("/")
def ana_sayfa():
    return send_from_directory(WEB, "index.html")


@app.get("/demo/<sid>")
def demo_sayfa(sid):
    if not sirket(sid):
        abort(404)
    return send_from_directory(WEB, "demo.html")


@app.get("/panel")
def panel_sayfa():
    return send_from_directory(WEB, "panel.html")


@app.get("/api/sirketler")
def api_sirketler():
    return jsonify([_ozet(s) for s in tum_sirketler()])


# ---------------- demo sohbet ----------------
# Demo uçları herkese açıktır: SADECE "demo-" ile başlayan sohbetlere dokunabilir.
# (Gerçek WhatsApp sohbetleri telefon numarasıyla tutulur; buradan asla okunamaz/silinemez.)

DEMO_ONEK = "demo-"
_demo_sayac: dict[str, list[float]] = {}
DEMO_LIMIT, DEMO_PENCERE_SN = 40, 600  # IP başına 10 dakikada 40 mesaj


def _demo_musteri(deger) -> str:
    m = str(deger or "")[:40]
    if not m.startswith(DEMO_ONEK) or not all(c.isalnum() or c == "-" for c in m):
        abort(400)
    return m


def _demo_sinir_asildi() -> bool:
    ip = request.headers.get("CF-Connecting-IP") or request.remote_addr or "?"
    simdi_sn = time.time()
    liste = [t for t in _demo_sayac.get(ip, []) if simdi_sn - t < DEMO_PENCERE_SN]
    liste.append(simdi_sn)
    _demo_sayac[ip] = liste
    return len(liste) > DEMO_LIMIT


@app.get("/api/demo/<sid>")
def api_demo_bilgi(sid):
    s = sirket(sid) or abort(404)
    return jsonify(_ozet(s))


@app.post("/api/demo/<sid>/mesaj")
def api_demo_mesaj(sid):
    veri = request.get_json(force=True)
    musteri = _demo_musteri(veri.get("musteri"))
    metin = str(veri.get("metin") or "").strip()[:2000]
    if not metin:
        return jsonify({"hata": "boş mesaj"}), 400
    if _demo_sinir_asildi():
        return jsonify({"cevap": "Demo için kısa sürede çok fazla mesaj gönderildi, lütfen birkaç dakika sonra tekrar deneyin."})
    try:
        cevap = akis.demo_mesaj(sid, musteri, metin, taban_url=request.host_url)
    except KeyError:
        abort(404)
    return jsonify({"cevap": cevap})


@app.get("/api/demo/<sid>/mesajlar")
def api_demo_mesajlar(sid):
    musteri = _demo_musteri(request.args.get("musteri"))
    son = int(request.args.get("son", 0))
    return jsonify([m for m in db.mesajlar_sonra(sid, musteri, son) if m["rol"] != "sistem"])


@app.post("/api/demo/<sid>/sifirla")
def api_demo_sifirla(sid):
    musteri = _demo_musteri(request.get_json(force=True).get("musteri"))
    db.musteri_verilerini_sil(sid, musteri)
    return jsonify({"tamam": True})


# ---------------- KVKK aydınlatma metni ----------------

@app.get("/kvkk/<sid>")
def kvkk_sayfa(sid):
    s = sirket(sid) or abort(404)
    return kvkk.aydinlatma_html(s), 200, {"Content-Type": "text/html; charset=utf-8"}


# ---------------- panel ----------------

def panel_yetki(f):
    @wraps(f)
    def sarici(*a, **k):
        if request.headers.get("X-Panel-Sifre") != PANEL_SIFRE:
            return jsonify({"hata": "yetkisiz"}), 401
        return f(*a, **k)
    return sarici


@app.get("/api/panel/giris")
@panel_yetki
def api_giris():
    return jsonify({"tamam": True})


@app.get("/api/panel/<sid>/sohbetler")
@panel_yetki
def api_sohbetler(sid):
    return jsonify(db.sohbetler(sid))


@app.get("/api/panel/<sid>/sohbet/<musteri>")
@panel_yetki
def api_sohbet(sid, musteri):
    return jsonify({"sohbet": db.sohbet(sid, musteri), "mesajlar": db.son_mesajlar(sid, musteri, 300)})


@app.post("/api/panel/<sid>/sohbet/<musteri>/gonder")
@panel_yetki
def api_yetkili_gonder(sid, musteri):
    metin = (request.get_json(force=True).get("metin") or "").strip()
    if not metin:
        return jsonify({"hata": "boş"}), 400
    return jsonify({"gonderildi": akis.yetkili_mesaji(sid, musteri, metin)})


@app.post("/api/panel/<sid>/sohbet/<musteri>/insan_modu")
@panel_yetki
def api_insan_modu(sid, musteri):
    db.insan_modu_ayarla(sid, musteri, bool(request.get_json(force=True).get("acik")))
    return jsonify({"tamam": True})


@app.post("/api/panel/<sid>/sohbet/<musteri>/sil")
@panel_yetki
def api_musteri_sil(sid, musteri):
    """KVKK m.7/m.11 silme talebi: müşterinin tüm mesaj ve randevu kayıtlarını kalıcı siler."""
    db.musteri_verilerini_sil(sid, musteri)
    return jsonify({"tamam": True})


@app.get("/api/panel/<sid>/randevular")
@panel_yetki
def api_randevular(sid):
    tumu = request.args.get("tumu") == "1"
    return jsonify(db.randevular(sid, None if tumu else simdi().strftime("%Y-%m-%d")))


@app.post("/api/panel/<sid>/randevu/<int:rid>/iptal")
@panel_yetki
def api_randevu_iptal(sid, rid):
    r = db.randevu(rid)
    if not r or r["sirket_id"] != sid:
        abort(404)
    db.randevu_iptal(rid)
    return jsonify({"tamam": True})


@app.get("/api/panel/<sid>/ayarlar")
@panel_yetki
def api_ayar_oku(sid):
    return jsonify(sirket(sid) or abort(404))


@app.post("/api/panel/<sid>/ayarlar")
@panel_yetki
def api_ayar_yaz(sid):
    veri = request.get_json(force=True)
    if veri.get("id") != sid:
        return jsonify({"hata": "id değiştirilemez"}), 400
    sirket_kaydet(veri)
    return jsonify({"tamam": True})


@app.get("/api/panel/sektorler")
@panel_yetki
def api_sektorler():
    return jsonify({k: v["ad"] for k, v in sektorler().items()})


@app.post("/api/panel/yeni_sirket")
@panel_yetki
def api_yeni_sirket():
    veri = request.get_json(force=True)
    sid = "".join(c for c in (veri.get("id") or "").lower() if c.isalnum() or c == "-")
    if not sid or sirket(sid):
        return jsonify({"hata": "id boş ya da zaten var"}), 400
    paket = sektorler().get(veri.get("sektor"), {})
    if "ornek_sirket" in paket:
        s = sektor_sablonundan_sirket(veri["sektor"], sid, veri.get("ad"))
    else:
        s = {"id": sid, "ad": veri.get("ad") or sid, "sektor": veri.get("sektor") or "genel",
             "asistan_adi": "Asistan", "calisma_saatleri": {}, "hizmetler": [], "sss": [],
             "randevu": {"aktif": True}, "yetkili": {}, "whatsapp": {"phone_number_id": ""}}
        sirket_kaydet(s)
    return jsonify(s)


# ---------------- WhatsApp webhook ----------------

@app.get("/webhook")
def webhook_dogrula():
    if (request.args.get("hub.mode") == "subscribe"
            and request.args.get("hub.verify_token") == WA_VERIFY_TOKEN):
        return request.args.get("hub.challenge", ""), 200
    return "doğrulama başarısız", 403


@app.post("/webhook")
def webhook_al():
    ham = request.get_data()
    if not whatsapp.imza_dogru(ham, request.headers.get("X-Hub-Signature-256")):
        return "imza geçersiz", 403
    try:
        govde = json.loads(ham or b"{}")
    except ValueError:
        return "ok", 200
    # Gönderilen mesajların teslim durumu (sent / delivered / read / failed)
    for entry in govde.get("entry", []):
        for change in entry.get("changes", []):
            for d in change.get("value", {}).get("statuses", []):
                hatalar = "; ".join(f"{h.get('code')} {h.get('title')} — {(h.get('error_data') or {}).get('details', '')}"
                                    for h in d.get("errors", []))
                print(f"[durum] {d.get('recipient_id')} {d.get('status')} {hatalar}".rstrip(), flush=True)
    for kayit in whatsapp.webhook_mesajlari(govde):
        if db.wa_mesaj_islendi_mi(kayit["wa_id"]):
            continue
        s = numaradan_sirket(kayit["phone_number_id"])
        if not s:
            print(f"[webhook] tanımsız numara: {kayit['phone_number_id']}")
            continue
        # Meta 200'ü hızlı bekler; işi arka plana at
        threading.Thread(target=akis.whatsapp_mesaj, args=(s, kayit), daemon=True).start()
    return "ok", 200


def _uyarilar():
    if not WA_APP_SECRET:
        print("  ⚠️  WA_APP_SECRET boş — webhook'a gelen sahte istekler ayırt edilemez. Gerçek müşteride MUTLAKA doldur.")
    if not GEMINI_UCRETLI:
        print("  ⚠️  Gemini ÜCRETSİZ katmanda: Google bu verileri ürün geliştirmede kullanabilir.\n"
              "      Gerçek müşteri verisiyle çalışmadan önce ücretli plana geç ve .env'de GEMINI_UCRETLI=1 yap.")


if __name__ == "__main__":
    print(f"\n  Demo:  http://localhost:{PORT}/\n  Panel: http://localhost:{PORT}/panel\n")
    _uyarilar()
    app.run(host="0.0.0.0", port=PORT, threaded=True)
