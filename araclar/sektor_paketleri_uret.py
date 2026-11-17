"""Sektör paketlerinin ilk sürümünü üretir. Sonrasında JSON'lar elle düzenlenebilir.
Kullanım: python araclar/sektor_paketleri_uret.py   (var olan dosyaların üzerine yazar!)"""
import json
from pathlib import Path

HEDEF = Path(__file__).resolve().parent.parent / "sektorler"
HEDEF.mkdir(exist_ok=True)


def haftaici(s):
    return {"pzt": s, "sal": s, "car": s, "per": s, "cum": s}


def bos_ayar():
    return {"ozel_kurallar": [], "whatsapp": {"phone_number_id": ""}}


P = {}

P["genel"] = {
    "ad": "Genel İşletme",
    "rol": "Müşterilerin sorularını yanıtlar, bilgi verir ve gerektiğinde randevu oluşturursun.",
    "ton": "samimi, kibar, çözüm odaklı",
    "randevu_kelimesi": "randevu",
    "randevu_bilgileri": ["ad soyad", "hizmet", "gün ve saat"],
    "kurallar": [],
}

P["dis_klinigi"] = {
    "ad": "Diş Kliniği / Sağlık",
    "rol": "Hastaların tedavi, fiyat, randevu ve klinik hakkındaki sorularını yanıtlar, muayene randevusu oluşturursun.",
    "ton": "güven veren, sakin, nazik ve profesyonel; hastanın kaygısını anlayışla karşıla",
    "randevu_kelimesi": "randevu",
    "randevu_bilgileri": ["hastanın adı soyadı", "istenen işlem (muayene, temizlik, dolgu vb.)", "gün ve saat"],
    "kurallar": [
        "Asla tanı koyma, ilaç önerme veya tedavi kararı verme; bunun için muayene gerektiğini söyle.",
        "ACİL durum sadece şunlardır: dayanılmaz ağrı, yüzde/çenede şişlik, durmayan kanama, kaza/darbe sonucu kırık diş. Bunlarda hemen yetkiliye_aktar ve kliniğin telefonunu ver. Hafif diş eti kanaması, hassasiyet, dolgu düşmesi gibi durumlar acil değildir: normal muayene randevusu öner.",
        "Kesin tedavi fiyatı muayene sonrası belli olur; listede 'başlayan' fiyat varsa bunu belirt.",
        "Sağlık bilgisi KVKK'da özel nitelikli kişisel veridir: şikayet/hastalık ayrıntısı SORMA ve randevu notuna YAZMA; "
        "notlara sadece istenen işlemi yaz (örn. 'muayene', 'diş taşı temizliği'). Hasta kendisi ayrıntı yazarsa tekrar etme, 'detayları muayenede hekimimizle konuşabilirsiniz' de.",
    ],
    "ornek_sirket": {
        "ad": "Gülüş Ağız ve Diş Sağlığı Polikliniği", "asistan_adi": "Elif",
        "aciklama": "Kadıköy'de 12 yıllık deneyimli diş polikliniği. 4 diş hekimi, panoramik röntgen ve dijital gülüş tasarımı.",
        "adres": "Caferağa Mah. Moda Cad. No:45 Kat:2, Kadıköy / İstanbul", "telefon": "0216 555 12 34",
        "calisma_saatleri": {**haftaici("09:00-19:00"), "cmt": "10:00-16:00", "paz": None},
        "hizmetler": [
            {"ad": "Muayene ve kontrol", "fiyat": "750 TL", "sure_dk": 30},
            {"ad": "Diş taşı temizliği", "fiyat": "1.500 TL", "sure_dk": 45},
            {"ad": "Dolgu", "fiyat": "2.000 TL'den başlayan", "sure_dk": 45},
            {"ad": "Kanal tedavisi", "fiyat": "4.500 TL'den başlayan", "sure_dk": 60},
            {"ad": "Diş beyazlatma (ofis tipi)", "fiyat": "6.000 TL", "sure_dk": 90},
            {"ad": "İmplant", "fiyat": "18.000 TL'den başlayan (muayene sonrası netleşir)", "sure_dk": 60},
            {"ad": "Çocuk diş hekimliği muayenesi", "fiyat": "750 TL", "sure_dk": 30},
        ],
        "sss": [
            {"soru": "Otopark var mı?", "cevap": "Binanın arkasında anlaşmalı otopark var, 2 saat ücretsiz."},
            {"soru": "SGK geçerli mi?", "cevap": "SGK anlaşmamız yok, bazı özel sigortalarla anlaşmamız var; sigorta adını yazarsanız kontrol ederiz."},
            {"soru": "Taksit var mı?", "cevap": "Kredi kartına 6 aya kadar taksit yapılıyor."},
        ],
        "kampanyalar": ["Kasım ayına özel: diş taşı temizliği + kontrol 1.900 TL"],
        "odeme": "Nakit, kredi kartı (6 taksit), havale",
        "randevu": {"aktif": True, "slot_dk": 30, "kapasite": 3, "varsayilan_sure_dk": 30, "en_az_kac_saat_once": 2, "kac_gun_ileri": 30},
        "yetkili": {"ad": "Klinik sekreteri", "telegram_chat_id": ""}, **bos_ayar(),
    },
}

P["kuafor_guzellik"] = {
    "ad": "Kuaför / Berber / Güzellik Salonu",
    "rol": "Müşterilerin hizmet, fiyat ve randevu sorularını yanıtlar, randevu oluşturursun.",
    "ton": "sıcak, enerjik, samimi (siz diye hitap et)",
    "randevu_kelimesi": "randevu",
    "randevu_bilgileri": ["ad soyad", "istenen hizmet(ler)", "tercih edilen uzman (varsa)", "gün ve saat"],
    "kurallar": [
        "Saç boyası, keratin gibi işlemlerde fiyatın saç uzunluğuna göre değişebileceğini belirt.",
        "Birden fazla hizmet istenirse en uzun hizmeti randevu hizmeti olarak seç, diğerlerini notlara yaz.",
        "Tercih edilen uzman varsa notlara yaz.",
    ],
    "ornek_sirket": {
        "ad": "Bella Kuaför & Güzellik", "asistan_adi": "Derya",
        "aciklama": "Ataşehir'de kadın-erkek kuaför ve güzellik salonu. 3 kuaför, 1 güzellik uzmanı.",
        "adres": "Atatürk Mah. Ataşehir Bulvarı No:12/B, Ataşehir / İstanbul", "telefon": "0216 444 55 66",
        "instagram": "@bellakuafor",
        "calisma_saatleri": {"pzt": None, "sal": "10:00-20:00", "car": "10:00-20:00", "per": "10:00-20:00",
                             "cum": "10:00-20:00", "cmt": "09:00-20:00", "paz": "11:00-18:00"},
        "hizmetler": [
            {"ad": "Kadın saç kesimi", "fiyat": "800 TL", "sure_dk": 45},
            {"ad": "Erkek saç kesimi", "fiyat": "450 TL", "sure_dk": 30},
            {"ad": "Fön", "fiyat": "400 TL", "sure_dk": 30},
            {"ad": "Dip boya", "fiyat": "1.500 TL'den başlayan", "sure_dk": 90},
            {"ad": "Balyaj / ombre", "fiyat": "4.500 TL'den başlayan", "sure_dk": 180},
            {"ad": "Keratin bakım", "fiyat": "3.500 TL'den başlayan", "sure_dk": 150},
            {"ad": "Manikür", "fiyat": "500 TL", "sure_dk": 45},
            {"ad": "Kalıcı oje", "fiyat": "650 TL", "sure_dk": 60},
            {"ad": "Kaş-bıyık", "fiyat": "200 TL", "sure_dk": 15},
        ],
        "urunler": [{"ad": "Uzmanlarımız", "detay": "Selin (renk uzmanı), Mert (erkek kesim), Aylin (kesim-fön), Zeynep (manikür, kaş)"}],
        "sss": [{"soru": "Gelin başı yapıyor musunuz?", "cevap": "Evet, gelin paketi için yetkilimiz size özel fiyat verir."}],
        "kampanyalar": ["Salı-çarşamba günleri fön %20 indirimli"],
        "odeme": "Nakit, kredi kartı",
        "randevu": {"aktif": True, "slot_dk": 15, "kapasite": 4, "varsayilan_sure_dk": 30, "en_az_kac_saat_once": 1, "kac_gun_ileri": 21},
        "yetkili": {"ad": "Salon sahibi", "telegram_chat_id": ""}, **bos_ayar(),
    },
}
P["kuafor_guzellik"]["ornek_sirket"]["ozel_kurallar"] = ["Gelin paketi sorulursa yetkiliye_aktar."]

P["restoran_kafe"] = {
    "ad": "Restoran / Kafe",
    "rol": "Menü, fiyat, çalışma saati, adres sorularını yanıtlar ve masa rezervasyonu alırsın.",
    "ton": "güler yüzlü, iştah açıcı, samimi",
    "randevu_kelimesi": "rezervasyon",
    "randevu_bilgileri": ["ad soyad", "kişi sayısı", "gün ve saat", "özel istek (doğum günü, bebek sandalyesi, alerji vb.)"],
    "kurallar": [
        "Rezervasyonda hizmet olarak 'Masa rezervasyonu' kullan, kişi sayısını kisi_sayisi alanına yaz.",
        "Kişi sayısı 10'dan fazlaysa grup rezervasyonu için yetkiliye_aktar.",
        "Paket servis siparişini WhatsApp'tan alma; paket servis bilgisi işletme bilgilerinde varsa onu ver.",
        "Alerji sorularında içerik bilgisi yoksa kesin konuşma, mutfağa sorulacağını söyle ve yetkiliye_aktar.",
    ],
    "ornek_sirket": {
        "ad": "Lezzet Durağı Ocakbaşı", "asistan_adi": "Ece",
        "aciklama": "Beşiktaş'ta ocakbaşı ve meze restoranı. 90 kişilik iç salon + 40 kişilik bahçe.",
        "adres": "Sinanpaşa Mah. Ihlamurdere Cad. No:30, Beşiktaş / İstanbul", "telefon": "0212 333 22 11",
        "calisma_saatleri": {**haftaici("12:00-23:30"), "cmt": "12:00-23:59", "paz": "12:00-23:00"},
        "hizmetler": [{"ad": "Masa rezervasyonu", "fiyat": "Ücretsiz", "sure_dk": 120}],
        "urunler": [
            {"ad": "Adana kebap", "fiyat": "520 TL"}, {"ad": "Kuzu şiş", "fiyat": "640 TL"},
            {"ad": "Karışık ızgara (2 kişilik)", "fiyat": "1.450 TL"}, {"ad": "Meze tabağı (6 çeşit)", "fiyat": "480 TL"},
            {"ad": "Künefe", "fiyat": "260 TL"}, {"ad": "Ayran", "fiyat": "70 TL"},
            {"ad": "Vejetaryen seçenekler", "detay": "Közlenmiş sebze tabağı 340 TL, mantar sote 290 TL"},
        ],
        "sss": [
            {"soru": "Paket servis var mı?", "cevap": "Evet, Yemeksepeti ve Trendyol Yemek'te 'Lezzet Durağı Beşiktaş' adıyla varız."},
            {"soru": "Alkol var mı?", "cevap": "Evet, rakı, şarap ve bira servisimiz var."},
            {"soru": "Otopark?", "cevap": "Vale hizmetimiz var (150 TL)."},
        ],
        "kampanyalar": ["Hafta içi 12:00-15:00 iş menüsü 390 TL (çorba + ana yemek + içecek)"],
        "odeme": "Nakit, kredi kartı, yemek kartları (Multinet, Sodexo, Ticket)",
        "randevu": {"aktif": True, "slot_dk": 30, "kapasite": 12, "varsayilan_sure_dk": 120, "en_az_kac_saat_once": 1, "kac_gun_ileri": 30},
        "yetkili": {"ad": "Restoran müdürü", "telegram_chat_id": ""}, **bos_ayar(),
    },
}

P["emlak"] = {
    "ad": "Emlak Ofisi",
    "rol": "Portföydeki ilanlar hakkında bilgi verir, müşterinin ne aradığını anlar (satılık/kiralık, bölge, bütçe, oda sayısı) ve yer gösterme randevusu alırsın.",
    "ton": "profesyonel, güvenilir, yardımsever",
    "randevu_kelimesi": "yer gösterme randevusu",
    "randevu_bilgileri": ["ad soyad", "görmek istediği ilan", "gün ve saat"],
    "kurallar": [
        "Müşteri ne aradığını söylerse portföyden uygun ilanları öner; uygun ilan yoksa kriterlerini al ve yetkiliye_aktar.",
        "Fiyatta pazarlık sorularını yetkiliye_aktar; kendi başına indirim sözü verme.",
        "Tapu, kredi, hukuki konularda kesin bilgi verme; danışmanın detay vereceğini söyle.",
        "Yer gösterme randevusunda hizmet olarak 'Yer gösterme' kullan, ilan adını notlara yaz.",
    ],
    "ornek_sirket": {
        "ad": "Kent Gayrimenkul", "asistan_adi": "Can",
        "aciklama": "Üsküdar ve Ümraniye bölgesinde 15 yıllık emlak danışmanlığı.",
        "adres": "Altunizade Mah. Kuşbakışı Cad. No:8, Üsküdar / İstanbul", "telefon": "0216 777 88 99",
        "calisma_saatleri": {**haftaici("09:30-19:00"), "cmt": "10:00-17:00", "paz": None},
        "hizmetler": [{"ad": "Yer gösterme", "fiyat": "Ücretsiz", "sure_dk": 60},
                      {"ad": "Ücretsiz ekspertiz / değerleme görüşmesi", "fiyat": "Ücretsiz", "sure_dk": 45}],
        "urunler": [
            {"ad": "SATILIK 3+1 Altunizade", "fiyat": "11.500.000 TL", "detay": "145 m², 6 yaşında, site içi, havuz, otopark, metroya 5 dk"},
            {"ad": "KİRALIK 2+1 Ümraniye Çakmak", "fiyat": "32.000 TL/ay", "detay": "95 m², eşyasız, doğalgaz, aidat 1.200 TL"},
            {"ad": "SATILIK 1+1 Üsküdar Merkez", "fiyat": "5.900.000 TL", "detay": "60 m², yeni bina, yatırımlık"},
            {"ad": "KİRALIK Dükkan Bağlarbaşı", "fiyat": "45.000 TL/ay", "detay": "80 m², cadde üzeri"},
        ],
        "sss": [{"soru": "Komisyon ne kadar?", "cevap": "Satışta %2+KDV, kiralamada 1 aylık kira bedeli + KDV."}],
        "kampanyalar": [], "odeme": "",
        "randevu": {"aktif": True, "slot_dk": 60, "kapasite": 2, "varsayilan_sure_dk": 60, "en_az_kac_saat_once": 3, "kac_gun_ileri": 21},
        "yetkili": {"ad": "Emlak danışmanı", "telegram_chat_id": ""}, **bos_ayar(),
    },
}

P["oto_servis"] = {
    "ad": "Oto Servis / Bakım / Yıkama",
    "rol": "Araç bakım, onarım, fiyat sorularını yanıtlar ve servis randevusu (araç kabul) oluşturursun.",
    "ton": "net, güvenilir, pratik",
    "randevu_kelimesi": "servis randevusu",
    "randevu_bilgileri": ["ad soyad", "araç marka-model-yıl", "plaka", "yapılacak işlem / arıza tarifi", "gün ve saat"],
    "kurallar": [
        "Arıza tanısı koyma; 'kontrol sonrası netleşir' de. Fiyatlar araca göre değişebilir.",
        "Araç bilgisi ve plakayı randevu notlarına yaz.",
        "Yolda kalma / çekici talebinde hemen yetkiliye_aktar.",
    ],
    "ornek_sirket": {
        "ad": "Usta Oto Servis", "asistan_adi": "Burak",
        "aciklama": "Tüm marka binek araçlar için periyodik bakım, mekanik, elektrik ve lastik hizmeti. Bostancı sanayi sitesinde.",
        "adres": "Bostancı Oto Sanayi Sitesi C Blok No:14, Kadıköy / İstanbul", "telefon": "0216 222 33 44",
        "calisma_saatleri": {**haftaici("08:30-18:30"), "cmt": "08:30-15:00", "paz": None},
        "hizmetler": [
            {"ad": "Periyodik bakım (yağ + filtre)", "fiyat": "3.500 TL'den başlayan", "sure_dk": 90},
            {"ad": "Fren balatası değişimi", "fiyat": "2.200 TL'den başlayan (parça dahil)", "sure_dk": 60},
            {"ad": "Arıza tespit (bilgisayarlı)", "fiyat": "750 TL", "sure_dk": 30},
            {"ad": "Lastik değişimi + balans (4 lastik)", "fiyat": "1.200 TL", "sure_dk": 45},
            {"ad": "Klima gazı dolumu", "fiyat": "1.400 TL", "sure_dk": 45},
            {"ad": "Detaylı iç-dış yıkama", "fiyat": "900 TL", "sure_dk": 90},
        ],
        "sss": [{"soru": "Garanti veriyor musunuz?", "cevap": "Yapılan işçiliğe 6 ay, değişen parçalara üretici garantisi geçerli."},
                {"soru": "Aracı alıp getiriyor musunuz?", "cevap": "Kadıköy ve Ataşehir içinde 500 TL'ye vale hizmeti var."}],
        "kampanyalar": ["Kış bakım paketi: akü + antifriz + lastik kontrolü ücretsiz (periyodik bakımla)"],
        "odeme": "Nakit, kredi kartı (3 taksit)",
        "randevu": {"aktif": True, "slot_dk": 30, "kapasite": 3, "varsayilan_sure_dk": 60, "en_az_kac_saat_once": 2, "kac_gun_ileri": 21},
        "yetkili": {"ad": "Servis şefi", "telegram_chat_id": ""}, **bos_ayar(),
    },
}

P["fitness_spor"] = {
    "ad": "Spor Salonu / Fitness / Pilates",
    "rol": "Üyelik, ders programı, fiyat sorularını yanıtlar, ücretsiz deneme dersi veya PT görüşmesi randevusu alırsın.",
    "ton": "motive edici, enerjik, samimi",
    "randevu_kelimesi": "deneme dersi randevusu",
    "randevu_bilgileri": ["ad soyad", "hedef (kilo verme, kas, esneklik vb.)", "gün ve saat"],
    "kurallar": [
        "Sağlık sorunu (bel fıtığı, hamilelik vb.) belirtenlere egzersiz önerme; eğitmenin değerlendireceğini söyle. "
        "Sağlık bilgisi özel nitelikli kişisel veridir: ayrıntısını sorma ve randevu notuna yazma.",
        "Üyelik fiyatında özel indirim isteyenleri yetkiliye_aktar.",
        "Hedefi randevu notlarına yaz.",
    ],
    "ornek_sirket": {
        "ad": "FormaFit Gym & Pilates", "asistan_adi": "Ada",
        "aciklama": "Maltepe'de 1.200 m² spor salonu: fitness alanı, reformer pilates stüdyosu, grup dersleri, sauna.",
        "adres": "Bağlarbaşı Mah. Bağdat Cad. No:410, Maltepe / İstanbul", "telefon": "0216 111 22 33",
        "instagram": "@formafit",
        "calisma_saatleri": {**haftaici("06:30-23:00"), "cmt": "08:00-22:00", "paz": "09:00-20:00"},
        "hizmetler": [
            {"ad": "Ücretsiz deneme dersi", "fiyat": "Ücretsiz", "sure_dk": 60},
            {"ad": "Personal trainer tanışma görüşmesi", "fiyat": "Ücretsiz", "sure_dk": 30},
            {"ad": "Reformer pilates deneme", "fiyat": "500 TL", "sure_dk": 50},
        ],
        "urunler": [
            {"ad": "Aylık fitness üyeliği", "fiyat": "2.500 TL"}, {"ad": "6 aylık üyelik", "fiyat": "11.500 TL"},
            {"ad": "Yıllık üyelik", "fiyat": "19.000 TL"}, {"ad": "Reformer pilates 8 ders paketi", "fiyat": "6.400 TL"},
            {"ad": "PT 10 ders paketi", "fiyat": "12.000 TL"},
            {"ad": "Grup ders programı", "detay": "Zumba Sal-Per 19:00, Spinning Pzt-Çar-Cum 20:00, Yoga Cmt 11:00"},
        ],
        "sss": [{"soru": "Dondurma hakkı var mı?", "cevap": "6 aylıkta 15 gün, yıllıkta 30 gün dondurma hakkı var."},
                {"soru": "Kadınlara özel alan var mı?", "cevap": "Evet, kadınlara özel fitness alanımız ve soyunma odamız var."}],
        "kampanyalar": ["Arkadaşını getir: ikiniz de 1 ay ücretsiz kazanın (yıllık üyelikte)"],
        "odeme": "Kredi kartı (12 taksite kadar), nakit",
        "randevu": {"aktif": True, "slot_dk": 30, "kapasite": 2, "varsayilan_sure_dk": 60, "en_az_kac_saat_once": 2, "kac_gun_ileri": 14},
        "yetkili": {"ad": "Salon müdürü", "telegram_chat_id": ""}, **bos_ayar(),
    },
}

P["dijital_ajans"] = {
    "ad": "Dijital Ajans / Yazılım / Hizmet",
    "rol": "Potansiyel müşterilerin hizmet, fiyat ve süreç sorularını yanıtlar, ihtiyaçlarını anlar ve ücretsiz tanışma görüşmesi planlarsın.",
    "ton": "profesyonel ama sıcak, danışman gibi; satış baskısı yapma",
    "randevu_kelimesi": "tanışma görüşmesi",
    "randevu_bilgileri": ["ad soyad", "işletme adı ve sektörü", "ihtiyaç (web sitesi, uygulama, otomasyon, video vb.)", "gün ve saat"],
    "kurallar": [
        "Müşterinin işletmesini ve ihtiyacını 1-2 soruyla anla, sonra uygun hizmeti ve fiyat aralığını söyle.",
        "Fiyatlar aralık olarak verilir; kesin fiyat ihtiyaç netleşince yazılı teklifle verilir.",
        "Ciddi ilgi gösteren müşteriye ücretsiz tanışma görüşmesi öner.",
        "İşletme adını, sektörü ve ihtiyacı randevu notlarına yaz.",
    ],
}

for ad, veri in P.items():
    (HEDEF / f"{ad}.json").write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
print("Üretildi:", ", ".join(P))
