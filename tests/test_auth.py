import unittest
import os
import sqlite3
import tempfile
from pathlib import Path


class AuthPolicyTests(unittest.TestCase):
    def test_admin_can_clear_and_teacher_cannot(self):
        from app.auth import can_perform

        self.assertTrue(can_perform("admin", "attendance.clear"))
        self.assertFalse(can_perform("teacher", "attendance.clear"))
        self.assertFalse(can_perform("viewer", "attendance.run"))

    def test_bcrypt_password_hash_verification(self):
        from app.auth import hash_password, verify_password

        password_hash = hash_password("s3cret-pass")

        self.assertNotEqual(password_hash, "s3cret-pass")
        self.assertTrue(password_hash.startswith("$2"))
        self.assertTrue(verify_password("s3cret-pass", password_hash))
        self.assertFalse(verify_password("wrong-pass", password_hash))

    def test_init_db_seeds_default_admin_and_teacher_and_authenticates(self):
        from app import database
        from app.user_store import authenticate_user

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            old_username = os.environ.get("ATTENDANCE_ADMIN_USERNAME")
            old_password = os.environ.get("ATTENDANCE_ADMIN_PASSWORD")
            old_teacher_username = os.environ.get("ATTENDANCE_TEACHER_USERNAME")
            old_teacher_password = os.environ.get("ATTENDANCE_TEACHER_PASSWORD")
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            os.environ["ATTENDANCE_ADMIN_USERNAME"] = "root_admin"
            os.environ["ATTENDANCE_ADMIN_PASSWORD"] = "RootAdmin123!"
            os.environ["ATTENDANCE_TEACHER_USERNAME"] = "demo_teacher"
            os.environ["ATTENDANCE_TEACHER_PASSWORD"] = "Teacher123!"
            try:
                database.init_db()
                admin_user = authenticate_user("root_admin", "RootAdmin123!")
                teacher_user = authenticate_user("demo_teacher", "Teacher123!")

                conn = sqlite3.connect(database.DB_PATH)
                users = conn.execute(
                    "SELECT username, password_hash, role, is_active FROM users ORDER BY role"
                ).fetchall()
                conn.close()

                by_username = {row[0]: row for row in users}
                self.assertEqual(by_username["root_admin"][2], "admin")
                self.assertEqual(by_username["demo_teacher"][2], "teacher")
                self.assertNotEqual(by_username["root_admin"][1], "RootAdmin123!")
                self.assertNotEqual(by_username["demo_teacher"][1], "Teacher123!")
                self.assertEqual(admin_user["role"], "admin")
                self.assertEqual(teacher_user["role"], "teacher")
                self.assertNotIn("password_hash", admin_user)
                self.assertNotIn("password_hash", teacher_user)
            finally:
                database.DB_PATH = old_db_path
                if old_username is None:
                    os.environ.pop("ATTENDANCE_ADMIN_USERNAME", None)
                else:
                    os.environ["ATTENDANCE_ADMIN_USERNAME"] = old_username
                if old_password is None:
                    os.environ.pop("ATTENDANCE_ADMIN_PASSWORD", None)
                else:
                    os.environ["ATTENDANCE_ADMIN_PASSWORD"] = old_password
                if old_teacher_username is None:
                    os.environ.pop("ATTENDANCE_TEACHER_USERNAME", None)
                else:
                    os.environ["ATTENDANCE_TEACHER_USERNAME"] = old_teacher_username
                if old_teacher_password is None:
                    os.environ.pop("ATTENDANCE_TEACHER_PASSWORD", None)
                else:
                    os.environ["ATTENDANCE_TEACHER_PASSWORD"] = old_teacher_password

    def test_init_db_adds_missing_default_teacher_to_existing_admin_db(self):
        from app import database
        from app.auth import ROLE_ADMIN, hash_password
        from app.user_store import authenticate_user

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                conn = sqlite3.connect(database.DB_PATH)
                conn.execute(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO users (username, password_hash, role, created_at, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    ("admin", hash_password("admin123"), ROLE_ADMIN, "2026-06-11T00:00:00"),
                )
                conn.commit()
                conn.close()

                database.init_db()

                self.assertEqual(authenticate_user("teacher", "teacher123")["role"], "teacher")
            finally:
                database.DB_PATH = old_db_path

    def test_inactive_user_cannot_authenticate(self):
        from app import database
        from app.auth import ROLE_VIEWER, hash_password
        from app.user_store import authenticate_user

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                conn = sqlite3.connect(database.DB_PATH)
                conn.execute(
                    """
                    INSERT INTO users (username, password_hash, role, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "inactive_user",
                        hash_password("inactive-pass"),
                        ROLE_VIEWER,
                        "2026-06-09T00:00:00",
                        0,
                    ),
                )
                conn.commit()
                conn.close()

                self.assertIsNone(authenticate_user("inactive_user", "inactive-pass"))
            finally:
                database.DB_PATH = old_db_path


if __name__ == "__main__":
    unittest.main()
