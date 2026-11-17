"""KVKK: aydınlatma metni sayfası, ilk mesaj bilgilendirmesi, saklama süresi temizliği.

Şirket dosyasındaki isteğe bağlı alan:
  "kvkk": {"unvan": "...", "adres": "...", "eposta": "...", "telefon": "...", "saklama_gun": 180}
Boş alanlar şirketin genel bilgilerinden doldurulur.
NOT: Bu bir şablondur, hukuki görüş değildir; gerçek müşteride avukata kontrol ettirilmelidir.
"""
import html
import re
import threading
import time

from . import veritabani as db
from .ayarlar import PUBLIC_URL, VARSAYILAN_SAKLAMA_GUN


def _bilgi(s: dict) -> dict:
    k = dict(s.get("kvkk") or {})
    k.setdefault("unvan", s.get("ad", ""))
    k["unvan"] = k["unvan"] or s.get("ad", "")
    for alan in ("adres", "telefon"):
        k[alan] = k.get(alan) or s.get(alan, "")
    k["saklama_gun"] = int(k.get("saklama_gun") or VARSAYILAN_SAKLAMA_GUN)
    return k


_KART = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_TCKN = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")


def _luhn(rakamlar: str) -> bool:
    toplam = 0
    for i, c in enumerate(reversed(rakamlar)):
        d = int(c)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        toplam += d
    return toplam % 10 == 0


def _tckn_gecerli(n: str) -> bool:
    d = [int(c) for c in n]
    return (((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10 == d[9]
            and sum(d[:10]) % 10 == d[10])


def hassas_maskele(metin: str) -> str:
    """Kart ve T.C. kimlik numaralarını kaydetmeden / yapay zekaya göndermeden önce maskeler."""
    def kart(m):
        r = re.sub(r"\D", "", m.group(0))
        return f"[kart numarası gizlendi ****{r[-4:]}]" if 13 <= len(r) <= 19 and _luhn(r) else m.group(0)
    metin = _KART.sub(kart, metin)
    return _TCKN.sub(lambda m: "[T.C. kimlik no gizlendi]" if _tckn_gecerli(m.group(0)) else m.group(0), metin)


def saklama_gunu(s: dict) -> int:
    return _bilgi(s)["saklama_gun"]


def link(s: dict, taban_url: str | None = None) -> str:
    taban = (taban_url or PUBLIC_URL or "").rstrip("/")
    return f"{taban}/kvkk/{s['id']}" if taban else ""


def ilk_bilgilendirme(s: dict, taban_url: str | None = None) -> str:
    """Yeni bir müşterinin ilk cevabının altına eklenen kısa not (KVKK m.10 + şeffaflık)."""
    url = link(s, taban_url)
    ek = f"Kişisel verilerinizin işlenmesi hakkında bilgi: {url}" if url else \
        "Kişisel verilerinizin işlenmesi hakkında bilgi almak için \"KVKK\" yazabilirsiniz."
    return f"ℹ️ Bu hesapta mesajlarınıza yapay zeka destekli dijital asistanımız yanıt verir; dilediğiniz an \"yetkili\" yazarak bir çalışanımızla görüşebilirsiniz. {ek}"


def aydinlatma_html(s: dict) -> str:
    k = _bilgi(s)
    e = lambda v: html.escape(str(v or ""))
    iletisim = " · ".join(p for p in [e(k.get("adres")), e(k.get("telefon")), e(k.get("eposta"))] if p)
    basvuru = (f"<b>{e(k['eposta'])}</b> adresine e-posta ile" if k.get("eposta") else "işletmenin adresine yazılı olarak")
    return f"""<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kişisel Verilerin İşlenmesine İlişkin Aydınlatma Metni — {e(k['unvan'])}</title>
<style>body{{font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;max-width:760px;margin:0 auto;padding:28px 18px;
line-height:1.6;color:#1f2933;font-size:15.5px}}h1{{font-size:21px;line-height:1.3}}h2{{font-size:16.5px;margin-top:26px}}
li{{margin:4px 0}}.kutu{{background:#fff7e0;border-radius:8px;padding:12px 14px;margin:16px 0}}small{{color:#6b7280}}</style></head><body>
<h1>WhatsApp Kanalı — Kişisel Verilerin İşlenmesine İlişkin Aydınlatma Metni</h1>
<p>Bu metin, 6698 sayılı Kişisel Verilerin Korunması Kanunu'nun ("KVKK") 10. maddesi uyarınca, <b>{e(k['unvan'])}</b>
("İşletme") WhatsApp hesabına mesaj gönderen kişileri bilgilendirmek amacıyla hazırlanmıştır.</p>
<div class="kutu">Bu WhatsApp hesabında mesajlarınıza <b>yapay zeka destekli dijital asistan</b> yanıt verir.
Dilediğiniz an "yetkili" yazarak bir çalışanla görüşmek isteyebilirsiniz.
Kart ve T.C. kimlik numaraları sistem tarafından otomatik gizlenir; yine de lütfen bu kanaldan <b>sağlık bilgisi, T.C. kimlik numarası, kart veya şifre bilgisi</b> gibi hassas verilerinizi paylaşmayınız.</div>

<h2>1. Veri sorumlusu</h2>
<p>{e(k['unvan'])}{('<br>' + iletisim) if iletisim else ''}</p>

<h2>2. İşlenen kişisel veriler</h2>
<ul><li>Telefon numaranız ve WhatsApp profil adınız</li>
<li>Gönderdiğiniz mesajların içeriği (yazılı mesaj; gönderirseniz sesli mesaj, fotoğraf, konum)</li>
<li>Randevu / rezervasyon için verdiğiniz bilgiler (ad soyad, tarih-saat, talep ettiğiniz hizmet, kişi sayısı, notlar)</li></ul>

<h2>3. İşleme amaçları</h2>
<ul><li>Sorularınızı yanıtlamak ve ürün/hizmetler hakkında bilgi vermek</li>
<li>Randevu ve rezervasyon oluşturmak, değiştirmek, iptal etmek</li>
<li>Talebinizi, gerektiğinde İşletme yetkilisine iletmek</li>
<li>Hizmet kalitesini ve müşteri memnuniyetini sağlamak</li></ul>

<h2>4. Hukuki sebepler ve toplama yöntemi</h2>
<p>Kişisel verileriniz, WhatsApp üzerinden elektronik ortamda ve otomatik yollarla toplanır; KVKK m.5/2-(c)
"bir sözleşmenin kurulması veya ifasıyla doğrudan ilgili olması" ve m.5/2-(f) "ilgili kişinin temel hak ve özgürlüklerine
zarar vermemek kaydıyla veri sorumlusunun meşru menfaati" hukuki sebeplerine dayanılarak işlenir.</p>

<h2>5. Aktarım ve yurt dışına aktarım</h2>
<p>Hizmetin sunulabilmesi için kişisel verileriniz, veri işleyen sıfatıyla hizmet aldığımız şu taraflarla paylaşılır:</p>
<ul><li><b>Meta Platforms</b> (WhatsApp Business altyapısı) — mesajların iletilmesi</li>
<li><b>Google</b> (Gemini yapay zeka hizmeti) — mesajlarınıza yanıt oluşturulması</li>
<li><b>NovaDijitalTR</b> — otomasyon sisteminin kurulumu, barındırılması ve teknik desteği</li>
<li><b>Telegram</b> — randevu ve yetkili taleplerinin İşletme yetkilisine bildirilmesi (ad, telefon, talep özeti)</li></ul>
<p>Meta, Google ve Telegram'ın sunucuları yurt dışında bulunduğundan kişisel verileriniz KVKK m.9 kapsamında yurt dışına aktarılmaktadır.
Ayrıca kanunen yetkili kamu kurum ve kuruluşlarına, talep halinde ve mevzuatın izin verdiği ölçüde aktarılabilir.</p>

<h2>6. Saklama süresi</h2>
<p>Mesaj kayıtları ve geçmiş randevu bilgileri <b>{k['saklama_gun']} gün</b> sonra otomatik olarak silinir.
Silme talebinde bulunmanız halinde daha önce silinir.</p>

<h2>7. Haklarınız (KVKK m.11)</h2>
<ul><li>Kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenmişse bilgi talep etme</li>
<li>İşlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme</li>
<li>Yurt içinde veya yurt dışında aktarıldığı üçüncü kişileri bilme</li>
<li>Eksik veya yanlış işlenmişse düzeltilmesini, KVKK m.7 şartları çerçevesinde silinmesini veya yok edilmesini isteme</li>
<li>Bu işlemlerin, verilerin aktarıldığı üçüncü kişilere bildirilmesini isteme</li>
<li>Münhasıran otomatik sistemlerle analiz edilmesi sonucu aleyhinize bir sonucun ortaya çıkmasına itiraz etme</li>
<li>Kanuna aykırı işleme sebebiyle zarara uğramanız halinde zararın giderilmesini talep etme</li></ul>

<h2>8. Başvuru</h2>
<p>Haklarınıza ilişkin taleplerinizi {basvuru} iletebilirsiniz. WhatsApp sohbetinde "verilerimi silin" yazmanız halinde
talebiniz İşletme yetkilisine iletilir. Başvurular en geç 30 gün içinde ücretsiz olarak sonuçlandırılır.</p>
<p><small>Son güncelleme: 2026-11 · Altyapı: NovaDijitalTR</small></p>
</body></html>"""


def _temizlik_dongusu():
    from .sirketler import tum_sirketler
    while True:
        for s in tum_sirketler():
            try:
                silinen = db.eski_kayitlari_sil(s["id"], saklama_gunu(s))
                if silinen:
                    print(f"[kvkk] {s['id']}: saklama süresi dolan {silinen} mesaj silindi")
            except Exception as e:
                print(f"[kvkk] temizlik hatası {s.get('id')}: {e}")
        time.sleep(24 * 3600)


def saklama_temizligini_baslat():
    threading.Thread(target=_temizlik_dongusu, daemon=True).start()
