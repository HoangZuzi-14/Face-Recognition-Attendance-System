"""Repository for attendance-related database operations."""

import pandas as pd
from datetime import datetime, time

from app.database import (
    get_connection, DB_PATH, write_audit_log,
    get_or_create_attendance_session, record_recognition_event,
)
from app.backup import backup_sqlite_db


class AttendanceRepository:
    """Handles attendance logging, querying, clearing, and export."""

    def log_attendance(self, db_key, class_id, confidence, deadline_hour=8, deadline_minute=0):
        """Log attendance for a student. Only once per class per day.
        Returns (logged: bool, status: str).
        """
        conn = get_connection()
        c = conn.cursor()

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        session_id = get_or_create_attendance_session(
            class_id, deadline_hour, deadline_minute
        )

        c.execute("SELECT id FROM students WHERE db_key=?", (db_key,))
        student_row = c.fetchone()
        student_id = student_row[0] if student_row else None

        c.execute(
            "SELECT id FROM attendance WHERE student_db_key=? AND class_id=? AND date=?",
            (db_key, class_id, today),
        )
        if c.fetchone() is not None:
            conn.close()
            return False, None

        deadline = time(hour=deadline_hour, minute=deadline_minute).isoformat()
        current_time = now.time().isoformat()
        status = "PRESENT" if current_time <= deadline else "LATE"

        c.execute(
            """
            INSERT INTO attendance (
                student_db_key, class_id, date, timestamp, confidence,
                status, session_id, student_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (db_key, class_id, today, now.isoformat(), confidence, status, session_id, student_id),
        )
        conn.commit()
        conn.close()
        write_audit_log(
            "attendance.logged",
            entity_type="attendance",
            entity_id=db_key,
            details=f"class_id={class_id};session_id={session_id};confidence={confidence}",
        )
        return True, status

    def get_full_attendance(self, class_id, deadline_hour=8, deadline_minute=0):
        """Get full class roster with attendance status."""
        conn = get_connection()
        today = datetime.now().strftime("%Y-%m-%d")

        query = """
            SELECT
                s.mssv AS "MSSV",
                s.full_name AS "Họ và Tên",
                s.db_key,
                a.timestamp,
                a.status
            FROM students s
            JOIN class_students cs ON s.id = cs.student_id
            LEFT JOIN attendance a ON a.student_db_key = s.db_key
                                    AND a.class_id = ?
                                    AND a.date = ?
            WHERE cs.class_id = ?
            ORDER BY s.full_name
        """
        df = pd.read_sql_query(query, conn, params=(class_id, today, class_id))
        conn.close()

        rows = []
        deadline_time = time(hour=deadline_hour, minute=deadline_minute)

        for _, row in df.iterrows():
            mssv = row["MSSV"]
            name = row["Họ và Tên"]
            db_key = row["db_key"]

            if db_key is None or db_key == "":
                status = "UNKNOWN"
                time_str = "--:--:--"
            elif row["timestamp"] is None:
                status = "ABSENT"
                time_str = "--:--:--"
            else:
                try:
                    ts = datetime.fromisoformat(row["timestamp"])
                    time_str = ts.strftime("%H:%M:%S")
                    if ts.time() <= deadline_time:
                        status = "PRESENT"
                    else:
                        status = "LATE"
                except Exception:
                    time_str = "--:--:--"
                    status = row["status"]

            rows.append({
                "MSSV": mssv,
                "Họ và Tên": name,
                "Thời Gian": time_str,
                "Trạng Thái": status,
            })

        return pd.DataFrame(rows)

    def get_attended_today(self, class_id):
        """Get set of db_keys that already attended today for a class."""
        conn = get_connection()
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute(
            "SELECT student_db_key FROM attendance WHERE class_id=? AND date=?",
            (class_id, today),
        )
        attended = {row[0] for row in c.fetchall()}
        conn.close()
        return attended

    def get_today_log(self, class_id):
        """Get only attended records for today (simple log)."""
        conn = get_connection()
        today = datetime.now().strftime("%Y-%m-%d")
        query = """SELECT student_db_key, timestamp, confidence, status
                   FROM attendance WHERE class_id=? AND date=?"""
        df = pd.read_sql_query(query, conn, params=(class_id, today))
        conn.close()
        return df

    def export_csv(self, class_id=None, export_path="app/attendance_export.csv"):
        """Export attendance to CSV and return the path."""
        conn = get_connection()
        if class_id:
            today = datetime.now().strftime("%Y-%m-%d")
            query = """
                SELECT s.mssv, s.full_name, a.timestamp, a.confidence, a.status
                FROM attendance a
                LEFT JOIN students s ON a.student_db_key = s.db_key
                WHERE a.class_id = ? AND a.date = ?
            """
            df = pd.read_sql_query(query, conn, params=(class_id, today))
        else:
            df = pd.read_sql_query("SELECT * FROM attendance", conn)
        df.to_csv(export_path, index=False)
        conn.close()
        write_audit_log(
            "report.exported",
            entity_type="class" if class_id else "attendance",
            entity_id=str(class_id) if class_id else None,
            details=f"path={export_path};rows={len(df)}",
        )
        return export_path

    def clear_today(self, class_id=None):
        """Clear attendance for today."""
        backup_sqlite_db(DB_PATH)
        conn = get_connection()
        c = conn.cursor()
        if class_id:
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("DELETE FROM attendance WHERE class_id=? AND date=?", (class_id, today))
        else:
            c.execute("DELETE FROM attendance")
        conn.commit()
        conn.close()
        write_audit_log(
            "attendance.cleared",
            entity_type="class" if class_id else "attendance",
            entity_id=str(class_id) if class_id else None,
        )

    def record_recognition_event(
        self,
        class_id,
        student_db_key,
        decision,
        confidence,
        distance=None,
        gap=None,
        session_id=None,
        liveness_score=None,
        liveness_label=None,
        attack_type=None,
        liveness_reasons=None,
        recognition_score=None,
    ):
        """Record a recognition event for analytics."""
        record_recognition_event(
            class_id, student_db_key, decision, confidence,
            distance=distance,
            gap=gap,
            session_id=session_id,
            liveness_score=liveness_score,
            liveness_label=liveness_label,
            attack_type=attack_type,
            liveness_reasons=liveness_reasons,
            recognition_score=recognition_score,
        )

    def get_recognition_stats(self, class_id=None, limit=50):
        """Get recognition event statistics."""
        conn = get_connection()
        if class_id is None:
            query = """
                SELECT decision, COUNT(*) AS count, AVG(confidence) AS avg_confidence
                FROM recognition_events
                GROUP BY decision ORDER BY count DESC LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(limit,))
        else:
            query = """
                SELECT decision, COUNT(*) AS count, AVG(confidence) AS avg_confidence
                FROM recognition_events
                WHERE class_id=?
                GROUP BY decision ORDER BY count DESC LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(class_id, limit))
        conn.close()
        return df
