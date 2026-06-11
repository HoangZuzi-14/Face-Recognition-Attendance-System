import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path


class DemoTestResultsExportTests(unittest.TestCase):
    def test_export_demo_results_writes_markdown_csv_and_validates_spoof_attendance(self):
        from app import database
        from scripts.export_demo_test_results import export_demo_test_results

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            old_db_path = database.DB_PATH
            database.DB_PATH = str(tmp_path / "attendance.db")
            try:
                database.init_db()
                conn = sqlite3.connect(database.DB_PATH)
                conn.execute(
                    """
                    INSERT INTO attendance (
                        student_db_key, class_id, date, timestamp, confidence, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "Alice_Live",
                        1,
                        "2026-06-11",
                        "2026-06-11T08:00:00",
                        0.96,
                        "PRESENT",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO recognition_events (
                        class_id, student_db_key, decision, confidence,
                        created_at, liveness_score, liveness_label, attack_type,
                        liveness_reasons, recognition_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        "Alice_Live",
                        "ACCEPT",
                        0.96,
                        "2026-06-11T08:00:00",
                        0.94,
                        "LIVE",
                        "",
                        "[]",
                        0.96,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO recognition_events (
                        class_id, student_db_key, decision, confidence,
                        created_at, liveness_score, liveness_label, attack_type,
                        liveness_reasons, recognition_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        "Eve_Print_Attack",
                        "REJECT_SPOOF",
                        0.91,
                        "2026-06-11T08:01:00",
                        0.12,
                        "SPOOF",
                        "print_attack",
                        '["pad_low_score"]',
                        0.91,
                    ),
                )
                conn.commit()
                conn.close()

                result = export_demo_test_results(
                    db_path=database.DB_PATH,
                    reports_dir=tmp_path / "reports",
                )

                self.assertEqual(result["recognition_events"], 2)
                self.assertEqual(result["attendance_rows"], 1)
                self.assertEqual(result["spoof_attendance_violations"], [])
                self.assertEqual(result["events_missing_required_fields"], [])
                self.assertTrue((tmp_path / "reports" / "demo_test_results.md").exists())
                csv_path = tmp_path / "reports" / "demo_test_results.csv"
                self.assertTrue(csv_path.exists())

                with csv_path.open(newline="", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))

                self.assertEqual(len(rows), 2)
                self.assertIn("timestamp", rows[0])
                self.assertIn("recognition_score", rows[0])
                self.assertIn("liveness_score", rows[0])
                self.assertIn("liveness_label", rows[0])
                self.assertIn("attack_type", rows[0])
                self.assertIn("decision", rows[0])
            finally:
                database.DB_PATH = old_db_path

    def test_real_demo_plan_contains_required_checklist_items(self):
        plan_path = Path("docs/real_demo_test_plan.md")

        self.assertTrue(plan_path.exists())
        text = plan_path.read_text(encoding="utf-8")

        for item in [
            "integrity check",
            "unit tests",
            "login/auth test",
            "real user attendance test",
            "unknown user test",
            "print attack test",
            "screen replay attack test",
            "active challenge test",
            "recognition event logging test",
            "attendance log verification",
        ]:
            self.assertIn(item, text)

    def test_export_filters_legacy_events_by_demo_date(self):
        from app import database
        from scripts.export_demo_test_results import export_demo_test_results

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            old_db_path = database.DB_PATH
            database.DB_PATH = str(tmp_path / "attendance.db")
            try:
                database.init_db()
                conn = sqlite3.connect(database.DB_PATH)
                conn.execute(
                    """
                    INSERT INTO recognition_events (
                        class_id, student_db_key, decision, confidence,
                        created_at, recognition_score, liveness_score, liveness_label
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        "Legacy_Event",
                        "NEED_REVIEW",
                        0.50,
                        "2026-05-26T14:07:29",
                        None,
                        None,
                        None,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO recognition_events (
                        class_id, student_db_key, decision, confidence,
                        created_at, recognition_score, liveness_score, liveness_label
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        "Today_Event",
                        "ACCEPT",
                        0.96,
                        "2026-06-11T09:00:00",
                        0.96,
                        0.94,
                        "LIVE",
                    ),
                )
                conn.commit()
                conn.close()

                result = export_demo_test_results(
                    db_path=database.DB_PATH,
                    reports_dir=tmp_path / "reports",
                    demo_date="2026-06-11",
                )

                self.assertEqual(result["recognition_events"], 1)
                self.assertEqual(result["events_missing_required_fields"], [])
                csv_text = (tmp_path / "reports" / "demo_test_results.csv").read_text(
                    encoding="utf-8"
                )
                self.assertIn("Today_Event", csv_text)
                self.assertNotIn("Legacy_Event", csv_text)
            finally:
                database.DB_PATH = old_db_path


if __name__ == "__main__":
    unittest.main()
