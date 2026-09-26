from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import pymysql
import os
from typing import Optional
from dotenv import load_dotenv

# Load kredensial dari .env (lokal) atau Environment Variables (Render)
load_dotenv()

app = FastAPI(title="SmartKeu API Backend")

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 4000)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

# --------------------------
# SCHEMAS (PAYLOAD MODEL)
# --------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

class PegawaiModel(BaseModel):
    nip: str
    nama: str
    status_kepegawaian: str
    pangkat: str
    golongan: str
    tingkat_perjadin: str

# --------------------------
# ENDPOINT TEST ROOT
# --------------------------
@app.get("/")
def root():
    return {"status": "success", "message": "SmartKeu API is running!"}

# --------------------------
# ENDPOINT DEBUG USERS
# --------------------------
@app.get("/api/check-users")
def check_users():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username, password, role FROM users")
            return cursor.fetchall()
    finally:
        connection.close()

# --------------------------
# ENDPOINT RESET PASSWORD
# --------------------------
@app.get("/api/reset-pass-superadmin")
def reset_pass_superadmin():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET password = %s WHERE username = 'SuperAdmin'", ("Radeon56809!",))
            connection.commit()
            return {"status": "success", "message": "Password SuperAdmin berhasil diubah menjadi Radeon56809!"}
    finally:
        connection.close()
        
# --------------------------
# ENDPOINT LOGIN
# --------------------------
@app.post("/api/login")
def login(request: LoginRequest):
    connection = get_db_connection()
    try:
        clean_user = request.username.strip()
        clean_pass = request.password.strip()

        with connection.cursor() as cursor:
            # Menggunakan BINARY agar 'SuperAdmin' dan 'superadmin' dianggap 2 username berbeda
            cursor.execute("SELECT * FROM users WHERE BINARY username = %s LIMIT 1", (clean_user,))
            user_data = cursor.fetchone()

        if not user_data:
            raise HTTPException(status_code=401, detail="Username atau Password salah")

        # Perbandingan password persis (case-sensitive)
        db_password = str(user_data.get("password", "")).strip()
        
        if clean_pass == db_password:
            return {"status": "success", "user": user_data}
        else:
            raise HTTPException(status_code=401, detail="Username atau Password salah")
    finally:
        connection.close()

# --------------------------
# ENDPOINT PEGAWAI
# --------------------------
@app.get("/api/pegawai")
def get_pegawai(status: Optional[str] = Query(None)):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if status and status != "Semua Pegawai":
                cursor.execute("SELECT * FROM pegawai WHERE status_kepegawaian = %s ORDER BY nama ASC", (status,))
            else:
                cursor.execute("SELECT * FROM pegawai ORDER BY nama ASC")
            pegawai_list = cursor.fetchall()
            return {"status": "success", "data": pegawai_list}
    finally:
        connection.close()

@app.post("/api/pegawai")
def tambah_pegawai(pegawai: PegawaiModel):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT nip FROM pegawai WHERE nip = %s", (pegawai.nip,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"NIP {pegawai.nip} sudah terdaftar!")

            cursor.execute("""
                INSERT INTO pegawai (nip, nama, status_kepegawaian, pangkat, golongan, tingkat_perjadin)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (pegawai.nip, pegawai.nama, pegawai.status_kepegawaian, pegawai.pangkat, pegawai.golongan, pegawai.tingkat_perjadin))
            connection.commit()
            return {"status": "success", "message": "Pegawai berhasil ditambahkan"}
    finally:
        connection.close()

@app.put("/api/pegawai/{nip_lama}")
def update_pegawai(nip_lama: str, pegawai: PegawaiModel):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if pegawai.nip != nip_lama:
                cursor.execute("SELECT nip FROM pegawai WHERE nip = %s", (pegawai.nip,))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"NIP {pegawai.nip} sudah terdaftar!")
                
                cursor.execute("""
                    INSERT INTO pegawai (nip, nama, status_kepegawaian, pangkat, golongan, tingkat_perjadin)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (pegawai.nip, pegawai.nama, pegawai.status_kepegawaian, pegawai.pangkat, pegawai.golongan, pegawai.tingkat_perjadin))
                cursor.execute("DELETE FROM pegawai WHERE nip = %s", (nip_lama,))
            else:
                cursor.execute("""
                    UPDATE pegawai SET nama = %s, status_kepegawaian = %s, pangkat = %s, golongan = %s, tingkat_perjadin = %s
                    WHERE nip = %s
                """, (pegawai.nama, pegawai.status_kepegawaian, pegawai.pangkat, pegawai.golongan, pegawai.tingkat_perjadin, nip_lama))
            connection.commit()
            return {"status": "success", "message": "Data pegawai diperbarui"}
    finally:
        connection.close()

@app.delete("/api/pegawai/{nip}")
def hapus_pegawai(nip: str):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM pegawai WHERE nip = %s", (nip,))
            connection.commit()
            return {"status": "success", "message": "Pegawai berhasil dihapus"}
    finally:
        connection.close()