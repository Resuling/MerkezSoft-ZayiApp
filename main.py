from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib

app = FastAPI()

# MerkezSoft Bulut Veritabanı (PostgreSQL) Bağlantısı
DATABASE_URL = "postgresql://resulbilgic_user:g7YU2B2nZWNt7reE5kC2I3XcgkxZU36B@dpg-da0pghtg1s2s73c5hgcg-a/resulbilgic"

def get_db_connection():
    # PostgreSQL'e bağlan ve verileri sözlük (dict) formatında getir
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def veritabani_kurulumu():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # KULLANICILAR TABLOSU
    cursor.execute('''CREATE TABLE IF NOT EXISTS kullanicilar (kullanici_adi TEXT PRIMARY KEY, sifre TEXT, firma_kodu TEXT)''')
    
    # ÜRÜNLER TABLOSU (PostgreSQL'de ID için SERIAL kullanılır)
    cursor.execute('''CREATE TABLE IF NOT EXISTS urunler (id SERIAL PRIMARY KEY, barkod TEXT, firma_kodu TEXT, marka TEXT, isim TEXT, stok_adedi INTEGER, skt TEXT, kategori TEXT, sube TEXT)''')
    
    # ZAYİ GEÇMİŞİ TABLOSU
    cursor.execute('''CREATE TABLE IF NOT EXISTS zayi_gecmisi (id SERIAL PRIMARY KEY, firma_kodu TEXT, tarih TEXT, barkod TEXT, marka TEXT, isim TEXT, zayi_miktari INTEGER, sebep TEXT)''')
    
    # FIRSAT REYONU TABLOSU
    cursor.execute('''CREATE TABLE IF NOT EXISTS firsat_reyonu (id SERIAL PRIMARY KEY, firma_kodu TEXT, barkod TEXT, marka TEXT, isim TEXT, kategori TEXT, stok_adedi INTEGER, indirimli_fiyat REAL, indirime_girdigi_tarih TEXT)''')
    
    conn.commit()
    cursor.close()
    conn.close()

# Uygulama başlarken tabloları kontrol et/oluştur
try:
    veritabani_kurulumu()
except Exception as e:
    print("Veritabanı bağlantı hatası:", e)

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
    conn = get_db_connection()
    cursor = conn.cursor()
    hashli_sifre = sifre_hashle(kul.sifre)
    try:
        # PostgreSQL'de parametreler %s ile belirtilir
        cursor.execute('INSERT INTO kullanicilar (kullanici_adi, sifre, firma_kodu) VALUES (%s, %s, %s)', (kul.kullanici_adi, hashli_sifre, kul.firma_kodu))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten alınmış!")
    cursor.close()
    conn.close()
    return {"mesaj": "Kayıt başarılı"}

@app.post("/giris/")
def kullanici_giris(kul: Kullanici):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashli_sifre = sifre_hashle(kul.sifre)
    cursor.execute('SELECT firma_kodu FROM kullanicilar WHERE kullanici_adi = %s AND sifre = %s', (kul.kullanici_adi, hashli_sifre))
    kullanici = cursor.fetchone()
    cursor.close()
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE firma_kodu = %s ORDER BY id DESC", (firma_kodu,))
    urunler = cursor.fetchall()
    cursor.close()
    conn.close()
    return urunler

@app.post("/urun-ekle/")
def urun_ekle(urun: Urun):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # A firması kendi içinde bu barkodu eklemiş mi kontrolü
    cursor.execute("SELECT * FROM urunler WHERE barkod = %s AND firma_kodu = %s", (urun.barkod, urun.firma_kodu))
    mevcut_urun = cursor.fetchone()
    
    if mevcut_urun:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Bu ürün firmanızda zaten kayıtlı!")
    else:
        cursor.execute('INSERT INTO urunler (barkod, firma_kodu, marka, isim, stok_adedi, skt, kategori, sube) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (urun.barkod, urun.firma_kodu, urun.marka, urun.isim, urun.stok_adedi, urun.skt, urun.kategori, urun.sube))
        conn.commit()
    
    cursor.close()
    conn.close()
    return {"mesaj": "Ürün eklendi"}

@app.put("/stok-guncelle/{firma_kodu}/{barkod}")
def stok_guncelle(firma_kodu: str, barkod: str, yeni_stok: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE urunler SET stok_adedi = %s WHERE barkod = %s AND firma_kodu = %s", (yeni_stok, barkod, firma_kodu))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mesaj": "Stok güncellendi."}

@app.delete("/urun-zayi-bildir/{firma_kodu}/{barkod}")
def zayi_bildir(firma_kodu: str, barkod: str, sebep: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE barkod = %s AND firma_kodu = %s", (barkod, firma_kodu))
    urun = cursor.fetchone()
    if urun:
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO zayi_gecmisi (firma_kodu, tarih, barkod, marka, isim, zayi_miktari, sebep) VALUES (%s, %s, %s, %s, %s, %s, %s)', (firma_kodu, zaman, urun["barkod"], urun["marka"], urun["isim"], urun["stok_adedi"], sebep))
        cursor.execute("DELETE FROM urunler WHERE barkod = %s AND firma_kodu = %s", (barkod, firma_kodu))
        conn.commit()
    cursor.close()
    conn.close()
    return {"mesaj": "Zayi bildirildi."}

@app.get("/zayi-gecmisi/{firma_kodu}")
def zayi_gecmisini_getir(firma_kodu: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zayi_gecmisi WHERE firma_kodu = %s ORDER BY id DESC", (firma_kodu,))
    gecmis = cursor.fetchall()
    cursor.close()
    conn.close()
    return gecmis

@app.post("/firsat-reyonuna-al/{firma_kodu}/{barkod}")
def firsat_reyonuna_al(firma_kodu: str, barkod: str, yeni_fiyat: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE barkod = %s AND firma_kodu = %s", (barkod, firma_kodu))
    urun = cursor.fetchone()
    if urun:
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO firsat_reyonu (firma_kodu, barkod, marka, isim, kategori, stok_adedi, indirimli_fiyat, indirime_girdigi_tarih) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (firma_kodu, urun["barkod"], urun["marka"], urun["isim"], urun["kategori"], urun["stok_adedi"], yeni_fiyat, zaman))
        cursor.execute("DELETE FROM urunler WHERE barkod = %s AND firma_kodu = %s", (barkod, firma_kodu))
        conn.commit()
    cursor.close()
    conn.close()
    return {"mesaj": "Fırsata alındı."}

@app.get("/firsat-reyonu/{firma_kodu}")
def firsat_reyonunu_getir(firma_kodu: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM firsat_reyonu WHERE firma_kodu = %s ORDER BY id DESC", (firma_kodu,))
    firsatlar = cursor.fetchall()
    cursor.close()
    conn.close()
    return firsatlar

@app.get("/manifest.json")
def get_manifest(): return FileResponse("manifest.json")
@app.get("/sw.js")
def get_sw(): return FileResponse("sw.js")
