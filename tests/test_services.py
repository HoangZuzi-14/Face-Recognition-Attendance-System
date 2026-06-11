import tempfile
import unittest
from pathlib import Path


class ServiceWrapperTests(unittest.TestCase):
    def test_recognition_service_builds_class_scoped_face_db(self):
        from app import database
        from services.recognition_service import RecognitionService

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

                face_db = {
                    "Duong_Ngo_Hoang_Vu": [1],
                    "Out_Of_Class": [2],
                }
                active_db = RecognitionService().build_active_face_db(face_db, class_id)

                self.assertEqual(set(active_db), {"Duong_Ngo_Hoang_Vu"})
            finally:
                database.DB_PATH = old_db_path


if __name__ == "__main__":
    unittest.main()
