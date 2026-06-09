"""Utility script to identify and optionally clean orphan embedding keys.

Orphan keys are entries in data/embeddings/db.pkl that do not correspond to
any student record in app/attendance.db.  Running with --dry-run (default)
only reports; pass --clean to actually remove them and create a new db.pkl.
"""

import argparse
import os
import pickle
import sqlite3
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.backup import backup_face_db
from app.database import write_audit_log
from src.face_db import FACE_DB_METADATA_KEY, identity_count

FACE_DB_PATH = "data/embeddings/db.pkl"
SQL_DB_PATH = "app/attendance.db"


def get_student_db_keys():
    """Return the set of non-null db_key values from the students table."""
    conn = sqlite3.connect(SQL_DB_PATH)
    cursor = conn.execute(
        "SELECT db_key FROM students WHERE db_key IS NOT NULL AND TRIM(db_key) != ''"
    )
    keys = {row[0] for row in cursor.fetchall()}
    conn.close()
    return keys


def find_orphan_keys():
    """Return orphan keys that exist in db.pkl but not in SQLite students."""
    if not os.path.exists(FACE_DB_PATH):
        print(f"Face DB not found: {FACE_DB_PATH}")
        return set(), {}

    with open(FACE_DB_PATH, "rb") as f:
        db = pickle.load(f)

    student_keys = get_student_db_keys()
    embedding_keys = {key for key in db.keys() if key != FACE_DB_METADATA_KEY}
    orphan_keys = embedding_keys - student_keys
    return orphan_keys, db


def clean_orphans(dry_run=True, max_display=20):
    orphan_keys, db = find_orphan_keys()

    if not orphan_keys:
        print("Không có orphan embedding key nào.")
        return 0

    print(f"\nTìm thấy {len(orphan_keys)} orphan embedding keys:")
    for i, key in enumerate(sorted(orphan_keys)):
        if i >= max_display:
            print(f"  ... và {len(orphan_keys) - max_display} keys khác")
            break
        print(f"  - {key}")

    if dry_run:
        print(f"\n[DRY RUN] Không xóa gì. Chạy với --clean để xóa {len(orphan_keys)} keys.")
        return len(orphan_keys)

    # Backup trước khi xóa
    backup_path = backup_face_db(FACE_DB_PATH)
    print(f"\n[BACKUP] Đã backup db.pkl tại: {backup_path}")

    # Xóa orphan keys
    for key in orphan_keys:
        del db[key]

    with open(FACE_DB_PATH, "wb") as f:
        pickle.dump(db, f)

    print(f"[OK] Đã xóa {len(orphan_keys)} orphan keys. db.pkl còn {identity_count(db)} entries.")
    write_audit_log(
        "embedding.orphans_cleaned",
        entity_type="face_db",
        entity_id=FACE_DB_PATH,
        details=f"removed={len(orphan_keys)};remaining={identity_count(db)}",
    )
    return len(orphan_keys)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tìm và dọn orphan embedding keys không liên kết với student nào."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Thực sự xóa orphan keys (mặc định chỉ dry-run).",
    )
    parser.add_argument(
        "--max-display",
        type=int,
        default=20,
        help="Số lượng key hiển thị tối đa (mặc định 20).",
    )
    args = parser.parse_args()
    clean_orphans(dry_run=not args.clean, max_display=args.max_display)
