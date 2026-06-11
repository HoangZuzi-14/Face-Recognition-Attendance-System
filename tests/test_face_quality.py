import unittest

import cv2
import numpy as np


class FaceQualityTests(unittest.TestCase):
    def test_rejects_when_face_count_is_not_one(self):
        from app.face_quality import assess_capture_frame

        frame = np.full((160, 160, 3), 120, dtype=np.uint8)

        no_face = assess_capture_frame(frame, [])
        many_faces = assess_capture_frame(frame, [(20, 20, 80, 80), (90, 20, 50, 50)])

        self.assertFalse(no_face.ok)
        self.assertEqual(no_face.reason, "NO_FACE")
        self.assertFalse(many_faces.ok)
        self.assertEqual(many_faces.reason, "MULTIPLE_FACES")

    def test_rejects_dark_and_blurry_faces(self):
        from app.face_quality import assess_capture_frame

        dark = np.full((160, 160, 3), 20, dtype=np.uint8)
        blurry = np.full((160, 160, 3), 120, dtype=np.uint8)

        dark_result = assess_capture_frame(dark, [(20, 20, 100, 100)])
        blurry_result = assess_capture_frame(blurry, [(20, 20, 100, 100)])

        self.assertFalse(dark_result.ok)
        self.assertEqual(dark_result.reason, "TOO_DARK")
        self.assertFalse(blurry_result.ok)
        self.assertEqual(blurry_result.reason, "BLURRY")

    def test_accepts_single_bright_sharp_face(self):
        from app.face_quality import assess_capture_frame

        frame = np.full((160, 160, 3), 120, dtype=np.uint8)
        for y in range(20, 120, 10):
            for x in range(20, 120, 10):
                color = 40 if (x + y) % 20 == 0 else 220
                frame[y:y + 10, x:x + 10] = color
        frame = cv2.GaussianBlur(frame, (3, 3), 0)

        result = assess_capture_frame(frame, [(20, 20, 100, 100)])

        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "OK")


if __name__ == "__main__":
    unittest.main()
