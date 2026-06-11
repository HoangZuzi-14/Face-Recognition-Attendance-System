import os
import pickle
import sqlite3
import tempfile
import unittest
from pathlib import Path


class BackupIntegrityTests(unittest.TestCase):
    def test_backup_file_copies_existing_file_with_timestamped_name(self):
        from app.backup import backup_file

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "db.pkl"
            source.write_bytes(b"face-db")

            backup_path = backup_file(source, backup_root=Path(tmp) / "backups", label="face_db")

            self.assertTrue(backup_path.exists())
            self.assertEqual(backup_path.read_bytes(), b"face-db")
            self.assertIn("face_db", backup_path.name)
            self.assertEqual(source.read_bytes(), b"face-db")

    def test_backup_file_prunes_old_backup_dirs(self):
        from app.backup import backup_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "db.pkl"
            backups = root / "backups"
            source.write_bytes(b"face-db")
            for idx in range(3):
                old_dir = backups / f"old_{idx}"
                old_dir.mkdir(parents=True)
                (old_dir / "x.txt").write_text("x")

            backup_file(source, backup_root=backups, max_dirs=2)

            remaining_dirs = [path for path in backups.iterdir() if path.is_dir()]
            self.assertLessEqual(len(remaining_dirs), 2)

    def test_validate_integrity_reports_missing_face_db_key_and_missing_folders(self):
        from app.integrity import validate_integrity

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "attendance.db"
            face_db_path = root / "db.pkl"
            raw_dir = root / "raw"
            processed_dir = root / "processed"
            raw_dir.mkdir()
            processed_dir.mkdir()

            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, mssv TEXT, full_name TEXT, db_key TEXT)")
            conn.execute("CREATE TABLE attendance (id INTEGER PRIMARY KEY, student_db_key TEXT)")
            conn.execute(
                "INSERT INTO students (mssv, full_name, db_key) VALUES (?, ?, ?)",
                ("S001", "Nguyen Van A", "Nguyen_Van_A"),
            )
            conn.execute(
                "INSERT INTO attendance (student_db_key) VALUES (?)",
                ("Missing_Attendance_Key",),
            )
            conn.commit()
            conn.close()

            with open(face_db_path, "wb") as f:
                pickle.dump({"Orphan_Face": [0.1, 0.2]}, f)

            report = validate_integrity(
                sql_db_path=db_path,
                face_db_path=face_db_path,
                raw_dir=raw_dir,
                processed_dir=processed_dir,
            )

            self.assertFalse(report.ok)
            self.assertIn("Nguyen_Van_A", report.students_missing_face_embeddings)
            self.assertIn("Orphan_Face", report.face_embeddings_missing_students)
            self.assertIn("Nguyen_Van_A", report.missing_raw_dirs)
            self.assertIn("Nguyen_Van_A", report.missing_processed_dirs)
            self.assertIn("Missing_Attendance_Key", report.attendance_keys_missing_students)

    def test_integrity_report_lines_can_limit_long_sections(self):
        from app.integrity import IntegrityReport

        report = IntegrityReport(face_embeddings_missing_students=["A", "B", "C"])

        lines = report.to_lines(max_items=2)

        self.assertIn("  - A", lines)
        self.assertIn("  - B", lines)
        self.assertIn("  ... 1 more", lines)
        self.assertNotIn("  - C", lines)


if __name__ == "__main__":
    unittest.main()
