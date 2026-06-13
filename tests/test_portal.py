import unittest


class PortalTests(unittest.TestCase):
    def test_admin_and_teacher_portals_have_distinct_labels_and_tabs(self):
        from app.portal import portal_for_role

        admin = portal_for_role("admin")
        teacher = portal_for_role("teacher")

        self.assertEqual(admin["label"], "Admin Portal")
        self.assertEqual(teacher["label"], "Teacher Portal")
        self.assertIn("setup", admin["tabs"])
        self.assertIn("roster", admin["tabs"])
        self.assertIn("face", admin["tabs"])
        self.assertNotIn("setup", teacher["tabs"])
        self.assertIn("roster", teacher["tabs"])
        self.assertIn("face", teacher["tabs"])

    def test_unknown_role_falls_back_to_teacher_portal(self):
        from app.portal import portal_for_role

        self.assertEqual(portal_for_role("unknown")["label"], "Teacher Portal")


if __name__ == "__main__":
    unittest.main()
