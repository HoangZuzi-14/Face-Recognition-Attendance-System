import unittest


class CapturePolicyTests(unittest.TestCase):
    def test_demo_capture_targets_keep_registration_lightweight(self):
        from app.capture_policy import MIN_CAPTURE_IMAGES, RECOMMENDED_CAPTURE_IMAGES

        self.assertEqual(MIN_CAPTURE_IMAGES, 8)
        self.assertEqual(RECOMMENDED_CAPTURE_IMAGES, 15)

    def test_can_finalize_only_after_minimum_valid_captures(self):
        from app.capture_policy import MIN_CAPTURE_IMAGES, can_finalize_capture

        self.assertFalse(can_finalize_capture(MIN_CAPTURE_IMAGES - 1))
        self.assertTrue(can_finalize_capture(MIN_CAPTURE_IMAGES))


if __name__ == "__main__":
    unittest.main()
