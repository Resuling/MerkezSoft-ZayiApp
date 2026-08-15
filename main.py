from fastapi import FastAPI, HTTPException
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
    # Her tablodaki veriyi sube_id ile ayırıyoruz
    cursor.execute('''CREATE TABLE IF NOT EXISTS urunler (barkod TEXT, sube_id TEXT, marka TEXT, isim TEXT, stok_adedi INTEGER, skt TEXT, kategori TEXT, PRIMARY KEY(barkod, sube_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS zayi_gecmisi (id INTEGER PRIMARY KEY AUTOINCREMENT, sube_id TEXT, tarih TEXT, barkod TEXT, marka TEXT, isim TEXT, zayi_miktari INTEGER, sebep TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS firsat_reyonu (id INTEGER PRIMARY KEY AUTOINCREMENT, sube_id TEXT, barkod TEXT, marka TEXT, isim TEXT, kategori TEXT, stok_adedi INTEGER, indirimli_fiyat REAL, indirime_girdigi_tarih TEXT)''')
    conn.commit()
    conn.close()

veritabani_kurulumu()

class Urun(BaseModel):
    barkod: str
    sube_id: str
    marka: str
    isim: str
    stok_adedi: int
    skt: str
    kategori: str

@app.get("/")
def ana_sayfa(): return FileResponse("index.html")

@app.get("/urunler/{sube_id}")
def urunleri_getir(sube_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE sube_id = ?", (sube_id,))
    urunler = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return urunler

@app.post("/urun-ekle/")
def urun_ekle(urun: Urun):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO urunler VALUES (?, ?, ?, ?, ?, ?, ?)', (urun.barkod, urun.sube_id, urun.marka, urun.isim, urun.stok_adedi, urun.skt, urun.kategori))
    conn.commit()
    conn.close()
    return {"mesaj": "Başarılı"}

@app.delete("/urun-zayi-bildir/{sube_id}/{barkod}")
def zayi_bildir(sube_id: str, barkod: str, sebep: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE barkod = ? AND sube_id = ?", (barkod, sube_id))
    urun = cursor.fetchone()
    if urun:
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO zayi_gecmisi (sube_id, tarih, barkod, marka, isim, zayi_miktari, sebep) VALUES (?, ?, ?, ?, ?, ?, ?)', (sube_id, zaman, urun["barkod"], urun["marka"], urun["isim"], urun["stok_adedi"], sebep))
        cursor.execute("DELETE FROM urunler WHERE barkod = ? AND sube_id = ?", (barkod, sube_id))
        conn.commit()
    conn.close()
    return {"mesaj": "Zayi bildirildi"}

@app.get("/zayi-gecmisi/{sube_id}")
def zayi_gecmisini_getir(sube_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zayi_gecmisi WHERE sube_id = ? ORDER BY id DESC", (sube_id,))
    gecmis = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return gecmis

@app.post("/firsat-reyonuna-al/{sube_id}/{barkod}")
def firsat_reyonuna_al(sube_id: str, barkod: str, yeni_fiyat: float):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE barkod = ? AND sube_id = ?", (barkod, sube_id))
    urun = cursor.fetchone()
    if urun:
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO firsat_reyonu (sube_id, barkod, marka, isim, kategori, stok_adedi, indirimli_fiyat, indirime_girdigi_tarih) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (sube_id, urun["barkod"], urun["marka"], urun["isim"], urun["kategori"], urun["stok_adedi"], yeni_fiyat, zaman))
        cursor.execute("DELETE FROM urunler WHERE barkod = ? AND sube_id = ?", (barkod, sube_id))
        conn.commit()
    conn.close()
    return {"mesaj": "Fırsata alındı"}

@app.get("/firsat-reyonu/{sube_id}")
def firsat_reyonunu_getir(sube_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM firsat_reyonu WHERE sube_id = ? ORDER BY id DESC", (sube_id,))
    firsatlar = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return firsatlar

@app.get("/manifest.json")
def get_manifest(): return FileResponse("manifest.json")
@app.get("/sw.js")
def get_sw(): return FileResponse("sw.js")
