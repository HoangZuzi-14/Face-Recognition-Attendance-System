import unittest
from pathlib import Path


class StreamlitAuthUiTests(unittest.TestCase):
    def test_main_uses_login_gate_and_removes_role_selector(self):
        source = Path("app/main.py").read_text(encoding="utf-8")

        self.assertIn("render_login_gate", source)
        self.assertIn("portal_for_role", source)
        self.assertNotIn("role_select", source)


if __name__ == "__main__":
    unittest.main()
