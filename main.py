import os
import json
import pymysql
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="SmartKeu API Disdukcapil")

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"),
        port=int(os.getenv("DB_PORT", 4000)),
        user=os.getenv("DB_USER", "3vYlC1T5sM5qg9e.root"),
        password=os.getenv("DB_PASSWORD", "Radeon56809!"),
        database=os.getenv("DB_NAME", "disdukcapil"),
        ssl={"ca": "/etc/ssl/certs/ca-certificates.crt"} if os.path.exists("/etc/ssl/certs/ca-certificates.crt") else None,
        cursorclass=pymysql.cursors.DictCursor
    )

# --- MODEL DATA (PYDANTIC) ---
class LoginRequest(BaseModel):
    username: str
    password: str

class PegawaiModel(BaseModel):
    nip: str
    nama: str
    status_kepegawaian: str
    pangkat: Optional[str] = ""
    golongan: Optional[str] = ""
    tingkat_perjadin: Optional[str] = ""

class UserModel(BaseModel):
    username: str
    password: str
    role: str

@app.get("/")
def root():
    return {"status": "online", "message": "API SmartKeu Disdukcapil Active"}

# ==========================================
# 1. ENDPOINT AUTHENTICATION
# ==========================================
@app.post("/api/login")
def login(request: LoginRequest):
    connection = get_db_connection()
    try:
        clean_user = request.username.strip()
        clean_pass = request.password.strip()

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE BINARY username = %s LIMIT 1", (clean_user,))
            user_data = cursor.fetchone()

        if not user_data:
            raise HTTPException(status_code=401, detail="Username atau Password salah")

        db_password = str(user_data.get("password", "")).strip()
        if clean_pass == db_password:
            return {"status": "success", "user": user_data}
        else:
            raise HTTPException(status_code=401, detail="Username atau Password salah")
    finally:
        connection.close()

# ==========================================
# 2. ENDPOINT USER MANAGEMENT
# ==========================================
@app.get("/api/users")
def get_users():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username, role FROM users ORDER BY id ASC")
            return {"status": "success", "data": cursor.fetchall()}
    finally:
        connection.close()

@app.post("/api/users")
def tambah_user(user: UserModel):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                           (user.username.strip(), user.password.strip(), user.role.strip()))
            connection.commit()
            return {"status": "success", "message": "User berhasil ditambahkan"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        connection.close()

@app.delete("/api/users/{user_id}")
def hapus_user(user_id: int):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            connection.commit()
            return {"status": "success", "message": "User berhasil dihapus"}
    finally:
        connection.close()

# ==========================================
# 3. ENDPOINT PEGAWAI
# ==========================================
@app.get("/api/pegawai")
def get_pegawai(status: Optional[str] = None):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if status and status != "Semua Pegawai":
                cursor.execute("SELECT * FROM pegawai WHERE status_kepegawaian = %s ORDER BY nama ASC", (status,))
            else:
                cursor.execute("SELECT * FROM pegawai ORDER BY nama ASC")
            return {"status": "success", "data": cursor.fetchall()}
    finally:
        connection.close()

@app.post("/api/pegawai")
def tambah_pegawai(pegawai: PegawaiModel):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO pegawai (nip, nama, status_kepegawaian, pangkat, golongan, tingkat_perjadin)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (pegawai.nip, pegawai.nama, pegawai.status_kepegawaian, pegawai.pangkat, pegawai.golongan, pegawai.tingkat_perjadin))
            connection.commit()
            return {"status": "success", "message": "Pegawai berhasil ditambahkan"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        connection.close()

@app.put("/api/pegawai/{nip_lama}")
def edit_pegawai(nip_lama: str, pegawai: PegawaiModel):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE pegawai 
                SET nip = %s, nama = %s, status_kepegawaian = %s, pangkat = %s, golongan = %s, tingkat_perjadin = %s
                WHERE nip = %s
            """, (pegawai.nip, pegawai.nama, pegawai.status_kepegawaian, pegawai.pangkat, pegawai.golongan, pegawai.tingkat_perjadin, nip_lama))
            connection.commit()
            return {"status": "success", "message": "Data pegawai berhasil diperbarui"}
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

# ==========================================
# 4. ENDPOINT ANGGARAN (DPA)
# ==========================================
@app.get("/api/anggaran")
def get_anggaran():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM anggaran")
            return {"status": "success", "data": cursor.fetchall()}
    finally:
        connection.close()

@app.post("/api/anggaran/bulk")
def bulk_insert_anggaran(data: List[Dict[str, Any]]):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM anggaran")
            for item in data:
                cursor.execute("""
                    INSERT INTO anggaran (id, urusan_code, urusan_uraian, urusan_pptk, prog_code, prog_uraian, prog_pptk, keg_code, keg_uraian, keg_pptk, sub_code, sub_uraian, sub_pptk, rin_code, rin_uraian, rin_nilai)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    item["id"], item["urusan_code"], item["urusan_uraian"], item["urusan_pptk"],
                    item["prog_code"], item["prog_uraian"], item["prog_pptk"],
                    item["keg_code"], item["keg_uraian"], item["keg_pptk"],
                    item["sub_code"], item["sub_uraian"], item["sub_pptk"],
                    item["rin_code"], item["rin_uraian"], item["rin_nilai"]
                ))
            connection.commit()
            return {"status": "success", "message": "Bulk import anggaran berhasil"}
    finally:
        connection.close()

@app.delete("/api/anggaran")
def delete_all_anggaran():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM anggaran")
            connection.commit()
            return {"status": "success", "message": "Seluruh data anggaran berhasil dihapus"}
    finally:
        connection.close()

# ==========================================
# 5. ENDPOINT BKU (BUKU KAS UMUM)
# ==========================================
@app.get("/api/bku")
def get_bku():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM bku")
            rows = cursor.fetchall()
            for r in rows:
                if isinstance(r.get("pajak"), str):
                    try:
                        r["pajak"] = json.loads(r["pajak"])
                    except Exception:
                        r["pajak"] = []
            return {"status": "success", "data": rows}
    finally:
        connection.close()

@app.post("/api/bku")
def tambah_bku(item: Dict[str, Any]):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            pajak_json = json.dumps(item.get("pajak", [])) if isinstance(item.get("pajak"), (list, dict)) else item.get("pajak", "[]")
            cursor.execute("""
                INSERT INTO bku (tanggal, dokumen, penerima, uraian, rekening, penerimaan, pengeluaran, keterangan, status_sipd, pajak)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                item.get("tanggal"), item.get("dokumen"), item.get("penerima"),
                item.get("uraian"), item.get("rekening"), item.get("penerimaan", 0.0),
                item.get("pengeluaran", 0.0), item.get("keterangan"), item.get("status_sipd", "Belum"),
                pajak_json
            ))
            connection.commit()
            return {"status": "success", "message": "BKU berhasil ditambahkan"}
    finally:
        connection.close()

@app.put("/api/bku/status/{bku_id}")
def update_status_sipd(bku_id: int, payload: Dict[str, str]):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE bku SET status_sipd = %s WHERE id = %s", (payload.get("status_sipd"), bku_id))
            connection.commit()
            return {"status": "success"}
    finally:
        connection.close()

@app.delete("/api/bku/{bku_id}")
def delete_bku(bku_id: int):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM bku WHERE id = %s", (bku_id,))
            connection.commit()
            return {"status": "success"}
    finally:
        connection.close()

@app.delete("/api/bku")
def delete_all_bku():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM bku")
            connection.commit()
            return {"status": "success"}
    finally:
        connection.close()

@app.post("/api/bku/bulk")
def bulk_insert_bku(data: List[Dict[str, Any]]):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM bku")
            for item in data:
                pajak_json = json.dumps(item.get("pajak", [])) if isinstance(item.get("pajak"), (list, dict)) else "[]"
                cursor.execute("""
                    INSERT INTO bku (tanggal, dokumen, penerima, uraian, rekening, penerimaan, pengeluaran, keterangan, status_sipd, pajak)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    item.get("tanggal"), item.get("dokumen"), item.get("penerima"),
                    item.get("uraian"), item.get("rekening"), item.get("penerimaan", 0.0),
                    item.get("pengeluaran", 0.0), item.get("keterangan"), item.get("status_sipd", "Belum"),
                    pajak_json
                ))
            connection.commit()
            return {"status": "success"}
    finally:
        connection.close()

# ==========================================
# 6. ENDPOINT ANGGARAN KAS
# ==========================================
@app.get("/api/anggaran-kas")
def get_anggaran_kas():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM anggaran_kas")
            rows = cursor.fetchall()
            for item in rows:
                if isinstance(item.get("months"), str):
                    try:
                        item["months"] = json.loads(item["months"])
                    except Exception:
                        item["months"] = {}
            return {"status": "success", "data": rows}
    finally:
        connection.close()

@app.put("/api/anggaran-kas/{kas_id}")
def update_anggaran_kas(kas_id: str, payload: Dict[str, Any]):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            months_str = json.dumps(payload.get("months", {}))
            cursor.execute("UPDATE anggaran_kas SET months = %s, total_kas = %s WHERE id = %s",
                           (months_str, payload.get("total_kas", 0.0), kas_id))
            connection.commit()
            return {"status": "success"}
    finally:
        connection.close()

@app.post("/api/anggaran-kas/bulk")
def bulk_insert_anggaran_kas(data: List[Dict[str, Any]]):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM anggaran_kas")
            for item in data:
                months_str = json.dumps(item.get("months", {}))
                cursor.execute("""
                    INSERT INTO anggaran_kas (id, idx, kode, uraian, months, total_kas)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (item["id"], item["idx"], item["kode"], item["uraian"], months_str, item["total_kas"]))
            connection.commit()
            return {"status": "success"}
    finally:
        connection.close()

@app.delete("/api/anggaran-kas")
def delete_all_anggaran_kas():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM anggaran_kas")
            connection.commit()
            return {"status": "success"}
    finally:
        connection.close()