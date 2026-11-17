"""Şirket bilgi dosyaları ve sektör paketleri."""
import json

from .ayarlar import SEKTOR_KLASORU, SIRKET_KLASORU

SIRKET_KLASORU.mkdir(exist_ok=True)


def _json(yol):
    return json.loads(yol.read_text(encoding="utf-8"))


def sektorler() -> dict:
    return {p.stem: _json(p) for p in sorted(SEKTOR_KLASORU.glob("*.json"))}


def sektor(ad) -> dict:
    yol = SEKTOR_KLASORU / f"{ad}.json"
    return _json(yol) if yol.exists() else _json(SEKTOR_KLASORU / "genel.json")


def sirket(sid) -> dict | None:
    yol = SIRKET_KLASORU / f"{sid}.json"
    return _json(yol) if yol.exists() else None


def tum_sirketler() -> list[dict]:
    return [_json(p) for p in sorted(SIRKET_KLASORU.glob("*.json"))]


def sirket_kaydet(veri: dict):
    if not veri.get("id"):
        raise ValueError("Şirketin 'id' alanı boş olamaz")
    yol = SIRKET_KLASORU / f"{veri['id']}.json"
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")


def numaradan_sirket(phone_number_id) -> dict | None:
    """WhatsApp'ın gönderdiği phone_number_id hangi şirkete ait?"""
    for s in tum_sirketler():
        if str(s.get("whatsapp", {}).get("phone_number_id", "")) == str(phone_number_id):
            return s
    return None


def sektor_sablonundan_sirket(sektor_adi, sid, ad=None) -> dict:
    """Sektör paketindeki örnek işletmeden yeni şirket dosyası üretir."""
    veri = json.loads(json.dumps(sektor(sektor_adi)["ornek_sirket"]))
    veri["id"] = sid
    veri["sektor"] = sektor_adi
    if ad:
        veri["ad"] = ad
    sirket_kaydet(veri)
    return veri


def demo_sirketleri_hazirla():
    """Her sektör paketi için bir demo şirket yoksa oluştur (satış sunumu için)."""
    for adi, paket in sektorler().items():
        if adi == "genel" or "ornek_sirket" not in paket:
            continue
        sid = f"demo-{adi.replace('_', '-')}"
        if not (SIRKET_KLASORU / f"{sid}.json").exists():
            veri = sektor_sablonundan_sirket(adi, sid)
            veri["demo"] = True
            sirket_kaydet(veri)
