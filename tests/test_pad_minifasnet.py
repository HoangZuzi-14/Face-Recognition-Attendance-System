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


class MiniFASNetPadTests(unittest.TestCase):
    def test_missing_model_file_raises_clear_error(self):
        from src.pad.minifasnet import MiniFASNetPAD, PADModelUnavailable

        model = MiniFASNetPAD("missing-model.onnx")

        with self.assertRaises(PADModelUnavailable) as ctx:
            model.predict(np.zeros((80, 80, 3), dtype=np.uint8))

        self.assertIn("PAD model file not found", str(ctx.exception))

    def test_mock_inference_returns_live_and_spoof_scores(self):
        from src.pad.minifasnet import MiniFASNetPAD

        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "minifasnet.onnx"
            model_path.write_bytes(b"fake")
            fake_session = FakeSession(np.array([[0.2, 0.8]], dtype=np.float32))
            model = MiniFASNetPAD(
                str(model_path),
                session_factory=lambda path, providers: fake_session,
            )

            result = model.predict(np.ones((80, 80, 3), dtype=np.uint8) * 127)

            self.assertAlmostEqual(result.spoof_score, 0.2, places=5)
            self.assertAlmostEqual(result.live_score, 0.8, places=5)
            self.assertEqual(fake_session.input_seen.shape, (1, 3, 80, 80))


if __name__ == "__main__":
    unittest.main()
