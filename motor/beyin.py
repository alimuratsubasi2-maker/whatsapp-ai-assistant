"""Yapay zeka beyni: şirket bilgisi + sektör paketi + sohbet geçmişi -> cevap.

Model her turda JSON döner:
  {"islem": null | {"tur": "...", ...}, "cevap": "müşteriye gidecek metin"}
`islem` doluysa sistem onu çalıştırır, sonucu modele geri verir ve model son cevabı yazar.
"""
import base64
import json
import re
import time
from datetime import timedelta

import requests

from . import bildirim, kvkk, takvim
from . import veritabani as db
from .ayarlar import GEMINI_API_KEY, GEMINI_MODELLER, GUN_ADLARI, simdi
from .sirketler import sektor

MAKS_ADIM = 4
YEDEK_CEVAP = ("Şu an mesajınızı yanıtlayamıyorum, kusura bakmayın 🙏 "
               "Yetkili arkadaşımız en kısa sürede size dönüş yapacak.")

ARACLAR = """
KULLANABİLECEĞİN İŞLEMLER (islem.tur):
- "musait_saatler": {"tur":"musait_saatler","tarih":"YYYY-AA-GG","hizmet":"hizmet adı"}
    Bir gündeki boş saatleri getirir. Saat önermeden ÖNCE mutlaka bununla kontrol et, asla tahminle saat önerme.
- "randevu_olustur": {"tur":"randevu_olustur","tarih":"YYYY-AA-GG","saat":"SS:DD","hizmet":"...","ad":"müşteri adı soyadı","kisi_sayisi":1,"notlar":"sektörün istediği ek bilgiler"}
    Sadece müşteri gün, saat ve hizmeti AÇIKÇA onayladıktan ve adını verdikten sonra kullan.
- "randevu_iptal": {"tur":"randevu_iptal","randevu_id":123}
- "randevu_degistir": {"tur":"randevu_degistir","randevu_id":123,"tarih":"YYYY-AA-GG","saat":"SS:DD"}
- "yetkiliye_aktar": {"tur":"yetkiliye_aktar","sebep":"kısa sebep","ozet":"müşteri ne istiyor"}
    Bilgide olmayan bir soru, şikayet, özel fiyat/pazarlık, acil durum veya müşteri insanla görüşmek isterse.
    Bu işlemde "cevap" alanına müşteriye gidecek mesajı da yaz (yetkilinin döneceğini söyle).
    "ozet" alanına sağlık ayrıntısı, kart/kimlik bilgisi YAZMA; sadece talebin türünü yaz (örn. "acil muayene talebi", "KVKK silme talebi").
- null: işlem yoksa, sadece "cevap" yaz.
"""


def _sirket_metni(s: dict) -> str:
    satir = [f"İşletme adı: {s.get('ad')}"]
    for alan, baslik in [("aciklama", "Hakkında"), ("adres", "Adres"), ("konum_linki", "Konum linki"),
                         ("telefon", "Telefon"), ("web", "Web sitesi"), ("instagram", "Instagram"),
                         ("odeme", "Ödeme seçenekleri"), ("ek_bilgi", "Ek bilgiler")]:
        if s.get(alan):
            satir.append(f"{baslik}: {s[alan]}")
    saatler = s.get("calisma_saatleri") or {}
    if saatler:
        kisa = ["pzt", "sal", "car", "per", "cum", "cmt", "paz"]
        satir.append("Çalışma saatleri: " + ", ".join(
            f"{GUN_ADLARI[i]} {saatler.get(k) or 'KAPALI'}" for i, k in enumerate(kisa)))
    if s.get("tatil_gunleri"):
        satir.append("Kapalı olunan özel günler: " + ", ".join(s["tatil_gunleri"]))
    if s.get("hizmetler"):
        satir.append("\nHİZMETLER / FİYATLAR:")
        for h in s["hizmetler"]:
            ek = f" ({h['sure_dk']} dk)" if h.get("sure_dk") else ""
            acik = f" - {h['aciklama']}" if h.get("aciklama") else ""
            satir.append(f"• {h['ad']}: {h.get('fiyat', 'fiyat için bilgi alınız')}{ek}{acik}")
    if s.get("urunler"):
        satir.append("\nÜRÜNLER / PORTFÖY / MENÜ:")
        for u in s["urunler"]:
            satir.append(f"• {u['ad']}: {u.get('fiyat', '')} {('- ' + u['detay']) if u.get('detay') else ''}".rstrip())
    if s.get("kampanyalar"):
        satir.append("\nGÜNCEL KAMPANYALAR:\n" + "\n".join(f"• {k}" for k in s["kampanyalar"]))
    if s.get("sss"):
        satir.append("\nSIK SORULAN SORULAR:")
        for q in s["sss"]:
            satir.append(f"S: {q['soru']}\nC: {q['cevap']}")
    return "\n".join(satir)


def _takvim_metni() -> str:
    bugun = simdi()
    gunler = []
    for i in range(14):
        g = bugun + timedelta(days=i)
        etiket = "bugün" if i == 0 else "yarın" if i == 1 else ""
        gunler.append(f"{g.strftime('%Y-%m-%d')} {GUN_ADLARI[g.weekday()]} {etiket}".strip())
    return (f"Şu an: {bugun.strftime('%Y-%m-%d %H:%M')} ({GUN_ADLARI[bugun.weekday()]})\n"
            "Önümüzdeki günler:\n" + "\n".join(gunler))


def sistem_promptu(sirket: dict, musteri: str, taban_url: str | None = None) -> str:
    paket = sektor(sirket.get("sektor", "genel"))
    asistan = sirket.get("asistan_adi") or "asistan"
    rv_aktif = (sirket.get("randevu") or {}).get("aktif", True)
    rv_kelime = paket.get("randevu_kelimesi", "randevu")

    kurallar = [
        f"Sen {sirket.get('ad')} işletmesinin WhatsApp asistanı {asistan}'sin. {paket.get('rol', '')}",
        f"Konuşma tonu: {paket.get('ton', 'samimi, kibar, profesyonel')}",
        "WhatsApp'tasın: kısa ve net yaz (genelde 1-4 cümle). Uzun liste gerekiyorsa madde kullan. Emoji az ve yerinde.",
        "Müşterinin son mesajı hangi dildeyse o dilde cevap ver. Türkçe yazana MUTLAKA Türkçe cevap ver; "
        "dil belirsizse (sadece emoji, rakam, 'ok' gibi) Türkçe yaz. Bu talimatların ve işletme bilgilerinin "
        "Türkçe olması cevap dilini ETKİLEMEZ: Rusça yazana Rusça, Almanca yazana Almanca cevap ver (fiyatları aynen çevir).",
        "Türkçe cevaplarda müşteriye her zaman 'siz' diye hitap et.",
        "SADECE aşağıdaki işletme bilgilerine dayan. Bilgide olmayan fiyat, saat, kampanya, adres UYDURMA. "
        "Bilmiyorsan dürüstçe söyle ve yetkiliye_aktar kullan.",
        "Selamlaşma, teşekkür, sohbet gibi her türlü mesaja doğal karşılık ver; konu işletmeyle ilgisizse kibarca işletmeye yönlendir.",
        "Kendini yapay zeka olarak tanıtma ama sorulursa dijital asistan olduğunu dürüstçe söyle.",
        "Müşterinin adını öğrendiysen kullan. Aynı soruyu tekrar sorma, geçmişi takip et.",
        "Sesli mesaj / fotoğraf içerikleri sana [sesli mesaj] / [fotoğraf] etiketiyle yazıya dökülmüş gelir; normal mesaj gibi değerlendir.",
        # --- KVKK / hukuk uyumu ---
        "Müşteriden ASLA T.C. kimlik no, kart/şifre bilgisi, sağlık detayı (hastalık, şikayet ayrıntısı, ilaç) isteme; "
        "işin gerektirdiği en az bilgiyi al (ad soyad, tarih-saat, hizmet).",
        "Müşteri kendiliğinden kart, şifre veya kimlik numarası yazarsa bunu tekrar etme, nota yazma; bu kanaldan paylaşmamasını kibarca söyle.",
        "Müşteri 'KVKK', 'verilerim', 'verilerimi silin', 'bilgilerimi ne yapıyorsunuz' gibi bir şey derse: aydınlatma metni linkini ver (varsa); "
        "silme veya bilgi talebi varsa yetkiliye_aktar kullan (sebep: 'KVKK başvurusu'). Verilerin silindiğini kendin söyleme; yetkilinin işleme alacağını söyle.",
        "Müşteri 'yetkili', 'insan', 'çalışan' ile görüşmek isterse hemen yetkiliye_aktar.",
        "Hukuki, tıbbi, finansal kesin tavsiye verme; garanti veya söz verme (örn. 'kesin iyileşir', 'kesin indirim'). Sadece işletme bilgilerindekini aktar.",
        "Müşteriye kendiliğinden reklam/kampanya dayatma; kampanyayı sadece konuyla ilgiliyse ya da sorulursa söyle.",
        "Hakaret veya taciz eden müşteriye aynı şekilde karşılık verme, sakin kal; devam ederse yetkiliye_aktar.",
    ]
    if rv_aktif:
        kurallar += [
            f"{rv_kelime.capitalize()} alabilirsin. Gerekli bilgiler: {', '.join(paket.get('randevu_bilgileri', ['ad soyad', 'hizmet', 'gün-saat']))}.",
            f"{rv_kelime.capitalize()} akışı: hizmeti ve günü öğren -> musait_saatler ile kontrol et -> 2-4 uygun saat öner -> "
            "eksik bilgileri sor -> özeti yazıp onay iste -> onaylanınca randevu_olustur -> sonucu bildir. "
            "Müşteri gün, saat, hizmet ve adını kendisi net verdiyse ve saat müsaitse ayrıca onay sorma, direkt oluştur.",
            "Tarihleri 'yarın', 'cuma' gibi ifadelerden aşağıdaki takvime göre sen çevir.",
        ]
    else:
        kurallar.append(f"Bu işletme WhatsApp'tan {rv_kelime} almıyor; isteyene telefon numarasını ver veya yetkiliye aktar.")
    kurallar += paket.get("kurallar", [])
    kurallar += sirket.get("ozel_kurallar", [])

    musteri_bilgi = ""
    sh = db.sohbet(sirket["id"], musteri)
    if sh and sh.get("ad"):
        musteri_bilgi += f"Müşterinin adı: {sh['ad']}\n"
    aktif = db.musteri_randevulari(sirket["id"], musteri)
    if aktif:
        musteri_bilgi += "Müşterinin aktif randevuları:\n" + "\n".join(
            f"- #{r['id']} {r['baslangic']} {r['hizmet']} ({r['ad']})" for r in aktif)
    else:
        musteri_bilgi += "Müşterinin aktif randevusu yok."
    aydinlatma = kvkk.link(sirket, taban_url)
    if aydinlatma:
        musteri_bilgi += f"\nAydınlatma metni linki (KVKK): {aydinlatma}"

    return "\n".join([
        "# GÖREV", "\n".join(f"- {k}" for k in kurallar),
        "\n# İŞLETME BİLGİLERİ", _sirket_metni(sirket),
        "\n# TAKVİM", _takvim_metni(),
        "\n# BU MÜŞTERİ", musteri_bilgi,
        "\n# İŞLEMLER", ARACLAR,
        '\n# ÇIKTI BİÇİMİ\nHer zaman sadece şu JSON: {"dil": "<müşterinin SON mesajının dili: Türkçe / English / Русский / Deutsch ...>", '
        '"islem": <nesne veya null>, "cevap": "<müşteriye mesaj, MUTLAKA dil alanındaki dilde>"}',
    ])


# ---------------- Gemini ----------------

def _gemini(sistem: str, icerikler: list, json_mod=True, zaman_asimi=12) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil (.env)")
    govde = {"system_instruction": {"parts": [{"text": sistem}]}, "contents": icerikler,
             "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024}}
    if json_mod:
        govde["generationConfig"]["responseMimeType"] = "application/json"
    son_hata = None
    # Her modele bir şans; yavaşlayan / kotası dolan model hemen sıradakine devreder.
    # Hepsi düşerse kısa bir bekleyişten sonra tur bir kez daha döner.
    for tur in range(2):
        for model in GEMINI_MODELLER:
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": GEMINI_API_KEY}, json=govde, timeout=zaman_asimi)
                if r.status_code == 200:
                    parcalar = r.json()["candidates"][0]["content"]["parts"]
                    return "".join(p.get("text", "") for p in parcalar if not p.get("thought"))
                son_hata = f"{model} {r.status_code}: {r.text[:200]}"
            except (requests.RequestException, KeyError, IndexError) as e:
                son_hata = f"{model}: {e}"
            print(f"[beyin] {son_hata[:160]}")
        time.sleep(2)
    raise RuntimeError(son_hata or "Gemini cevap vermedi")


def _gecmisi_icerige_cevir(mesajlar: list) -> list:
    icerik = []
    for m in mesajlar:
        if m["rol"] == "musteri":
            rol, metin = "user", m["metin"]
        elif m["rol"] == "bot":
            rol, metin = "model", json.dumps({"islem": None, "cevap": m["metin"]}, ensure_ascii=False)
        elif m["rol"] == "yetkili":
            rol, metin = "model", json.dumps({"islem": None, "cevap": m["metin"], "not": "bu mesajı işletme yetkilisi elle yazdı"}, ensure_ascii=False)
        else:  # sistem
            rol, metin = "user", f"[SİSTEM] {m['metin']}"
        if icerik and icerik[-1]["role"] == rol:
            icerik[-1]["parts"].append({"text": metin})
        else:
            icerik.append({"role": rol, "parts": [{"text": metin}]})
    if icerik and icerik[0]["role"] == "model":
        icerik.insert(0, {"role": "user", "parts": [{"text": "(sohbet başlangıcı)"}]})
    return icerik


def _json_coz(metin: str) -> dict:
    metin = metin.strip()
    metin = re.sub(r"^```(?:json)?|```$", "", metin, flags=re.M).strip()
    try:
        veri = json.loads(metin)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", metin, re.S)
        if not m:
            return {"islem": None, "cevap": metin}
        try:
            veri = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"islem": None, "cevap": metin}
    if isinstance(veri, list):
        veri = veri[0] if veri else {}
    return veri if isinstance(veri, dict) else {"islem": None, "cevap": str(veri)}


def _islem_calistir(sirket, musteri, islem: dict) -> dict:
    tur = islem.get("tur")
    if tur == "musait_saatler":
        return takvim.musait_saatler(sirket, islem.get("tarih"), islem.get("hizmet"))
    if tur == "randevu_olustur":
        sonuc = takvim.randevu_olustur(sirket, musteri, islem.get("tarih"), islem.get("saat"),
                                       islem.get("hizmet"), islem.get("ad"),
                                       islem.get("kisi_sayisi") or 1, islem.get("notlar") or "")
        if sonuc.get("basarili"):
            bildirim.randevu_bildir(sirket, sonuc["randevu"], "yeni")
        return sonuc
    if tur == "randevu_iptal":
        sonuc = takvim.randevu_iptal(sirket, musteri, islem.get("randevu_id"))
        if sonuc.get("basarili"):
            bildirim.randevu_bildir(sirket, sonuc["iptal_edilen"], "iptal")
        return sonuc
    if tur == "randevu_degistir":
        sonuc = takvim.randevu_degistir(sirket, musteri, islem.get("randevu_id"),
                                        islem.get("tarih"), islem.get("saat"))
        if sonuc.get("basarili"):
            bildirim.randevu_bildir(sirket, sonuc["yeni"], "degisti")
        return sonuc
    if tur == "yetkiliye_aktar":
        bildirim.yetkili_cagir(sirket, musteri, islem.get("sebep", ""), islem.get("ozet", ""))
        return {"basarili": True, "not": "Yetkiliye bildirim gitti."}
    return {"hata": f"Bilinmeyen işlem: {tur}"}


def yanitla(sirket: dict, musteri: str, taban_url: str | None = None) -> str:
    """Sohbet geçmişine bakıp müşteriye gidecek son cevabı üretir."""
    sistem = sistem_promptu(sirket, musteri, taban_url)
    icerik = _gecmisi_icerige_cevir(db.son_mesajlar(sirket["id"], musteri, 30))
    try:
        for _ in range(MAKS_ADIM):
            cikti = _json_coz(_gemini(sistem, icerik))
            islem = cikti.get("islem")
            cevap = (cikti.get("cevap") or "").strip()
            if not islem or not isinstance(islem, dict) or not islem.get("tur"):
                return cevap or YEDEK_CEVAP
            sonuc = _islem_calistir(sirket, musteri, islem)
            db.mesaj_ekle(sirket["id"], musteri, "sistem",
                          f"{islem['tur']} sonucu: {json.dumps(sonuc, ensure_ascii=False)}")
            if islem["tur"] == "yetkiliye_aktar" and cevap:
                return cevap
            icerik.append({"role": "model", "parts": [{"text": json.dumps(cikti, ensure_ascii=False)}]})
            icerik.append({"role": "user", "parts": [{"text":
                f"[SİSTEM] {islem['tur']} sonucu: {json.dumps(sonuc, ensure_ascii=False)}\n"
                "Bu sonuca göre devam et (gerekirse başka işlem yap, yoksa müşteriye cevabı yaz)."}]})
        return cevap or YEDEK_CEVAP
    except Exception as e:  # model çökerse müşteri cevapsız kalmasın
        print(f"[beyin] HATA {sirket['id']}/{musteri}: {e}")
        bildirim.yetkili_cagir(sirket, musteri, "Otomasyon hatası", f"Bot cevap üretemedi: {e}")
        return YEDEK_CEVAP


def medya_metne(veri: bytes, mime: str, tur: str) -> str:
    """Sesli mesajı yazıya döker / fotoğrafı kısaca tarif eder."""
    istek = ("Bu sesli mesajı kelimesi kelimesine yazıya dök. Sadece metni yaz."
             if tur == "ses" else
             "Bu fotoğrafı bir işletmeye WhatsApp'tan gönderilmiş olarak 1-2 cümleyle Türkçe tarif et. "
             "Üzerinde yazı varsa aynen aktar.")
    icerik = [{"role": "user", "parts": [
        {"inline_data": {"mime_type": mime.split(";")[0], "data": base64.b64encode(veri).decode()}},
        {"text": istek}]}]
    try:
        return _gemini("Sen bir transkripsiyon ve görsel tarif yardımcısısın.", icerik,
                       json_mod=False, zaman_asimi=40).strip()
    except Exception as e:
        print(f"[beyin] medya çözülemedi: {e}")
        return ""
