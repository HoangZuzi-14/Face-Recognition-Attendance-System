import unittest

import numpy as np


class LivenessTests(unittest.TestCase):
    def test_missing_frame_returns_unknown(self):
        from src.liveness import LIVENESS_UNKNOWN, assess_liveness

        result = assess_liveness(None, face_bbox=(0, 0, 10, 10))

        self.assertEqual(result.label, LIVENESS_UNKNOWN)
        self.assertIn("frame_missing", result.reasons)

    def test_missing_face_bbox_returns_unknown(self):
        from src.liveness import LIVENESS_UNKNOWN, assess_liveness

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = assess_liveness(frame)

        self.assertEqual(result.label, LIVENESS_UNKNOWN)
        self.assertIn("face_bbox_missing", result.reasons)

    def test_valid_frame_and_bbox_return_live_placeholder(self):
        from src.liveness import LIVENESS_LIVE, assess_liveness

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = assess_liveness(frame, face_bbox=(10, 10, 50, 50))

        self.assertEqual(result.label, LIVENESS_LIVE)
        self.assertEqual(result.score, 1.0)
        self.assertIn("rule_placeholder_live", result.reasons)
        self.assertEqual(result.details["bbox_area"], 1600)

    def test_texture_baseline_adds_features_without_deciding_alone(self):
        from src.liveness import assess_texture_liveness

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[20:80, 20:80] = np.indices((60, 60)).sum(axis=0)[:, :, None] % 255

        result = assess_texture_liveness(frame, face_bbox=(20, 20, 80, 80))

        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)
        self.assertIn("sharpness", result.details)
        self.assertIn("fft_high_frequency_ratio", result.details)
        self.assertIn("lbp_texture", result.details)

    def test_pad_score_controls_liveness_when_model_returns_result(self):
        from src.liveness import LIVENESS_SPOOF, assess_liveness
        from src.pad.minifasnet import PADResult

        class FakePadModel:
            def predict(self, crop):
                return PADResult(live_score=0.2, spoof_score=0.8)

        frame = np.ones((100, 100, 3), dtype=np.uint8) * 127
        result = assess_liveness(
            frame,
            face_bbox=(10, 10, 90, 90),
            pad_model=FakePadModel(),
            pad_threshold=0.7,
        )

        self.assertEqual(result.label, LIVENESS_SPOOF)
        self.assertEqual(result.score, 0.2)
        self.assertIn("pad_low_score", result.reasons)
        self.assertEqual(result.details["pad"]["spoof_score"], 0.8)

    def test_missing_pad_model_is_reported_without_breaking_placeholder_flow(self):
        from src.liveness import LIVENESS_LIVE, assess_liveness
        from src.pad.minifasnet import PADModelUnavailable

        class MissingPadModel:
            def predict(self, crop):
                raise PADModelUnavailable("PAD model file not found: model.onnx")

        frame = np.ones((100, 100, 3), dtype=np.uint8) * 127
        result = assess_liveness(
            frame,
            face_bbox=(10, 10, 90, 90),
            pad_model=MissingPadModel(),
        )

        self.assertEqual(result.label, LIVENESS_LIVE)
        self.assertIn("pad_model_unavailable", result.reasons)
        self.assertIn("PAD model file not found", result.details["pad_error"])


if __name__ == "__main__":
    unittest.main()
