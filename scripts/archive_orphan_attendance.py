import argparse
import json
import pickle
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


ARCHIVE_COLUMNS = [
    "student_db_key",
    "class_id",
    "date",
    "timestamp",
    "confidence",
    "status",
    "session_id",
    "student_id",
    "review_reason",
]


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _sqlite_identity_exists(conn, key):
    if _table_exists(conn, "students"):
        row = conn.execute(
            "SELECT 1 FROM students WHERE db_key=? LIMIT 1",
            (key,),
        ).fetchone()
        if row:
            return True
    if _table_exists(conn, "face_identities"):
        row = conn.execute(
            "SELECT 1 FROM face_identities WHERE person_key=? LIMIT 1",
            (key,),
        ).fetchone()
        if row:
            return True
    return False


def _face_db_identity_exists(face_db_path, key):
    path = Path(face_db_path)
    if not path.exists():
        return False
    try:
        with open(path, "rb") as handle:
            db = pickle.load(handle)
    except Exception:
        return False
    return isinstance(db, dict) and key in db


def _ensure_archive_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_orphans (
            archive_id INTEGER PRIMARY KEY,
            original_attendance_id INTEGER UNIQUE,
            student_db_key TEXT,
            class_id INTEGER,
            date TEXT,
            timestamp TEXT,
            confidence REAL,
            status TEXT,
            session_id INTEGER,
            student_id INTEGER,
            review_reason TEXT,
            archived_at TEXT,
            archive_reason TEXT
        )
        """
    )


def _attendance_columns(conn):
    return {row[1] for row in conn.execute("PRAGMA table_info(attendance)").fetchall()}


def _write_audit_if_available(conn, key, count):
    if not _table_exists(conn, "audit_logs"):
        return
    conn.execute(
        """
        INSERT INTO audit_logs (action, entity_type, entity_id, actor, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "attendance.orphan_archived",
            "attendance",
            key,
            "system",
            f"archived_count={count}",
            datetime.now().isoformat(),
        ),
    )


def archive_orphan_attendance(
    db_path="app/attendance.db",
    face_db_path="data/embeddings/db.pkl",
    key="Tran_Binh_Minh",
    backup=True,
    backup_root=None,
):
    db_path = Path(db_path)
    if backup:
        from app.backup import backup_sqlite_db

        backup_sqlite_db(str(db_path), backup_root=backup_root or "backups")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if not _table_exists(conn, "attendance"):
            return {"key": key, "archived_count": 0, "reason": "attendance_table_missing"}

        if _sqlite_identity_exists(conn, key) or _face_db_identity_exists(face_db_path, key):
            return {"key": key, "archived_count": 0, "reason": "identity_exists"}

        rows = conn.execute(
            "SELECT * FROM attendance WHERE student_db_key=?",
            (key,),
        ).fetchall()
        if not rows:
            return {"key": key, "archived_count": 0, "reason": "no_attendance_rows"}

        _ensure_archive_table(conn)
        existing_columns = _attendance_columns(conn)
        archived_at = datetime.now().isoformat()
        archive_reason = "student_db_key_missing_from_students_face_identities_and_face_db"

        for row in rows:
            values = {
                column: row[column] if column in existing_columns else None
                for column in ARCHIVE_COLUMNS
            }
            conn.execute(
                """
                INSERT OR IGNORE INTO attendance_orphans (
                    original_attendance_id, student_db_key, class_id, date,
                    timestamp, confidence, status, session_id, student_id,
                    review_reason, archived_at, archive_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    values["student_db_key"],
                    values["class_id"],
                    values["date"],
                    values["timestamp"],
                    values["confidence"],
                    values["status"],
                    values["session_id"],
                    values["student_id"],
                    values["review_reason"],
                    archived_at,
                    archive_reason,
                ),
            )

        conn.execute("DELETE FROM attendance WHERE student_db_key=?", (key,))
        _write_audit_if_available(conn, key, len(rows))
        conn.commit()
        return {"key": key, "archived_count": len(rows), "reason": "archived"}
    finally:
        conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Archive orphan attendance rows.")
    parser.add_argument("--db-path", default="app/attendance.db")
    parser.add_argument("--face-db-path", default="data/embeddings/db.pkl")
    parser.add_argument("--key", default="Tran_Binh_Minh")
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument("--backup-root", default="backups")
    args = parser.parse_args(argv)

    result = archive_orphan_attendance(
        db_path=args.db_path,
        face_db_path=args.face_db_path,
        key=args.key,
        backup=not args.no_backup,
        backup_root=args.backup_root,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
