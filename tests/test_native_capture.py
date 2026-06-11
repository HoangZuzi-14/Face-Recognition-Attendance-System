import types
import unittest
import sys


class FakeProcess:
    def __init__(self, running=True):
        self.running = running
        self.terminated = False
        self.wait_timeout = None
        self.killed = False

    def poll(self):
        return None if self.running else 0

    def terminate(self):
        self.terminated = True
        self.running = False

    def wait(self, timeout=None):
        self.wait_timeout = timeout
        self.running = False
        return 0

    def kill(self):
        self.killed = True
        self.running = False


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class NativeCaptureTests(unittest.TestCase):
    def test_build_native_capture_command_uses_module_and_capture_args(self):
        from app.native_capture import build_native_capture_command

        command = build_native_capture_command(
            python_executable="python.exe",
            camera_index=1,
            person_key="Nguyen_Van_A",
            start_index=7,
        )

        self.assertEqual(command[:3], ["python.exe", "-m", "app.native_capture_runner"])
        self.assertIn("--camera-index", command)
        self.assertIn("1", command)
        self.assertIn("--person-key", command)
        self.assertIn("Nguyen_Van_A", command)
        self.assertIn("--start-index", command)
        self.assertIn("7", command)
        self.assertIn("--profile", command)
        self.assertIn("smooth", command)

    def test_start_native_capture_session_stores_process_and_reuses_running_process(self):
        from app.native_capture import start_native_capture_session

        session_state = {}
        created = []

        def fake_popen(command, **kwargs):
            created.append((command, kwargs))
            return FakeProcess(running=True)

        first = start_native_capture_session(
            session_state,
            camera_index=0,
            person_key="Person_A",
            start_index=2,
            popen=fake_popen,
        )
        second = start_native_capture_session(
            session_state,
            camera_index=0,
            person_key="Person_A",
            start_index=2,
            popen=fake_popen,
        )

        self.assertIs(first, second)
        self.assertEqual(len(created), 1)
        self.assertIs(session_state["native_capture_process"], first)
        self.assertEqual(session_state["native_capture_person_key"], "Person_A")

    def test_stop_native_capture_session_terminates_process_and_clears_session_state(self):
        from app.native_capture import stop_native_capture_session

        process = FakeProcess(running=True)
        session_state = {
            "native_capture_process": process,
            "native_capture_person_key": "Person_A",
        }

        stopped = stop_native_capture_session(session_state)

        self.assertTrue(stopped)
        self.assertTrue(process.terminated)
        self.assertEqual(process.wait_timeout, 3)
        self.assertIsNone(session_state["native_capture_process"])
        self.assertIsNone(session_state["native_capture_person_key"])

    def test_save_valid_capture_writes_only_quality_ok_frames(self):
        from app.native_capture_runner import save_valid_capture

        calls = []

        def fake_save(person_key, frame, index):
            calls.append((person_key, frame, index))
            return "saved.jpg"

        saved = save_valid_capture(
            fake_save,
            person_key="Person_A",
            frame="frame",
            index=5,
            quality=types.SimpleNamespace(ok=True, message="OK"),
        )
        rejected = save_valid_capture(
            fake_save,
            person_key="Person_A",
            frame="bad_frame",
            index=6,
            quality=types.SimpleNamespace(ok=False, message="BLURRY"),
        )

        self.assertEqual(saved, (True, "OK"))
        self.assertEqual(rejected, (False, "BLURRY"))
        self.assertEqual(calls, [("Person_A", "frame", 5)])

    def test_face_register_page_no_longer_uses_streamlit_camera_input(self):
        from pathlib import Path

        source = Path("app/pages/face_register_page.py").read_text(encoding="utf-8")

        self.assertNotIn("st.camera_input", source)
        self.assertIn("start_native_capture_session", source)

    def test_face_registration_display_strings_are_ascii(self):
        from pathlib import Path

        paths = [
            Path("app/pages/face_register_page.py"),
            Path("app/face_quality.py"),
            Path("app/capture_policy.py"),
            Path("app/add_face.py"),
            Path("app/native_capture_runner.py"),
        ]

        for path in paths:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
                source.encode("ascii")

    def test_attendance_start_is_disabled_while_native_capture_is_active(self):
        from pathlib import Path

        source = Path("app/main.py").read_text(encoding="utf-8")

        self.assertIn(
            "st.session_state.capture_mode and not st.session_state.run",
            source,
        )

    def test_begin_capture_starts_native_process_immediately(self):
        sys.modules.setdefault("cv2", types.SimpleNamespace())
        from app.pages import face_register_page

        state = FakeSessionState(cam_source=2)
        calls = []

        face_register_page.st = types.SimpleNamespace(session_state=state)
        face_register_page.get_existing_count = lambda person_key: 4
        face_register_page.stop_native_camera_session = (
            lambda session_state: calls.append(("stop_camera", session_state))
        )
        face_register_page.stop_native_capture_session = (
            lambda session_state: calls.append(("stop_capture", session_state))
        )
        face_register_page.start_native_capture_session = (
            lambda session_state, **kwargs: calls.append(("start_capture", kwargs))
        )

        face_register_page._begin_capture("Person_A")

        self.assertTrue(state["capture_mode"])
        self.assertEqual(state["capture_person_key"], "Person_A")
        self.assertEqual(state["captured_count"], 4)
        self.assertIn(
            (
                "start_capture",
                {
                    "camera_index": 2,
                    "person_key": "Person_A",
                    "start_index": 4,
                    "profile": "smooth",
                },
            ),
            calls,
        )


if __name__ == "__main__":
    unittest.main()
