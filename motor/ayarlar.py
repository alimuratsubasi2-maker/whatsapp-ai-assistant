"""Ortak ayarlar: .env yükleme, SSL düzeltmesi, saat dilimi."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Avast HTTPS taraması Python'un certifi'sini bozuyor -> Windows sertifika deposunu kullan
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

from dotenv import load_dotenv

KOK = Path(__file__).resolve().parent.parent
load_dotenv(KOK / ".env")

SEKTOR_KLASORU = KOK / "sektorler"
SIRKET_KLASORU = KOK / "sirketler"
VERI_KLASORU = KOK / "veri"
VERI_KLASORU.mkdir(exist_ok=True)
VERITABANI = VERI_KLASORU / "otomasyon.db"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODELLER = [m.strip() for m in os.getenv(
    "GEMINI_MODELLER", "gemini-3.5-flash-lite,gemini-flash-lite-latest,gemini-3.1-flash-lite").split(",") if m.strip()]

WA_TOKEN = os.getenv("WA_TOKEN", "")              # Meta kalıcı erişim anahtarı
WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "nova-dogrulama")
WA_APP_SECRET = os.getenv("WA_APP_SECRET", "")    # varsa webhook imzası doğrulanır
WA_API_SURUM = os.getenv("WA_API_SURUM", "v21.0")

# Ücretsiz katmanda Google gönderilen içeriği ürün geliştirmede kullanabilir (KVKK riski)
GEMINI_UCRETLI = os.getenv("GEMINI_UCRETLI", "0") == "1"

# Sunucunun internetteki adresi (aydınlatma metni linki için), örn. https://bot.novadijitaltr.com
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
# Şirket dosyasında kvkk.saklama_gun yoksa: eski sohbet ve randevular kaç gün sonra silinsin
VARSAYILAN_SAKLAMA_GUN = int(os.getenv("SAKLAMA_GUN", "180"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PANEL_SIFRE = os.getenv("PANEL_SIFRE") or secrets.token_urlsafe(12)  # .env'de yoksa her açılışta rastgele üretilir
if not os.getenv("PANEL_SIFRE"):
    print(f"[UYARI] PANEL_SIFRE tanımlı değil. Bu oturumun panel şifresi: {PANEL_SIFRE}")
PORT = int(os.getenv("PORT", "5080"))

# Gelen mesajları birleştirme süresi (müşteri art arda yazınca tek cevap)
BEKLEME_SN = float(os.getenv("BEKLEME_SN", "4"))

TR = timezone(timedelta(hours=3))  # Türkiye yaz/kış saati uygulamıyor


def simdi() -> datetime:
    return datetime.now(TR).replace(tzinfo=None)


GUNLER = ["pzt", "sal", "car", "per", "cum", "cmt", "paz"]
GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
