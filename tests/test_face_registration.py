import unittest
from unittest.mock import patch
import pickle
import tempfile
from pathlib import Path

import cv2
import numpy as np


class FaceRegistrationTests(unittest.TestCase):
    def test_finalize_registration_reports_preprocess_failure(self):
        from app.add_face import finalize_face_registration

        with patch("app.add_face.preprocess_person", return_value=0), \
             patch("app.add_face.extract_and_merge_embedding") as extract:
            result = finalize_face_registration("Nguyen_Van_A")

        self.assertFalse(result.ok)
        self.assertEqual(result.stage, "preprocess")
        self.assertEqual(result.valid_images, 0)
        extract.assert_not_called()

    def test_finalize_registration_reports_embedding_failure(self):
        from app.add_face import finalize_face_registration

        with patch("app.add_face.preprocess_person", return_value=3), \
             patch("app.add_face.extract_and_merge_embedding", return_value=False):
            result = finalize_face_registration("Nguyen_Van_A")

        self.assertFalse(result.ok)
        self.assertEqual(result.stage, "embedding")
        self.assertEqual(result.valid_images, 3)

    def test_finalize_registration_reports_success(self):
        from app.add_face import finalize_face_registration

        with patch("app.add_face.preprocess_person", return_value=5), \
             patch("app.add_face.extract_and_merge_embedding", return_value=True):
            result = finalize_face_registration("Nguyen_Van_A")

        self.assertTrue(result.ok)
        self.assertEqual(result.stage, "complete")
        self.assertEqual(result.valid_images, 5)

    def test_extract_embedding_falls_back_to_raw_frames_when_processed_detection_fails(self):
        from app.add_face import extract_and_merge_embedding

        class FakeFaceModel:
            def get_embedding(self, img_bgr):
                if img_bgr.shape[:2] == (112, 112):
                    return None
                return np.ones(512, dtype=np.float32)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_dir = root / "raw"
            processed_dir = root / "processed"
            db_path = root / "db.pkl"
            (raw_dir / "Nguyen_Van_A").mkdir(parents=True)
            (processed_dir / "Nguyen_Van_A").mkdir(parents=True)
            cv2.imwrite(
                str(raw_dir / "Nguyen_Van_A" / "raw.jpg"),
                np.full((480, 640, 3), 127, dtype=np.uint8),
            )
            cv2.imwrite(
                str(processed_dir / "Nguyen_Van_A" / "processed.jpg"),
                np.full((112, 112, 3), 127, dtype=np.uint8),
            )

            with patch("app.add_face.RAW_DIR", str(raw_dir)), \
                 patch("app.add_face.PROCESSED_DIR", str(processed_dir)), \
                 patch("app.add_face.DB_PATH", str(db_path)), \
                 patch("app.add_face.get_face_model", return_value=FakeFaceModel()):
                result = extract_and_merge_embedding("Nguyen_Van_A")

            self.assertTrue(result)
            with open(db_path, "rb") as handle:
                db = pickle.load(handle)
            self.assertIn("Nguyen_Van_A", db)
            np.testing.assert_allclose(db["Nguyen_Van_A"], np.ones(512, dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
