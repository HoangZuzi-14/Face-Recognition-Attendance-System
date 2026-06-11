import unittest


class CameraTuningTests(unittest.TestCase):
    def test_recommend_profile_prefers_sharpest_profile_above_target_fps(self):
        from src.tune_native_camera import recommend_profile

        results = [
            {"profile": "smooth", "measured_fps": 31.0, "avg_sharpness": 80.0},
            {"profile": "balanced", "measured_fps": 28.0, "avg_sharpness": 120.0},
            {"profile": "sharp", "measured_fps": 25.0, "avg_sharpness": 160.0},
        ]

        self.assertEqual(recommend_profile(results)["profile"], "sharp")

    def test_recommend_profile_uses_fastest_when_no_profile_reaches_target_fps(self):
        from src.tune_native_camera import recommend_profile

        results = [
            {"profile": "smooth", "measured_fps": 20.0, "avg_sharpness": 80.0},
            {"profile": "balanced", "measured_fps": 18.0, "avg_sharpness": 150.0},
            {"profile": "sharp", "measured_fps": 12.0, "avg_sharpness": 250.0},
        ]

        self.assertEqual(recommend_profile(results)["profile"], "smooth")


if __name__ == "__main__":
    unittest.main()
