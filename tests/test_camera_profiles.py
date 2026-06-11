import unittest


class CameraProfileTests(unittest.TestCase):
    def test_resolve_camera_profile_returns_smooth_profile(self):
        from app.camera_profiles import resolve_camera_profile

        profile = resolve_camera_profile("smooth")

        self.assertEqual(profile.name, "smooth")
        self.assertEqual(profile.width, 640)
        self.assertEqual(profile.height, 360)
        self.assertEqual(profile.fps, 60)
        self.assertEqual(profile.fourcc, "MJPG")

    def test_resolve_camera_profile_falls_back_to_default(self):
        from app.camera_profiles import DEFAULT_CAMERA_PROFILE, resolve_camera_profile

        self.assertEqual(
            resolve_camera_profile("unknown").name,
            DEFAULT_CAMERA_PROFILE,
        )

    def test_profile_options_returns_labels_for_ui(self):
        from app.camera_profiles import profile_options

        options = profile_options()

        self.assertEqual(list(options), ["smooth"])
        self.assertIn("Mượt", options["smooth"])


if __name__ == "__main__":
    unittest.main()
