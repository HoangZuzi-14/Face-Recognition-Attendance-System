import unittest
from pathlib import Path


class DashboardRefreshTests(unittest.TestCase):
    def test_running_camera_does_not_force_full_page_rerun(self):
        source = Path("app/main.py").read_text(encoding="utf-8")

        self.assertNotIn("time.sleep(NATIVE_DASHBOARD_REFRESH_SECONDS)", source)
        self.assertNotIn("if st.session_state.run:\n    st.rerun()", source)

    def test_attendance_dashboard_uses_fragment_refresh(self):
        source = Path("app/main.py").read_text(encoding="utf-8")

        self.assertIn("@st.fragment(run_every=NATIVE_DASHBOARD_REFRESH_SECONDS)", source)

    def test_main_does_not_emit_raw_closing_div_markdown(self):
        source = Path("app/main.py").read_text(encoding="utf-8")

        self.assertNotIn("st.markdown('</div>', unsafe_allow_html=True)", source)


if __name__ == "__main__":
    unittest.main()
