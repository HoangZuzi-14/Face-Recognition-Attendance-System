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

    def test_init_db_seeds_initial_admin_and_authenticates(self):
        from app import database
        from app.user_store import authenticate_user

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            old_username = os.environ.get("ATTENDANCE_ADMIN_USERNAME")
            old_password = os.environ.get("ATTENDANCE_ADMIN_PASSWORD")
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            os.environ["ATTENDANCE_ADMIN_USERNAME"] = "root_admin"
            os.environ["ATTENDANCE_ADMIN_PASSWORD"] = "RootAdmin123!"
            try:
                database.init_db()
                user = authenticate_user("root_admin", "RootAdmin123!")

                conn = sqlite3.connect(database.DB_PATH)
                user_row = conn.execute(
                    "SELECT username, password_hash, role, is_active FROM users"
                ).fetchone()
                conn.close()

                self.assertEqual(user_row[0], "root_admin")
                self.assertNotEqual(user_row[1], "RootAdmin123!")
                self.assertEqual(user_row[2], "admin")
                self.assertEqual(user_row[3], 1)
                self.assertEqual(user["username"], "root_admin")
                self.assertEqual(user["role"], "admin")
                self.assertNotIn("password_hash", user)
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
