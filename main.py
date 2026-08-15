from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import sqlite3

app = FastAPI()

def get_db():
    conn = sqlite3.connect("zayiapp.db")
    conn.row_factory = sqlite3.Row  
    return conn

def veritabani_kurulumu():
    conn = get_db()
    cursor = conn.cursor()
    
    # YENİ EKLENEN: marka sütunu eklendi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urunler (
            barkod TEXT PRIMARY KEY,
            marka TEXT,
            isim TEXT,
            stok_adedi INTEGER,
            skt TEXT,
            kategori TEXT,
            sube TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zayi_gecmisi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            barkod TEXT,
            marka TEXT,
            isim TEXT,
            zayi_miktari INTEGER,
            sebep TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS firsat_reyonu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            marka TEXT,
            isim TEXT,
            kategori TEXT,
            stok_adedi INTEGER,
            indirimli_fiyat REAL,
            indirime_girdigi_tarih TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

veritabani_kurulumu()

# YENİ EKLENEN: marka alanı eklendi
class Urun(BaseModel):
    barkod: str
    marka: str
    isim: str
    stok_adedi: int
    skt: str
    kategori: str
    sube: str

@app.get("/")
def ana_sayfa():
    return FileResponse("index.html")

@app.get("/urunler/")
def urunleri_getir():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler")
    urunler = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return urunler

@app.post("/urun-ekle/")
def urun_ekle(urun: Urun):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # YENİ EKLENEN: marka veritabanına yazılıyor
        cursor.execute('''
            INSERT INTO urunler (barkod, marka, isim, stok_adedi, skt, kategori, sube) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (urun.barkod, urun.marka, urun.isim, urun.stok_adedi, urun.skt, urun.kategori, urun.sube))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Bu barkoda sahip bir ürün zaten rafta var!")
    
    conn.close()
    return {"mesaj": "Ürün başarıyla eklendi", "urun": urun}

@app.put("/stok-guncelle/{barkod}")
def stok_guncelle(barkod: str, yeni_stok: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE urunler SET stok_adedi = ? WHERE barkod = ?", (yeni_stok, barkod))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    conn.commit()
    conn.close()
    return {"mesaj": "Stok güncellendi."}

@app.delete("/urun-zayi-bildir/{barkod}")
def zayi_bildir(barkod: str, sebep: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE barkod = ?", (barkod,))
    urun = cursor.fetchone()
    if not urun:
        conn.close()
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # YENİ EKLENEN: marka arşiv tablosuna da ekleniyor
    cursor.execute('''
        INSERT INTO zayi_gecmisi (tarih, barkod, marka, isim, zayi_miktari, sebep)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (zaman, urun["barkod"], urun["marka"], urun["isim"], urun["stok_adedi"], sebep))
    
    cursor.execute("DELETE FROM urunler WHERE barkod = ?", (barkod,))
    conn.commit()
    conn.close()
    return {"mesaj": "Ürün zayi arşivine gönderildi."}

@app.get("/zayi-gecmisi/")
def zayi_gecmisini_getir():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zayi_gecmisi ORDER BY id DESC")
    gecmis = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return gecmis

@app.post("/firsat-reyonuna-al/{barkod}")
def firsat_reyonuna_al(barkod: str, yeni_fiyat: float):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE barkod = ?", (barkod,))
    urun = cursor.fetchone()
    
    if not urun:
        conn.close()
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # YENİ EKLENEN: marka fırsat reyonu tablosuna da ekleniyor
    cursor.execute('''
        INSERT INTO firsat_reyonu (barkod, marka, isim, kategori, stok_adedi, indirimli_fiyat, indirime_girdigi_tarih)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (urun["barkod"], urun["marka"], urun["isim"], urun["kategori"], urun["stok_adedi"], yeni_fiyat, zaman))
    
    cursor.execute("DELETE FROM urunler WHERE barkod = ?", (barkod,))
    conn.commit()
    conn.close()
    return {"mesaj": "Ürün fırsat reyonuna taşındı."}

@app.get("/firsat-reyonu/")
def firsat_reyonunu_getir():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM firsat_reyonu ORDER BY id DESC")
    firsatlar = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return firsatlar