"""Repository for student-related database operations."""

import sqlite3
import pandas as pd
from datetime import datetime

from app.database import get_connection, DB_PATH, DEFAULT_ROSTER, write_audit_log, _sync_face_identities, _next_demo_mssv
from app.backup import backup_sqlite_db


class StudentRepository:
    """Handles student CRUD, roster import, and face linking."""

    def get_all_students(self):
        """Get all students."""
        conn = get_connection()
        df = pd.read_sql_query(
            "SELECT id, mssv, full_name, db_key FROM students ORDER BY full_name", conn
        )
        conn.close()
        return df

    def get_student_by_db_key(self, db_key):
        """Get student info from face db key."""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT mssv, full_name FROM students WHERE db_key=?", (db_key,))
        row = c.fetchone()
        conn.close()
        if row:
            return {"mssv": row[0], "full_name": row[1]}
        return None

    def link_student_face(self, mssv, db_key):
        """Link a student MSSV to a face database key."""
        backup_sqlite_db(DB_PATH)
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE students SET db_key=? WHERE mssv=?", (db_key, mssv))
        conn.commit()
        _sync_face_identities(conn)
        conn.close()
        write_audit_log(
            "student.face_linked",
            entity_type="student",
            entity_id=mssv,
            details=f"db_key={db_key}",
        )

    def ensure_student_in_class(self, class_id, full_name, db_key, mssv=None):
        """Create/link a demo student and attach it to the selected class."""
        full_name = str(full_name).strip()
        db_key = str(db_key).strip()
        if not full_name or not db_key:
            return None

        backup_sqlite_db(DB_PATH)
        conn = get_connection()
        c = conn.cursor()

        c.execute("SELECT id, mssv FROM students WHERE db_key=?", (db_key,))
        row = c.fetchone()
        if row:
            student_id = row[0]
            c.execute("UPDATE students SET full_name=? WHERE id=?", (full_name, student_id))
        else:
            if not mssv:
                mssv = _next_demo_mssv(c)
            c.execute(
                """
                INSERT INTO students (mssv, full_name, db_key)
                VALUES (?, ?, ?)
                ON CONFLICT(mssv) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    db_key = EXCLUDED.db_key
                """,
                (mssv, full_name, db_key),
            )
            c.execute("SELECT id FROM students WHERE mssv=?", (mssv,))
            student_id = c.fetchone()[0]

        c.execute(
            "INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)",
            (class_id, student_id),
        )
        conn.commit()
        _sync_face_identities(conn)
        conn.close()
        return student_id

    def upload_roster(self, class_id, df, existing_faces=None):
        """Import roster from DataFrame with columns 'MSSV' and 'FullName'.
        Returns (added_count, skipped_count).
        """
        valid, message = self.validate_roster_dataframe(df)
        if not valid:
            raise ValueError(message)

        if existing_faces is None:
            existing_faces = set()

        backup_sqlite_db(DB_PATH)
        conn = get_connection()
        c = conn.cursor()
        added = 0
        skipped = 0

        for _, row in df.iterrows():
            mssv = str(row.get("MSSV", "")).strip()
            full_name = str(row.get("FullName", row.get("Họ và Tên", ""))).strip()

            if not mssv or not full_name:
                skipped += 1
                continue

            assumed_db_key = full_name.replace(" ", "_")
            db_key_to_set = assumed_db_key if assumed_db_key in existing_faces else None

            c.execute("""
                INSERT INTO students (mssv, full_name, db_key)
                VALUES (?, ?, ?)
                ON CONFLICT(mssv) DO UPDATE SET full_name = EXCLUDED.full_name
            """, (mssv, full_name, db_key_to_set))

            if db_key_to_set:
                c.execute("UPDATE students SET db_key=? WHERE mssv=?", (db_key_to_set, mssv))

            c.execute("SELECT id FROM students WHERE mssv=?", (mssv,))
            student_id = c.fetchone()[0]

            c.execute(
                "INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)",
                (class_id, student_id),
            )
            added += 1

        conn.commit()
        _sync_face_identities(conn)
        conn.close()
        write_audit_log(
            "roster.imported",
            entity_type="class",
            entity_id=str(class_id),
            details=f"added={added};skipped={skipped}",
        )
        return added, skipped

    def ensure_default_roster(self, class_id, existing_faces=None):
        """Populate a class with 30 demo students. Returns (added_count, skipped_count)."""
        if existing_faces is None:
            existing_faces = set()

        backup_sqlite_db(DB_PATH)
        conn = get_connection()
        c = conn.cursor()
        added = 0
        skipped = 0

        for mssv, full_name in DEFAULT_ROSTER:
            if not mssv or not full_name:
                skipped += 1
                continue

            assumed_db_key = full_name.replace(" ", "_")
            db_key_to_set = assumed_db_key if assumed_db_key in existing_faces else None

            c.execute("SELECT id, db_key FROM students WHERE mssv=?", (mssv,))
            row = c.fetchone()
            if row:
                student_id, current_db_key = row
                c.execute("UPDATE students SET full_name=? WHERE id=?", (full_name, student_id))
                if db_key_to_set and current_db_key != db_key_to_set:
                    c.execute("UPDATE students SET db_key=? WHERE id=?", (db_key_to_set, student_id))
            else:
                c.execute(
                    "INSERT INTO students (mssv, full_name, db_key) VALUES (?, ?, ?)",
                    (mssv, full_name, db_key_to_set),
                )
                student_id = c.lastrowid

            c.execute(
                "INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)",
                (class_id, student_id),
            )
            added += 1

        conn.commit()
        _sync_face_identities(conn)
        conn.close()
        write_audit_log(
            "roster.default_applied",
            entity_type="class",
            entity_id=str(class_id),
            details=f"added={added};skipped={skipped}",
        )
        return added, skipped

    @staticmethod
    def validate_roster_dataframe(df):
        required_id = "MSSV"
        name_options = {"FullName", "Họ và Tên"}
        columns = set(df.columns)
        if required_id not in columns:
            return False, "Roster thiếu cột MSSV."
        if not columns.intersection(name_options):
            return False, "Roster thiếu cột FullName hoặc Họ và Tên."
        if df.empty:
            return False, "Roster không có sinh viên."
        return True, "OK"
