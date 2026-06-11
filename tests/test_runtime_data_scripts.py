import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RuntimeDataScriptTests(unittest.TestCase):
    def test_backup_runtime_data_copies_files_and_writes_manifest(self):
        from scripts.backup_runtime_data import create_runtime_backup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir()
            (root / "data" / "embeddings").mkdir(parents=True)
            (root / "data" / "raw" / "Alice").mkdir(parents=True)

            (root / "app" / "attendance.db").write_bytes(b"sqlite-db")
            (root / "data" / "embeddings" / "db.pkl").write_bytes(b"face-db")
            (root / "data" / "raw" / "Alice" / "img.jpg").write_bytes(b"image")

            backup_dir, manifest = create_runtime_backup(
                project_root=root,
                backup_root=root / "backups",
                timestamp="20260609_120000",
                include_paths=[
                    "app/attendance.db",
                    "data/embeddings/db.pkl",
                    "data/raw",
                ],
            )

            self.assertTrue((backup_dir / "app" / "attendance.db").exists())
            self.assertTrue((backup_dir / "data" / "embeddings" / "db.pkl").exists())
            self.assertTrue((backup_dir / "data" / "raw" / "Alice" / "img.jpg").exists())
            self.assertTrue((backup_dir / "backup_manifest.json").exists())

            manifest_paths = {entry["relative_path"] for entry in manifest["files"]}
            self.assertIn("app/attendance.db", manifest_paths)
            self.assertIn("data/embeddings/db.pkl", manifest_paths)
            self.assertIn("data/raw/Alice/img.jpg", manifest_paths)
            for entry in manifest["files"]:
                self.assertEqual(len(entry["sha256"]), 64)
                self.assertGreater(entry["size_bytes"], 0)

    def test_archive_orphan_attendance_moves_rows_without_hard_delete(self):
        from scripts.archive_orphan_attendance import archive_orphan_attendance

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "attendance.db"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, db_key TEXT)")
            conn.execute(
                "CREATE TABLE face_identities (id INTEGER PRIMARY KEY, person_key TEXT)"
            )
            conn.execute(
                """
                CREATE TABLE attendance (
                    id INTEGER PRIMARY KEY,
                    student_db_key TEXT,
                    class_id INTEGER,
                    date TEXT,
                    timestamp TEXT,
                    confidence REAL,
                    status TEXT,
                    session_id INTEGER,
                    student_id INTEGER,
                    review_reason TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO attendance (
                    student_db_key, class_id, date, timestamp,
                    confidence, status, session_id, student_id, review_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("Tran_Binh_Minh", 1, "2026-05-18", "2026-05-18T00:17:58", 0.9, "PRESENT", None, None, None),
            )
            conn.commit()
            conn.close()

            result = archive_orphan_attendance(
                db_path=db_path,
                face_db_path=Path(tmp) / "missing.pkl",
                key="Tran_Binh_Minh",
                backup=False,
            )

            self.assertEqual(result["archived_count"], 1)
            conn = sqlite3.connect(db_path)
            current_rows = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
            archived_rows = conn.execute("SELECT COUNT(*) FROM attendance_orphans").fetchone()[0]
            archived_key = conn.execute(
                "SELECT student_db_key FROM attendance_orphans"
            ).fetchone()[0]
            conn.close()

            self.assertEqual(current_rows, 0)
            self.assertEqual(archived_rows, 1)
            self.assertEqual(archived_key, "Tran_Binh_Minh")

    def test_archive_orphan_attendance_skips_existing_student_identity(self):
        from scripts.archive_orphan_attendance import archive_orphan_attendance

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "attendance.db"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, db_key TEXT)")
            conn.execute(
                "CREATE TABLE face_identities (id INTEGER PRIMARY KEY, person_key TEXT)"
            )
            conn.execute(
                "CREATE TABLE attendance (id INTEGER PRIMARY KEY, student_db_key TEXT)"
            )
            conn.execute("INSERT INTO students (db_key) VALUES (?)", ("Known_Key",))
            conn.execute(
                "INSERT INTO attendance (student_db_key) VALUES (?)", ("Known_Key",)
            )
            conn.commit()
            conn.close()

            result = archive_orphan_attendance(
                db_path=db_path,
                face_db_path=Path(tmp) / "missing.pkl",
                key="Known_Key",
                backup=False,
            )

            self.assertEqual(result["archived_count"], 0)
            self.assertEqual(result["reason"], "identity_exists")

    def test_archive_orphan_attendance_cli_runs_from_script_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "attendance.db"
            backup_root = Path(tmp) / "backups"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, db_key TEXT)")
            conn.execute(
                "CREATE TABLE face_identities (id INTEGER PRIMARY KEY, person_key TEXT)"
            )
            conn.execute(
                "CREATE TABLE attendance (id INTEGER PRIMARY KEY, student_db_key TEXT)"
            )
            conn.execute(
                "INSERT INTO attendance (student_db_key) VALUES (?)",
                ("Tran_Binh_Minh",),
            )
            conn.commit()
            conn.close()

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/archive_orphan_attendance.py",
                    "--db-path",
                    str(db_path),
                    "--face-db-path",
                    str(Path(tmp) / "missing.pkl"),
                    "--key",
                    "Tran_Binh_Minh",
                    "--backup-root",
                    str(backup_root),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"archived_count": 1', result.stdout)


if __name__ == "__main__":
    unittest.main()
