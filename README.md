# NovaDijitalTR — WhatsApp Yapay Zeka Asistanı

İşletmelerin WhatsApp'ına gelen her mesaja 7/24 otomatik cevap veren sistem:
soruları cevaplar, randevu/rezervasyon alır, değiştirir, iptal eder, sesli mesaj ve fotoğrafı anlar,
bilmediği konuda (pazarlık, şikayet, acil durum) işletme sahibine Telegram'dan haber verir.

## Çalıştırma

`baslat.bat` dosyasına çift tıkla (ya da `python app.py`).

| Adres | Ne işe yarar |
|---|---|
| http://localhost:5080/ | Demo listesi: müşteriye canlı sunum |
| http://localhost:5080/demo/novadijitaltr | WhatsApp görünümlü test ekranı |
| http://localhost:5080/panel | Yönetim paneli (şifre `.env` içinde `PANEL_SIFRE`) |

## Yapı: ortak motor + sektör paketleri

```
motor/        HERKESİN ORTAK MOTORU (bir kez yazıldı, her müşteride aynı)
  beyin.py      yapay zeka: şirket bilgisi + sektör kuralları + sohbet geçmişi → cevap
  takvim.py     çalışma saatleri, kapasite, müsait saat, çakışma kontrolü
  akis.py       mesaj al → birleştir (4 sn) → cevapla → gönder
  whatsapp.py   Meta WhatsApp Cloud API
  bildirim.py   işletme sahibine Telegram bildirimi
sektorler/    HER SEKTÖRE AYRI PAKET (konuşma tonu, randevuda istenecek bilgiler, özel kurallar, örnek işletme)
sirketler/    HER MÜŞTERİ ŞİRKETE BİR DOSYA (fiyatlar, saatler, SSS, kampanyalar, Telegram, WhatsApp numarası)
veri/         veritabanı (sohbetler, randevular) — yedeklenmeli
```

Hazır sektörler: diş kliniği/sağlık, kuaför/güzellik, restoran/kafe, emlak, oto servis, spor salonu, dijital ajans, genel.
Yeni sektör: `sektorler/` içine yeni bir JSON koy (örnek: `araclar/sektor_paketleri_uret.py`).

## Yeni müşteri ekleme (≈30 dk)

1. Panel → **+ Yeni şirket** → sektörü seç, adı yaz. Sektörün örnek işletmesinden dolu bir dosya oluşur.
2. **İşletme bilgileri** sekmesinde müşterinin gerçek fiyatlarını, saatlerini, adresini, SSS'lerini yaz → Kaydet.
3. `randevu.kapasite`: aynı saatte kaç randevu alınabilir (koltuk/masa/usta sayısı). `randevu.aktif: false` → sadece soru-cevap.
4. Bot müşteriye yazdığı dilde cevap verir (Türkçe yazana her zaman Türkçe).
5. `yetkili.telegram_chat_id`: işletme sahibinin Telegram chat id'si (bildirimler buraya gelir).
5. Demo ekranından dene, sonra WhatsApp numarasını bağla (aşağıda).

## WhatsApp'a bağlama (Meta WhatsApp Cloud API)

Gereken: WhatsApp'ta **kullanılmayan** bir numara (yeni hat / sabit hat da olur), Facebook hesabı.

1. https://developers.facebook.com → **Uygulama oluştur** → tür: *İşletme* → ürün olarak **WhatsApp** ekle.
2. WhatsApp → *API Kurulumu*: **Telefon numarası ekle** → numarayı SMS/aramayla doğrula.
   Buradaki **Phone number ID**'yi şirket dosyasında `whatsapp.phone_number_id` alanına yaz.
3. Kalıcı token: *İşletme Ayarları → Sistem kullanıcıları* → yönetici kullanıcı → **Token oluştur**
   (izinler: `whatsapp_business_messaging`, `whatsapp_business_management`) → `.env` içinde `WA_TOKEN`.
4. Sunucunun internetten erişilebilir olması gerekir (aşağıdaki "Yayına alma" bölümü).
5. WhatsApp → *Yapılandırma → Webhook*: URL `https://ALAN-ADI/webhook`, doğrulama anahtarı `.env`'deki `WA_VERIFY_TOKEN`
   → **Doğrula ve kaydet** → `messages` alanına abone ol.
6. Uygulama Ayarları → Temel → **Uygulama gizli anahtarı** → `.env` içinde `WA_APP_SECRET` (sahte istekleri engeller).
7. Uygulamayı **Canlı** moda al. Numaraya WhatsApp'tan mesaj at → bot cevaplar.

Ücret: Müşterinin başlattığı sohbete 24 saat içinde verilen cevaplar ücretsiz. İşletmenin kendisinin başlattığı
kampanya/hatırlatma mesajları Meta tarafından ücretlendirilir (bu sürümde yok).

Not: Numara Cloud API'ye bağlanınca o numara artık telefondaki WhatsApp uygulamasında kullanılamaz;
yetkili müşterilere panelden yazar ("Sohbeti devral" ile bot susar).

## Yayına alma (7/24)

Bilgisayar kapalıyken de çalışması için bir sunucuya koy (Render / Railway / Hugging Face Spaces / VPS).
Başlatma komutu: `gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT app:app`
(`-w 1` önemli: mesaj birleştirme zamanlayıcıları tek süreçte tutulur.) `veri/` klasörü kalıcı disk olmalı.
Hızlı yerel deneme için: `cloudflared tunnel --url http://localhost:5080` → çıkan https adresini webhook'a yaz.

## Test

`python araclar/test_sohbet.py demo-dis-klinigi` — senaryolu konuşma, yapılan işlemler ve oluşan randevular.
