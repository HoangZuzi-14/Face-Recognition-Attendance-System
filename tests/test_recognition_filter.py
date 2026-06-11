import unittest
import sys
import tempfile
import types
from pathlib import Path

sys.modules.setdefault("cv2", types.SimpleNamespace())


class RecognitionFilterTests(unittest.TestCase):
    def test_filter_face_db_keeps_only_allowed_class_keys(self):
        from src.recognize import filter_face_db

        face_db = {
            "Duong_Ngo_Hoang_Vu": [0.1, 0.2],
            "Nguyen_Khanh_Toan": [0.3, 0.4],
            "George_W_Bush": [0.5, 0.6],
        }

        filtered = filter_face_db(
            face_db,
            {"Duong_Ngo_Hoang_Vu", "Nguyen_Khanh_Toan"},
        )

        self.assertEqual(
            set(filtered),
            {"Duong_Ngo_Hoang_Vu", "Nguyen_Khanh_Toan"},
        )

    def test_filter_face_db_returns_original_when_no_allowed_keys_given(self):
        from src.recognize import filter_face_db

        face_db = {"A": [1], "B": [2]}

        self.assertIs(filter_face_db(face_db, None), face_db)

    def test_reports_class_keys_missing_from_face_db(self):
        from app import database
        from services.recognition_service import RecognitionService

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                class_id = database.ensure_default_class()
                database.ensure_student_in_class(
                    class_id, "Known Student", "Known_Student", "ST001"
                )
                database.ensure_student_in_class(
                    class_id, "Missing Student", "Missing_Student", "ST002"
                )

                service = RecognitionService()

                self.assertEqual(
                    service.get_missing_face_keys(
                        {"Known_Student": [1.0, 0.0]},
                        class_id,
                    ),
                    ["Missing_Student"],
                )
            finally:
                database.DB_PATH = old_db_path

    def test_scale_bbox_to_frame_uses_configured_scale(self):
        from src.recognize import scale_bbox_to_frame

        self.assertEqual(
            scale_bbox_to_frame((10, 20, 30, 40), 0.25, (100, 120, 3)),
            (40, 80, 120, 100),
        )


if __name__ == "__main__":
    unittest.main()
