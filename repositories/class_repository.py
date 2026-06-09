"""Repository for class-related database operations."""

import sqlite3
import pandas as pd
from datetime import datetime

from app.database import get_connection, DB_PATH, DEFAULT_CLASS_NAME, write_audit_log
from app.backup import backup_sqlite_db


class ClassRepository:
    """Handles all class CRUD and roster membership queries."""

    def create_class(self, class_name):
        """Create a new class. Returns class_id or None if name already exists."""
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO classes (class_name, created_at) VALUES (?, ?)",
                (class_name, datetime.now().isoformat()),
            )
            conn.commit()
            class_id = c.lastrowid
        except sqlite3.IntegrityError:
            class_id = None
        conn.close()
        return class_id

    def get_classes(self):
        """Return DataFrame of all classes."""
        conn = get_connection()
        df = pd.read_sql_query(
            "SELECT id, class_name, created_at FROM classes ORDER BY class_name", conn
        )
        conn.close()
        return df

    def ensure_default_class(self, class_name=DEFAULT_CLASS_NAME):
        """Create the demo class if needed and return its id."""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM classes WHERE class_name=?", (class_name,))
        row = c.fetchone()
        if row:
            conn.close()
            return row[0]
        c.execute(
            "INSERT INTO classes (class_name, created_at) VALUES (?, ?)",
            (class_name, datetime.now().isoformat()),
        )
        conn.commit()
        class_id = c.lastrowid
        conn.close()
        return class_id

    def class_has_roster(self, class_id):
        """Check if a class has at least one student."""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT 1 FROM class_students WHERE class_id=? LIMIT 1", (class_id,))
        has_roster = c.fetchone() is not None
        conn.close()
        return has_roster

    def get_class_roster(self, class_id):
        """Get all students in a class."""
        conn = get_connection()
        query = """
            SELECT s.mssv, s.full_name, s.db_key
            FROM students s
            JOIN class_students cs ON s.id = cs.student_id
            WHERE cs.class_id = ?
            ORDER BY s.full_name
        """
        df = pd.read_sql_query(query, conn, params=(class_id,))
        conn.close()
        return df

    def get_class_db_keys(self, class_id):
        """Get linked face database keys for students in a class."""
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT s.db_key
            FROM students s
            JOIN class_students cs ON s.id = cs.student_id
            WHERE cs.class_id = ?
              AND s.db_key IS NOT NULL
              AND TRIM(s.db_key) != ''
            """,
            (class_id,),
        )
        keys = {row[0] for row in c.fetchall()}
        conn.close()
        return keys

    def delete_class(self, class_id):
        """Delete a class and its associations."""
        backup_sqlite_db(DB_PATH)
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM class_students WHERE class_id=?", (class_id,))
        c.execute("DELETE FROM attendance WHERE class_id=?", (class_id,))
        c.execute("DELETE FROM classes WHERE id=?", (class_id,))
        conn.commit()
        conn.close()
        write_audit_log("class.deleted", entity_type="class", entity_id=str(class_id))
