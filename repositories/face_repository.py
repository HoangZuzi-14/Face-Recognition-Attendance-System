"""Repository for face identity metadata operations."""

import pandas as pd
from datetime import datetime

from app.database import get_connection, _sync_face_identities


class FaceRepository:
    """Handles face_identities metadata in SQLite."""

    def sync_from_students(self):
        """Synchronize face_identities table from students.db_key."""
        conn = get_connection()
        _sync_face_identities(conn)
        conn.close()

    def get_all_identities(self, active_only=True):
        """Get all face identity records."""
        conn = get_connection()
        query = """
            SELECT fi.id, fi.student_id, fi.person_key, fi.embedding_store,
                   fi.active, fi.created_at, fi.updated_at,
                   s.mssv, s.full_name
            FROM face_identities fi
            LEFT JOIN students s ON fi.student_id = s.id
        """
        if active_only:
            query += " WHERE fi.active = 1"
        query += " ORDER BY fi.person_key"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_identity_by_person_key(self, person_key):
        """Get a face identity by person_key."""
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT fi.id, fi.student_id, fi.person_key, fi.active,
                   s.mssv, s.full_name
            FROM face_identities fi
            LEFT JOIN students s ON fi.student_id = s.id
            WHERE fi.person_key = ?
            """,
            (person_key,),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "student_id": row[1],
                "person_key": row[2],
                "active": bool(row[3]),
                "mssv": row[4],
                "full_name": row[5],
            }
        return None

    def deactivate_identity(self, person_key):
        """Mark a face identity as inactive."""
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE face_identities SET active = 0, updated_at = ? WHERE person_key = ?",
            (datetime.now().isoformat(), person_key),
        )
        conn.commit()
        conn.close()

    def count_active(self):
        """Count active face identities."""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM face_identities WHERE active = 1")
        count = c.fetchone()[0]
        conn.close()
        return count
