import os
import unittest


class LivenessConfigTests(unittest.TestCase):
    def test_env_helpers_use_defaults_for_missing_or_invalid_values(self):
        from app.config import _env_bool, _env_float, _env_int

        missing_name = "MISSING_LIVENESS_TEST_ENV"
        os.environ.pop(missing_name, None)

        self.assertFalse(_env_bool(missing_name, False))
        self.assertEqual(_env_float(missing_name, 0.7), 0.7)
        self.assertEqual(_env_int(missing_name, 12), 12)

        os.environ[missing_name] = "not-a-number"
        try:
            self.assertEqual(_env_float(missing_name, 0.7), 0.7)
            self.assertEqual(_env_int(missing_name, 12), 12)
        finally:
            os.environ.pop(missing_name, None)

    def test_liveness_config_exports_expected_names(self):
        from app import config

        self.assertIsInstance(config.LIVENESS_ENABLED, bool)
        self.assertIsInstance(config.LIVENESS_THRESHOLD, float)
        self.assertIsInstance(config.CHALLENGE_TIMEOUT, int)
        self.assertIsInstance(config.RPPG_WINDOW, int)
        self.assertIsInstance(config.PASSIVE_PAD_ENABLED, bool)
        self.assertIsInstance(config.ACTIVE_CHALLENGE_ENABLED, bool)
        self.assertIsInstance(config.RPPG_ENABLED, bool)
        self.assertIsInstance(config.PAD_MODEL_PATH, str)
        self.assertIsInstance(config.PAD_THRESHOLD, float)


if __name__ == "__main__":
    unittest.main()
