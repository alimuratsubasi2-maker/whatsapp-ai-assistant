"""SQLite: mesajlar, sohbetler, randevular."""
import sqlite3
import threading
from datetime import timedelta

from .ayarlar import VERITABANI, simdi

_kilit = threading.RLock()
_baglanti = sqlite3.connect(VERITABANI, check_same_thread=False)
_baglanti.row_factory = sqlite3.Row

_baglanti.executescript("""
CREATE TABLE IF NOT EXISTS mesajlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sirket_id TEXT, musteri TEXT, rol TEXT, metin TEXT, zaman TEXT
);
CREATE INDEX IF NOT EXISTS ix_mesaj ON mesajlar(sirket_id, musteri, id);
CREATE TABLE IF NOT EXISTS sohbetler (
    sirket_id TEXT, musteri TEXT, ad TEXT, kanal TEXT,
    insan_modu INTEGER DEFAULT 0, son_zaman TEXT, son_metin TEXT,
    PRIMARY KEY (sirket_id, musteri)
);
CREATE TABLE IF NOT EXISTS randevular (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sirket_id TEXT, musteri TEXT, ad TEXT, hizmet TEXT,
    baslangic TEXT, bitis TEXT, kisi_sayisi INTEGER DEFAULT 1,
    notlar TEXT, durum TEXT DEFAULT 'onayli', olusturma TEXT
);
CREATE INDEX IF NOT EXISTS ix_randevu ON randevular(sirket_id, baslangic);
CREATE TABLE IF NOT EXISTS islenen_mesajlar (wa_id TEXT PRIMARY KEY, zaman TEXT);
""")
_baglanti.commit()


def _yaz(sql, args=()):
    with _kilit:
        cur = _baglanti.execute(sql, args)
        _baglanti.commit()
        return cur.lastrowid


def _oku(sql, args=()):
    with _kilit:
        return [dict(r) for r in _baglanti.execute(sql, args).fetchall()]


# ---- mesajlar / sohbetler ----

def mesaj_ekle(sirket_id, musteri, rol, metin, kanal=None, ad=None):
    z = simdi().strftime("%Y-%m-%d %H:%M:%S")
    mid = _yaz("INSERT INTO mesajlar(sirket_id,musteri,rol,metin,zaman) VALUES(?,?,?,?,?)",
               (sirket_id, musteri, rol, metin, z))
    _yaz("""INSERT INTO sohbetler(sirket_id,musteri,ad,kanal,son_zaman,son_metin) VALUES(?,?,?,?,?,?)
            ON CONFLICT(sirket_id,musteri) DO UPDATE SET son_zaman=excluded.son_zaman,
            son_metin=excluded.son_metin, ad=COALESCE(excluded.ad, sohbetler.ad),
            kanal=COALESCE(excluded.kanal, sohbetler.kanal)""",
         (sirket_id, musteri, ad, kanal, z, metin[:200]))
    return mid


def son_mesajlar(sirket_id, musteri, adet=30):
    satirlar = _oku("SELECT * FROM mesajlar WHERE sirket_id=? AND musteri=? ORDER BY id DESC LIMIT ?",
                    (sirket_id, musteri, adet))
    return list(reversed(satirlar))


def mesajlar_sonra(sirket_id, musteri, son_id):
    return _oku("SELECT * FROM mesajlar WHERE sirket_id=? AND musteri=? AND id>? ORDER BY id",
                (sirket_id, musteri, son_id))


def sohbet(sirket_id, musteri):
    r = _oku("SELECT * FROM sohbetler WHERE sirket_id=? AND musteri=?", (sirket_id, musteri))
    return r[0] if r else None


def sohbetler(sirket_id):
    return _oku("SELECT * FROM sohbetler WHERE sirket_id=? ORDER BY son_zaman DESC", (sirket_id,))


def insan_modu_ayarla(sirket_id, musteri, acik: bool):
    _yaz("UPDATE sohbetler SET insan_modu=? WHERE sirket_id=? AND musteri=?",
         (1 if acik else 0, sirket_id, musteri))


def ad_kaydet(sirket_id, musteri, ad):
    if ad:
        _yaz("UPDATE sohbetler SET ad=? WHERE sirket_id=? AND musteri=?", (ad, sirket_id, musteri))


def sohbet_sil(sirket_id, musteri):
    _yaz("DELETE FROM mesajlar WHERE sirket_id=? AND musteri=?", (sirket_id, musteri))
    _yaz("DELETE FROM sohbetler WHERE sirket_id=? AND musteri=?", (sirket_id, musteri))


def bot_mesaj_sayisi(sirket_id, musteri) -> int:
    return _oku("SELECT COUNT(*) AS n FROM mesajlar WHERE sirket_id=? AND musteri=? AND rol='bot'",
                (sirket_id, musteri))[0]["n"]


def musteri_verilerini_sil(sirket_id, musteri):
    """KVKK silme talebi: sohbet, mesajlar ve randevular kalıcı olarak silinir."""
    sohbet_sil(sirket_id, musteri)
    _yaz("DELETE FROM randevular WHERE sirket_id=? AND musteri=?", (sirket_id, musteri))


def eski_kayitlari_sil(sirket_id, gun) -> int:
    """Saklama süresi dolan mesajları, sessiz sohbetleri ve geçmiş randevuları siler."""
    sinir = (simdi() - timedelta(days=gun)).strftime("%Y-%m-%d %H:%M:%S")
    with _kilit:
        n = _baglanti.execute("DELETE FROM mesajlar WHERE sirket_id=? AND zaman<?", (sirket_id, sinir)).rowcount
        _baglanti.execute("DELETE FROM sohbetler WHERE sirket_id=? AND son_zaman<?", (sirket_id, sinir))
        _baglanti.execute("DELETE FROM randevular WHERE sirket_id=? AND bitis<?", (sirket_id, sinir[:16]))
        _baglanti.execute("DELETE FROM islenen_mesajlar WHERE zaman<?", (sinir.replace(" ", "T"),))
        _baglanti.commit()
    return n


def wa_mesaj_islendi_mi(wa_id) -> bool:
    """Meta aynı mesajı tekrar gönderebilir; ikinci kez cevaplamamak için."""
    with _kilit:
        try:
            _baglanti.execute("INSERT INTO islenen_mesajlar VALUES(?,?)", (wa_id, simdi().isoformat()))
            _baglanti.commit()
            return False
        except sqlite3.IntegrityError:
            return True


# ---- randevular ----

def randevu_ekle(sirket_id, musteri, ad, hizmet, baslangic, bitis, kisi_sayisi=1, notlar=""):
    return _yaz("""INSERT INTO randevular(sirket_id,musteri,ad,hizmet,baslangic,bitis,kisi_sayisi,notlar,olusturma)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (sirket_id, musteri, ad, hizmet, baslangic, bitis, kisi_sayisi, notlar,
                 simdi().strftime("%Y-%m-%d %H:%M")))


def randevu(rid):
    r = _oku("SELECT * FROM randevular WHERE id=?", (rid,))
    return r[0] if r else None


def randevu_iptal(rid):
    _yaz("UPDATE randevular SET durum='iptal' WHERE id=?", (rid,))


def gunun_randevulari(sirket_id, tarih):
    return _oku("""SELECT * FROM randevular WHERE sirket_id=? AND durum='onayli'
                   AND substr(baslangic,1,10)=? ORDER BY baslangic""", (sirket_id, tarih))


def musteri_randevulari(sirket_id, musteri, sadece_gelecek=True):
    sql = "SELECT * FROM randevular WHERE sirket_id=? AND musteri=? AND durum='onayli'"
    args = [sirket_id, musteri]
    if sadece_gelecek:
        sql += " AND baslangic>=?"
        args.append(simdi().strftime("%Y-%m-%d %H:%M"))
    return _oku(sql + " ORDER BY baslangic", args)


def randevular(sirket_id, baslangic_tarih=None):
    sql = "SELECT * FROM randevular WHERE sirket_id=?"
    args = [sirket_id]
    if baslangic_tarih:
        sql += " AND baslangic>=?"
        args.append(baslangic_tarih)
    return _oku(sql + " ORDER BY baslangic", args)
