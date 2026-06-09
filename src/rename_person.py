import os
import pickle
import sqlite3
import argparse
import shutil
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.backup import backup_face_db, backup_sqlite_db
from app.database import write_audit_log
from src.face_db import FACE_DB_METADATA_KEY

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
EMBEDDING_DB = "data/embeddings/db.pkl"
SQL_DB = "app/attendance.db"

def rename_person(old_name, new_name):
    print(f"--- Đang đổi tên từ '{old_name}' sang '{new_name}' ---")
    backup_face_db(EMBEDDING_DB)
    backup_sqlite_db(SQL_DB)

    # 1. Đổi tên thư mục ảnh
    for base_dir in [RAW_DIR, PROCESSED_DIR]:
        old_path = os.path.join(base_dir, old_name)
        new_path = os.path.join(base_dir, new_name)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            print(f"[OK] Đã đổi tên thư mục: {old_path} -> {new_path}")
        else:
            print(f"[!] Không tìm thấy thư mục: {old_path}")

    # 2. Cập nhật file embeddings (db.pkl)
    if os.path.exists(EMBEDDING_DB):
        with open(EMBEDDING_DB, "rb") as f:
            db = pickle.load(f)
        
        if old_name in db:
            db[new_name] = db.pop(old_name)
            metadata = db.get(FACE_DB_METADATA_KEY)
            if isinstance(metadata, dict):
                identity_models = metadata.get("identity_models")
                if isinstance(identity_models, dict) and old_name in identity_models:
                    identity_models[new_name] = identity_models.pop(old_name)
            with open(EMBEDDING_DB, "wb") as f:
                pickle.dump(db, f)
            print(f"[OK] Đã cập nhật vector nhận diện trong {EMBEDDING_DB}")
        else:
            print(f"[!] Không tìm thấy '{old_name}' trong file embeddings.")

    # 3. Cập nhật SQL Database
    if os.path.exists(SQL_DB):
        try:
            conn = sqlite3.connect(SQL_DB)
            cursor = conn.cursor()
            
            # Chuyển đổi tên mới thành định dạng Họ và Tên (thay _ bằng khoảng trắng)
            new_full_name = new_name.replace("_", " ")

            # Cập nhật bảng students (đổi cả db_key và full_name)
            cursor.execute("UPDATE students SET db_key = ?, full_name = ? WHERE db_key = ?", (new_name, new_full_name, old_name))
            updated_students = cursor.rowcount
            
            # Cập nhật bảng attendance
            cursor.execute("UPDATE attendance SET student_db_key = ? WHERE student_db_key = ?", (new_name, old_name))
            updated_attendance = cursor.rowcount
            
            conn.commit()
            conn.close()
            print(f"[OK] Đã cập nhật database SQL: {updated_students} sinh viên, {updated_attendance} bản ghi điểm danh.")
            print(f"     -> Họ tên mới: {new_full_name}")
        except Exception as e:
            print(f"[ERR] Lỗi cập nhật database: {e}")

    print("\n--- Hoàn tất! ---")
    write_audit_log(
        "person.renamed",
        entity_type="student",
        entity_id=new_name,
        details=f"old_key={old_name};new_key={new_name}",
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đổi tên người trong hệ thống face attendance.")
    parser.add_argument("--old", required=True, help="Tên cũ (db_key cũ)")
    parser.add_argument("--new", required=True, help="Tên mới (db_key mới)")
    args = parser.parse_args()
    
    rename_person(args.old, args.new)
