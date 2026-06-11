import sqlite3
import tempfile
import unittest
from pathlib import Path


class SchemaAuditTests(unittest.TestCase):
    def test_init_db_creates_target_schema_tables(self):
        from app import database

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                conn = sqlite3.connect(database.DB_PATH)
                tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                conn.close()

                self.assertIn("face_identities", tables)
                self.assertIn("attendance_sessions", tables)
                self.assertIn("audit_logs", tables)
                self.assertIn("recognition_events", tables)
                conn = sqlite3.connect(database.DB_PATH)
                audit_columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(audit_logs)")
                }
                conn.close()
                self.assertIn("actor_user_id", audit_columns)
                self.assertIn("actor_username", audit_columns)
                self.assertIn("target", audit_columns)
                self.assertIn("timestamp", audit_columns)
                self.assertIn("status", audit_columns)
                conn = sqlite3.connect(database.DB_PATH)
                recognition_columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(recognition_events)")
                }
                conn.close()
                self.assertIn("liveness_score", recognition_columns)
                self.assertIn("liveness_label", recognition_columns)
                self.assertIn("attack_type", recognition_columns)
                self.assertIn("liveness_reasons", recognition_columns)
                self.assertIn("recognition_score", recognition_columns)
                self.assertIn("decision", recognition_columns)
            finally:
                database.DB_PATH = old_db_path

    def test_log_attendance_links_default_session_and_writes_audit(self):
        from app import database

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                class_id = database.ensure_default_class()
                database.ensure_student_in_class(
                    class_id,
                    full_name="Duong Ngo Hoang Vu",
                    db_key="Duong_Ngo_Hoang_Vu",
                    mssv="DEMO001",
                )

                logged, status = database.log_attendance(
                    "Duong_Ngo_Hoang_Vu", class_id, 0.92
                )

                conn = sqlite3.connect(database.DB_PATH)
                session_count = conn.execute(
                    "SELECT COUNT(*) FROM attendance_sessions WHERE class_id=?",
                    (class_id,),
                ).fetchone()[0]
                attendance_row = conn.execute(
                    "SELECT session_id, student_id, confidence, status FROM attendance"
                ).fetchone()
                audit_count = conn.execute(
                    "SELECT COUNT(*) FROM audit_logs WHERE action='attendance.logged'"
                ).fetchone()[0]
                conn.close()
                audit_df = database.get_recent_audit_logs()

                self.assertTrue(logged)
                self.assertIn(status, {"PRESENT", "LATE"})
                self.assertEqual(session_count, 1)
                self.assertIsNotNone(attendance_row[0])
                self.assertIsNotNone(attendance_row[1])
                self.assertEqual(attendance_row[2], 0.92)
                self.assertGreaterEqual(audit_count, 1)
                self.assertIn("attendance.logged", set(audit_df["action"]))
            finally:
                database.DB_PATH = old_db_path

    def test_audit_log_uses_current_user_context(self):
        from app import database
        from app.audit_context import clear_current_user, set_current_user

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                set_current_user({"id": 42, "username": "admin_user", "role": "admin"})

                database.write_audit_log(
                    "identity.deleted",
                    entity_type="face_identity",
                    entity_id="Alice_Smith",
                    status="SUCCESS",
                )

                conn = sqlite3.connect(database.DB_PATH)
                row = conn.execute(
                    """
                    SELECT actor_user_id, actor_username, target, status, timestamp
                    FROM audit_logs
                    WHERE action='identity.deleted'
                    """
                ).fetchone()
                conn.close()

                self.assertEqual(row[0], 42)
                self.assertEqual(row[1], "admin_user")
                self.assertEqual(row[2], "face_identity:Alice_Smith")
                self.assertEqual(row[3], "SUCCESS")
                self.assertIsNotNone(row[4])
            finally:
                clear_current_user()
                database.DB_PATH = old_db_path

    def test_record_recognition_event_stores_liveness_fields(self):
        from app import database

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                class_id = database.ensure_default_class()

                database.record_recognition_event(
                    class_id,
                    "Alice_Smith",
                    "REJECT_SPOOF",
                    0.91,
                    distance=0.09,
                    gap=0.22,
                    liveness_score=0.12,
                    liveness_label="SPOOF",
                    attack_type="presentation_attack",
                    liveness_reasons=["pad_low_score"],
                    recognition_score=0.91,
                )

                conn = sqlite3.connect(database.DB_PATH)
                row = conn.execute(
                    """
                    SELECT decision, liveness_score, liveness_label, attack_type,
                           liveness_reasons, recognition_score
                    FROM recognition_events
                    WHERE student_db_key='Alice_Smith'
                    """
                ).fetchone()
                conn.close()

                self.assertEqual(row[0], "REJECT_SPOOF")
                self.assertEqual(row[1], 0.12)
                self.assertEqual(row[2], "SPOOF")
                self.assertEqual(row[3], "presentation_attack")
                self.assertIn("pad_low_score", row[4])
                self.assertEqual(row[5], 0.91)
            finally:
                database.DB_PATH = old_db_path


if __name__ == "__main__":
    unittest.main()
