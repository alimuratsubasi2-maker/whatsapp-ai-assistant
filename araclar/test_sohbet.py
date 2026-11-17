"""Senaryolu konuşma testi: python araclar/test_sohbet.py [sirket_id]"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")
from motor import akis, veritabani as db
from motor.sirketler import demo_sirketleri_hazirla

demo_sirketleri_hazirla()
SENARYO = {
    "demo-dis-klinigi": ["Merhaba", "diş taşı temizliği ne kadar", "yarın öğleden sonra için randevu alabilir miyim",
                         "ilk uygun saat olsun", "Ayşe Yılmaz, diş etlerim kanıyor", "evet onaylıyorum", "teşekkürler"],
    "demo-restoran-kafe": ["selam cumartesi akşam 8de 5 kişilik masa var mı", "adım Murat Kaya, doğum günü için", "evet", "vegan yemek var mı"],
    "novadijitaltr": ["Merhaba kuaför salonum var, whatsapp otomasyonu nasıl çalışıyor?", "fiyatı ne kadar?", "web sitesi de lazım ne kadar tutar"],
}
sid = sys.argv[1] if len(sys.argv) > 1 else "demo-dis-klinigi"
musteri = f"test-{int(time.time())}"
for m in SENARYO.get(sid, ["Merhaba", "Fiyatlarınız nedir?", "Randevu almak istiyorum"]):
    print(f"\n👤 {m}")
    t = time.time()
    print(f"🤖 {akis.demo_mesaj(sid, musteri, m)}   ({time.time()-t:.1f} sn)")
print("\n--- sistem kayıtları ---")
for k in db.son_mesajlar(sid, musteri, 100):
    if k["rol"] == "sistem":
        print("⚙️", k["metin"][:300])
print("Randevular:", db.musteri_randevulari(sid, musteri))
