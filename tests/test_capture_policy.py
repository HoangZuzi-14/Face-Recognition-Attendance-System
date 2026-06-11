import unittest


class CapturePolicyTests(unittest.TestCase):
    def test_minimum_capture_images_is_15_and_recommended_is_30(self):
        from app.capture_policy import MIN_CAPTURE_IMAGES, RECOMMENDED_CAPTURE_IMAGES

        self.assertEqual(MIN_CAPTURE_IMAGES, 15)
        self.assertEqual(RECOMMENDED_CAPTURE_IMAGES, 30)

    def test_can_finalize_only_after_minimum_valid_captures(self):
        from app.capture_policy import MIN_CAPTURE_IMAGES, can_finalize_capture

        self.assertFalse(can_finalize_capture(MIN_CAPTURE_IMAGES - 1))
        self.assertTrue(can_finalize_capture(MIN_CAPTURE_IMAGES))


if __name__ == "__main__":
    unittest.main()
