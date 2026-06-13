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
        import src.liveness

        old_val = src.liveness.PASSIVE_PAD_ENABLED
        src.liveness.PASSIVE_PAD_ENABLED = False
        try:
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            result = assess_liveness(frame, face_bbox=(10, 10, 50, 50))
        finally:
            src.liveness.PASSIVE_PAD_ENABLED = old_val

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
        from src.pad import PADResult

        class FakePadModel:
            def predict(self, frame, face_bbox):
                return PADResult(
                    live_score=0.2,
                    print_score=0.4,
                    replay_score=0.4,
                    spoof_score=0.8,
                    label="SPOOF",
                )

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

    def test_detect_spoof_returns_passive_pad_result_without_attendance_decision(self):
        from src.liveness import detect_spoof
        from src.pad import PADResult

        class LivePadModel:
            def predict(self, frame, face_bbox):
                return PADResult(
                    live_score=0.9,
                    print_score=0.05,
                    replay_score=0.05,
                    spoof_score=0.1,
                    label="LIVE",
                )

        frame = np.ones((100, 100, 3), dtype=np.uint8) * 127
        result = detect_spoof(frame, (10, 10, 90, 90), pad_model=LivePadModel())

        self.assertEqual(result.label, "LIVE")
        self.assertEqual(result.details["pad"]["spoof_score"], 0.1)
        self.assertNotIn("attendance_logged", result.details)

    def test_missing_pad_model_is_blocked_when_passive_pad_is_enabled(self):
        from src.liveness import LIVENESS_UNKNOWN, assess_liveness
        from src.pad import PADModelUnavailable

        class MissingPadModel:
            def predict(self, frame, face_bbox):
                raise PADModelUnavailable("PAD model file not found: model.onnx")

        frame = np.ones((100, 100, 3), dtype=np.uint8) * 127
        result = assess_liveness(
            frame,
            face_bbox=(10, 10, 90, 90),
            pad_model=MissingPadModel(),
        )

        self.assertEqual(result.label, LIVENESS_UNKNOWN)
        self.assertEqual(result.score, 0.0)
        self.assertIn("pad_model_unavailable", result.reasons)
        self.assertIn("PAD model file not found", result.details["pad_error"])

    def test_pad_inference_error_is_blocked_when_passive_pad_is_enabled(self):
        from src.liveness import LIVENESS_UNKNOWN, assess_liveness

        class BrokenPadModel:
            def predict(self, frame, face_bbox):
                raise RuntimeError("bad tensor shape")

        frame = np.ones((100, 100, 3), dtype=np.uint8) * 127
        result = assess_liveness(
            frame,
            face_bbox=(10, 10, 90, 90),
            pad_model=BrokenPadModel(),
        )

        self.assertEqual(result.label, LIVENESS_UNKNOWN)
        self.assertEqual(result.score, 0.0)
        self.assertIn("pad_inference_error", result.reasons)
        self.assertIn("bad tensor shape", result.details["pad_error"])

    def test_bad_pad_output_shape_is_blocked_when_passive_pad_is_enabled(self):
        from src.liveness import LIVENESS_UNKNOWN, assess_liveness
        from src.pad import PADModelUnavailable

        class BadShapePadModel:
            def predict(self, frame, face_bbox):
                raise PADModelUnavailable("PAD model output must contain at least 3 scores")

        frame = np.ones((100, 100, 3), dtype=np.uint8) * 127
        result = assess_liveness(
            frame,
            face_bbox=(10, 10, 90, 90),
            pad_model=BadShapePadModel(),
        )

        self.assertEqual(result.label, LIVENESS_UNKNOWN)
        self.assertEqual(result.score, 0.0)
        self.assertIn("pad_model_unavailable", result.reasons)
        self.assertIn("at least 3 scores", result.details["pad_error"])


if __name__ == "__main__":
    unittest.main()
