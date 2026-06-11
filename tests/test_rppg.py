import unittest

import numpy as np


class RppgTests(unittest.TestCase):
    def test_buffer_stores_rgb_means_and_keeps_window_size(self):
        from src.rppg import RppgFrameBuffer

        buffer = RppgFrameBuffer(window_size=2)
        frame = np.zeros((20, 20, 3), dtype=np.uint8)
        frame[5:15, 5:15] = [10, 20, 30]

        buffer.add_frame(frame, face_bbox=(5, 5, 15, 15), timestamp=1.0)
        buffer.add_frame(frame + 1, face_bbox=(5, 5, 15, 15), timestamp=2.0)
        buffer.add_frame(frame + 2, face_bbox=(5, 5, 15, 15), timestamp=3.0)

        series = buffer.rgb_series()

        self.assertEqual(series.shape, (2, 3))
        self.assertEqual(buffer.timestamps(), [2.0, 3.0])
        self.assertTrue(np.all(series[-1] > series[0]))

    def test_short_signal_returns_unknown_without_crashing(self):
        from src.rppg import RPPG_UNKNOWN, estimate_pulse

        result = estimate_pulse(np.ones((8, 3), dtype=np.float32), fps=30.0)

        self.assertEqual(result.label, RPPG_UNKNOWN)
        self.assertIn("signal_too_short", result.reasons)

    def test_synthetic_pulse_returns_live_confidence(self):
        from src.rppg import RPPG_LIVE, estimate_pulse

        fps = 30.0
        seconds = 8
        t = np.arange(int(fps * seconds)) / fps
        pulse = 0.05 * np.sin(2 * np.pi * 1.2 * t)
        rgb = np.stack(
            [
                0.5 + pulse * 0.3,
                0.5 + pulse,
                0.5 + pulse * 0.2,
            ],
            axis=1,
        ).astype(np.float32)

        result = estimate_pulse(rgb, fps=fps)

        self.assertEqual(result.label, RPPG_LIVE)
        self.assertGreater(result.pulse_confidence, 0.0)
        self.assertGreater(result.bpm, 40)
        self.assertLess(result.bpm, 240)


if __name__ == "__main__":
    unittest.main()
