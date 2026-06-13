import unittest


class DemoPerformanceConfigTests(unittest.TestCase):
    def test_demo_defaults_prioritize_fast_attendance_and_disable_liveness_tests(self):
        from app import config

        self.assertEqual(config.VOTE_WINDOW, 2)
        self.assertEqual(config.VOTE_RATIO, 1.0)
        self.assertGreaterEqual(config.TRACKER_TIMEOUT, 5.0)
        self.assertTrue(config.LIVENESS_ENABLED)
        self.assertTrue(config.PASSIVE_PAD_ENABLED)
        self.assertFalse(config.RPPG_ENABLED)

    def test_smooth_profile_runs_recognition_more_frequently(self):
        from app.camera_profiles import resolve_camera_profile

        profile = resolve_camera_profile("smooth")

        self.assertLessEqual(profile.recognition_interval, 0.2)
        self.assertLessEqual(profile.recognition_scale, 0.35)
