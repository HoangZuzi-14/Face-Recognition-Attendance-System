import tempfile
import unittest
from pathlib import Path

import numpy as np


class FakeSession:
    def __init__(self, output):
        self.output = output
        self.input_seen = None

    def get_inputs(self):
        class Input:
            name = "input"

        return [Input()]

    def run(self, output_names, feeds):
        self.input_seen = feeds["input"]
        return [self.output]


class MiniFASNetONNXTests(unittest.TestCase):
    def test_missing_model_file_raises_clear_error(self):
        from src.pad.minifasnet_onnx import MiniFASNetPAD, PADModelUnavailable

        model = MiniFASNetPAD("missing-model.onnx")

        with self.assertRaises(PADModelUnavailable) as ctx:
            model.predict(np.zeros((100, 100, 3), dtype=np.uint8), (10, 10, 90, 90))

        self.assertIn("PAD model file not found", str(ctx.exception))

    def test_crop_face_dimensions_and_margin(self):
        from src.pad.minifasnet_onnx import MiniFASNetPAD

        model = MiniFASNetPAD("dummy.onnx")
        frame = np.ones((200, 200, 3), dtype=np.uint8) * 10
        
        # Test basic crop with no margin (margin_ratio=1.0)
        crop_no_margin = model.crop_face(frame, (50, 50, 150, 150), margin_ratio=1.0)
        self.assertEqual(crop_no_margin.shape, (100, 100, 3))
        
        # Test crop with margin (margin_ratio=1.2) -> width/height scale is 1.2
        # cx = 100, cy = 100, w = 100, h = 100
        # w_new = 120, h_new = 120 -> bounds: (40, 40, 160, 160)
        crop_with_margin = model.crop_face(frame, (50, 50, 150, 150), margin_ratio=1.2)
        self.assertEqual(crop_with_margin.shape, (120, 120, 3))

    def test_softmax_calculation_uses_print_live_replay_order(self):
        from src.pad.minifasnet_onnx import MiniFASNetPAD

        # Case 1: logits that trigger Spoof
        # print_score high, live_score low, replay_score low
        # spoof_score = print + replay >= 0.35 threshold -> label = SPOOF
        logits = np.array([[8.0, 1.0, 1.0]], dtype=np.float32)
        result = MiniFASNetPAD._parse_scores([logits], spoof_threshold=0.35, live_threshold=0.70)
        self.assertEqual(result.label, "SPOOF")
        self.assertAlmostEqual(result.spoof_score, 0.999, places=3)
        
        # Case 2: logits that trigger Live
        # print_score low, live_score high, replay_score low
        # live_score = 0.998 >= 0.70 threshold -> label = LIVE
        logits = np.array([[1.0, 8.0, 1.0]], dtype=np.float32)
        result = MiniFASNetPAD._parse_scores([logits], spoof_threshold=0.35, live_threshold=0.70)
        self.assertEqual(result.label, "LIVE")
        self.assertAlmostEqual(result.live_score, 0.998, places=3)

        # Case 3: logits that trigger Uncertain
        # print_score = 0.2, live_score = 0.6, replay_score = 0.2
        # spoof_score = 0.4 >= 0.35 -> Wait, spoof threshold is 0.35, so spoof score 0.4 triggers SPOOF first.
        # Let's adjust logits to get spoof_score = 0.2, live_score = 0.6
        # index 0 is print, index 1 is live, index 2 is replay.
        # Let's use custom thresholds: spoof_threshold = 0.5, live_threshold = 0.7.
        # With probs = [0.2, 0.6, 0.2]:
        # live_score = 0.6 < 0.7, spoof_score = 0.4 < 0.5.
        # Result should be UNCERTAIN.
        logits = np.array([[1.0, 2.1, 1.0]], dtype=np.float32)
        result = MiniFASNetPAD._parse_scores([logits], spoof_threshold=0.50, live_threshold=0.70)
        self.assertEqual(result.label, "UNCERTAIN")

    def test_probability_vector_order_is_print_live_replay(self):
        from src.pad.minifasnet_onnx import MiniFASNetPAD

        probabilities = np.array([[0.18, 0.72, 0.10]], dtype=np.float32)
        result = MiniFASNetPAD._parse_scores([probabilities], spoof_threshold=0.35, live_threshold=0.70)

        self.assertEqual(result.label, "LIVE")
        self.assertAlmostEqual(result.live_score, 0.72, places=5)
        self.assertAlmostEqual(result.print_score, 0.18, places=5)
        self.assertAlmostEqual(result.replay_score, 0.10, places=5)
        self.assertAlmostEqual(result.spoof_score, 0.28, places=5)

    def test_output_shape_with_less_than_three_scores_is_blocked(self):
        from src.pad.minifasnet_onnx import MiniFASNetPAD, PADModelUnavailable

        with self.assertRaises(PADModelUnavailable) as ctx:
            MiniFASNetPAD._parse_scores([np.array([[0.9, 0.1]], dtype=np.float32)])

        self.assertIn("at least 3 scores", str(ctx.exception))

    def test_mock_inference_full_flow(self):
        from src.pad.minifasnet_onnx import MiniFASNetPAD

        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "minifasnet.onnx"
            model_path.write_bytes(b"fake model content")
            
            # Mock session outputs 3 class probabilities: index 0 (print), index 1 (live), index 2 (replay).
            fake_session = FakeSession(np.array([[0.1, 0.8, 0.1]], dtype=np.float32))
            model = MiniFASNetPAD(
                str(model_path),
                session_factory=lambda path, providers: fake_session,
            )

            frame = np.ones((100, 100, 3), dtype=np.uint8) * 127
            result = model.predict(frame, (10, 10, 90, 90), spoof_threshold=0.35, live_threshold=0.70)

            self.assertEqual(result.label, "LIVE")
            self.assertAlmostEqual(result.live_score, 0.8, places=3)
            self.assertAlmostEqual(result.print_score, 0.1, places=3)
            self.assertAlmostEqual(result.replay_score, 0.1, places=3)
            self.assertAlmostEqual(result.spoof_score, 0.2, places=3)
            self.assertEqual(fake_session.input_seen.shape, (1, 3, 80, 80))
            self.assertAlmostEqual(float(fake_session.input_seen.max()), 127.0, places=3)


if __name__ == "__main__":
    unittest.main()
