import tempfile
import unittest
from pathlib import Path


class DefaultRosterTests(unittest.TestCase):
    def test_default_class_roster_has_30_students_and_links_existing_faces(self):
        from app import database

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                class_id = database.ensure_default_class()
                added, skipped = database.ensure_default_roster(
                    class_id,
                    existing_faces={
                        "Duong_Ngo_Hoang_Vu",
                        "Nguyen_Khanh_Toan",
                        "Tony_Blair",
                    },
                )

                roster = database.get_class_roster(class_id)

                self.assertEqual(added, 29)
                self.assertEqual(skipped, 0)
                self.assertEqual(len(roster), 29)
                linked = dict(zip(roster["full_name"], roster["db_key"]))
                self.assertEqual(linked["Nguyen Khanh Toan"], "Nguyen_Khanh_Toan")
                self.assertEqual(linked["Tony Blair"], "Tony_Blair")
            finally:
                database.DB_PATH = old_db_path

    def test_ensure_student_in_class_creates_demo_student_and_links_face(self):
        from app import database

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                conn = database.get_connection()
                conn.execute("DELETE FROM class_students")
                conn.execute("DELETE FROM students")
                conn.commit()
                conn.close()
                class_id = database.ensure_default_class()

                student_id = database.ensure_student_in_class(
                    class_id,
                    full_name="Nguyen Van A",
                    db_key="Nguyen_Van_A",
                )
                roster = database.get_class_roster(class_id)

                self.assertIsInstance(student_id, int)
                self.assertEqual(len(roster), 1)
                self.assertEqual(roster.iloc[0]["full_name"], "Nguyen Van A")
                self.assertEqual(roster.iloc[0]["db_key"], "Nguyen_Van_A")
                self.assertTrue(str(roster.iloc[0]["mssv"]).startswith("DEMO"))
            finally:
                database.DB_PATH = old_db_path

    def test_default_roster_replaces_stale_demo_face_links(self):
        from app import database

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                class_id = database.ensure_default_class()
                database.ensure_student_in_class(
                    class_id,
                    full_name="George W Bush",
                    db_key="George_W_Bush",
                    mssv="DEMO002",
                )

                database.ensure_default_roster(
                    class_id,
                    existing_faces={"Nguyen_Khanh_Toan"},
                )
                roster = database.get_class_roster(class_id)
                linked = dict(zip(roster["full_name"], roster["db_key"]))

                self.assertEqual(linked["Nguyen Khanh Toan"], "Nguyen_Khanh_Toan")
            finally:
                database.DB_PATH = old_db_path

    def test_get_class_db_keys_returns_only_linked_students_in_class(self):
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
                database.ensure_student_in_class(
                    class_id,
                    full_name="Nguyen Khanh Toan",
                    db_key="Nguyen_Khanh_Toan",
                    mssv="DEMO002",
                )

                self.assertEqual(
                    database.get_class_db_keys(class_id),
                    {"Duong_Ngo_Hoang_Vu", "Nguyen_Khanh_Toan"},
                )
            finally:
                database.DB_PATH = old_db_path


if __name__ == "__main__":
    unittest.main()
