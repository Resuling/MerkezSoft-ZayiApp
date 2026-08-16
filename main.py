from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import hashlib
import os

app = FastAPI()

# DİKKAT: ESKİ SORUNLU VERİTABANINI KALICI OLARAK SİLİYORUZ
if os.path.exists("zayiapp.db"):
    try:
        os.remove("zayiapp.db")
    except:
        pass

def get_db():
    conn = sqlite3.connect("zayiapp.db")
    conn.row_factory = sqlite3.Row  
    return conn

def veritabani_kurulumu():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS kullanicilar (kullanici_adi TEXT PRIMARY KEY, sifre TEXT, firma_kodu TEXT)''')
    
    # ÇÖZÜM BURADA: PRIMARY KEY artık 'id', böylece farklı firmalar aynı barkodu sorunsuzca ekleyebilir!
    cursor.execute('''CREATE TABLE IF NOT EXISTS urunler (id INTEGER PRIMARY KEY AUTOINCREMENT, barkod TEXT, firma_kodu TEXT, marka TEXT, isim TEXT, stok_adedi INTEGER, skt TEXT, kategori TEXT, sube TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS zayi_gecmisi (id INTEGER PRIMARY KEY AUTOINCREMENT, firma_kodu TEXT, tarih TEXT, barkod TEXT, marka TEXT, isim TEXT, zayi_miktari INTEGER, sebep TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS firsat_reyonu (id INTEGER PRIMARY KEY AUTOINCREMENT, firma_kodu TEXT, barkod TEXT, marka TEXT, isim TEXT, kategori TEXT, stok_adedi INTEGER, indirimli_fiyat REAL, indirime_girdigi_tarih TEXT)''')
    
    conn.commit()
    conn.close()

veritabani_kurulumu()

def sifre_hashle(sifre: str):
    return hashlib.sha256(sifre.encode()).hexdigest()

class Kullanici(BaseModel):
    kullanici_adi: str
    sifre: str
    firma_kodu: str = None

class Urun(BaseModel):
    barkod: str
    firma_kodu: str 
    marka: str
    isim: str
    stok_adedi: int
    skt: str
    kategori: str
    sube: str

@app.post("/kayit/")
def kullanici_kayit(kul: Kullanici):
    if not kul.firma_kodu:
        raise HTTPException(status_code=400, detail="Firma kodu zorunludur!")
    conn = get_db()
    cursor = conn.cursor()
    hashli_sifre = sifre_hashle(kul.sifre)
    try:
        cursor.execute('INSERT INTO kullanicilar (kullanici_adi, sifre, firma_kodu) VALUES (?, ?, ?)', (kul.kullanici_adi, hashli_sifre, kul.firma_kodu))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten alınmış!")
    conn.close()
    return {"mesaj": "Kayıt başarılı"}

@app.post("/giris/")
def kullanici_giris(kul: Kullanici):
    conn = get_db()
    cursor = conn.cursor()
    hashli_sifre = sifre_hashle(kul.sifre)
    cursor.execute('SELECT firma_kodu FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?', (kul.kullanici_adi, hashli_sifre))
    kullanici = cursor.fetchone()
    conn.close()
    if kullanici:
        return {"mesaj": "Giriş başarılı", "firma_kodu": kullanici["firma_kodu"], "kullanici_adi": kul.kullanici_adi}
    else:
        raise HTTPException(status_code=401, detail="Hatalı kullanıcı adı veya şifre!")

@app.get("/")
def ana_sayfa(): 
    return FileResponse("index.html")

@app.get("/app")
def uygulama_sayfasi(): 
    return FileResponse("app.html")

@app.get("/urunler/{firma_kodu}")
def urunleri_getir(firma_kodu: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE firma_kodu = ?", (firma_kodu,))
    urunler = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return urunler

@app.post("/urun-ekle/")
def urun_ekle(urun: Urun):
    conn = get_db()
    cursor = conn.cursor()
    
    # AYNI FİRMANIN AYNI BARKODU 2 KERE EKLEMESİNİ ENGELLE
    cursor.execute("SELECT * FROM urunler WHERE barkod = ? AND firma_kodu = ?", (urun.barkod, urun.firma_kodu))
    mevcut_urun = cursor.fetchone()
    
    if mevcut_urun:
        conn.close()
        raise HTTPException(status_code=400, detail="Bu ürün firmanızda zaten kayıtlı!")
    else:
        cursor.execute('INSERT INTO urunler (barkod, firma_kodu, marka, isim, stok_adedi, skt, kategori, sube) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (urun.barkod, urun.firma_kodu, urun.marka, urun.isim, urun.stok_adedi, urun.skt, urun.kategori, urun.sube))
        conn.commit()
    
    conn.close()
    return {"mesaj": "Ürün eklendi"}

@app.put("/stok-guncelle/{firma_kodu}/{barkod}")
def stok_guncelle(firma_kodu: str, barkod: str, yeni_stok: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE urunler SET stok_adedi = ? WHERE barkod = ? AND firma_kodu = ?", (yeni_stok, barkod, firma_kodu))
    conn.commit()
    conn.close()
    return {"mesaj": "Stok güncellendi."}

@app.delete("/urun-zayi-bildir/{firma_kodu}/{barkod}")
def zayi_bildir(firma_kodu: str, barkod: str, sebep: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE barkod = ? AND firma_kodu = ?", (barkod, firma_kodu))
    urun = cursor.fetchone()
    if urun:
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO zayi_gecmisi (firma_kodu, tarih, barkod, marka, isim, zayi_miktari, sebep) VALUES (?, ?, ?, ?, ?, ?, ?)', (firma_kodu, zaman, urun["barkod"], urun["marka"], urun["isim"], urun["stok_adedi"], sebep))
        cursor.execute("DELETE FROM urunler WHERE barkod = ? AND firma_kodu = ?", (barkod, firma_kodu))
        conn.commit()
    conn.close()
    return {"mesaj": "Zayi bildirildi."}

@app.get("/zayi-gecmisi/{firma_kodu}")
def zayi_gecmisini_getir(firma_kodu: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zayi_gecmisi WHERE firma_kodu = ? ORDER BY id DESC", (firma_kodu,))
    gecmis = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return gecmis

@app.post("/firsat-reyonuna-al/{firma_kodu}/{barkod}")
def firsat_reyonuna_al(firma_kodu: str, barkod: str, yeni_fiyat: float):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE barkod = ? AND firma_kodu = ?", (barkod, firma_kodu))
    urun = cursor.fetchone()
    if urun:
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO firsat_reyonu (firma_kodu, barkod, marka, isim, kategori, stok_adedi, indirimli_fiyat, indirime_girdigi_tarih) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (firma_kodu, urun["barkod"], urun["marka"], urun["isim"], urun["kategori"], urun["stok_adedi"], yeni_fiyat, zaman))
        cursor.execute("DELETE FROM urunler WHERE barkod = ? AND firma_kodu = ?", (barkod, firma_kodu))
        conn.commit()
    conn.close()
    return {"mesaj": "Fırsata alındı."}

@app.get("/firsat-reyonu/{firma_kodu}")
def firsat_reyonunu_getir(firma_kodu: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM firsat_reyonu WHERE firma_kodu = ? ORDER BY id DESC", (firma_kodu,))
    firsatlar = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return firsatlar

@app.get("/manifest.json")
def get_manifest(): return FileResponse("manifest.json")
@app.get("/sw.js")
def get_sw(): return FileResponse("sw.js")
