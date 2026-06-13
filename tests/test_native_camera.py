import unittest


class FakeProcess:
    def __init__(self, running=True, returncode=0):
        self.running = running
        self.returncode = returncode
        self.terminated = False
        self.wait_timeout = None
        self.killed = False

    def poll(self):
        return None if self.running else self.returncode

    def terminate(self):
        self.terminated = True
        self.running = False

    def wait(self, timeout=None):
        self.wait_timeout = timeout
        self.running = False
        return self.returncode

    def kill(self):
        self.killed = True
        self.running = False


class NativeCameraTests(unittest.TestCase):
    def test_build_native_camera_command_uses_module_and_runtime_args(self):
        from app.native_camera import build_native_camera_command

        command = build_native_camera_command(
            python_executable="python.exe",
            camera_index=1,
            class_id=42,
            deadline_hour=9,
            deadline_minute=15,
        )

        self.assertEqual(command[:3], ["python.exe", "-m", "app.native_camera_runner"])
        self.assertIn("--camera-index", command)
        self.assertIn("1", command)
        self.assertIn("--class-id", command)
        self.assertIn("42", command)
        self.assertIn("--deadline-hour", command)
        self.assertIn("9", command)
        self.assertIn("--deadline-minute", command)
        self.assertIn("15", command)
        self.assertIn("--profile", command)
        self.assertIn("smooth", command)

    def test_start_native_camera_stores_process_and_reuses_running_process(self):
        from app.native_camera import start_native_camera_session

        session_state = {}
        created = []

        def fake_popen(command, **kwargs):
            created.append((command, kwargs))
            return FakeProcess(running=True)

        first = start_native_camera_session(
            session_state,
            camera_index=0,
            class_id=3,
            deadline_hour=8,
            deadline_minute=0,
            popen=fake_popen,
        )
        second = start_native_camera_session(
            session_state,
            camera_index=0,
            class_id=3,
            deadline_hour=8,
            deadline_minute=0,
            popen=fake_popen,
        )

        self.assertIs(first, second)
        self.assertEqual(len(created), 1)
        self.assertIs(session_state["native_camera_process"], first)
        self.assertIn("native_camera_preflight", session_state)
        self.assertIn("native_camera_log_path", session_state)
        self.assertIn("stdout", created[0][1])
        self.assertIn("stderr", created[0][1])

    def test_stop_native_camera_terminates_process_and_clears_session_state(self):
        from app.native_camera import stop_native_camera_session

        process = FakeProcess(running=True)
        session_state = {"native_camera_process": process, "run": True}

        stopped = stop_native_camera_session(session_state)

        self.assertTrue(stopped)
        self.assertTrue(process.terminated)
        self.assertEqual(process.wait_timeout, 3)
        self.assertIsNone(session_state["native_camera_process"])
        self.assertFalse(session_state["run"])

    def test_sync_native_camera_state_clears_finished_process(self):
        from app.native_camera import sync_native_camera_state

        session_state = {"native_camera_process": FakeProcess(running=False), "run": True}

        self.assertFalse(sync_native_camera_state(session_state))
        self.assertIsNone(session_state["native_camera_process"])
        self.assertFalse(session_state["run"])

    def test_sync_native_camera_state_reports_known_exit_code(self):
        from app.native_camera import sync_native_camera_state

        session_state = {
            "native_camera_process": FakeProcess(running=False, returncode=3),
            "run": True,
            "native_camera_log_path": "logs/native_camera.log",
        }

        self.assertFalse(sync_native_camera_state(session_state))

        self.assertIn("No usable face embeddings", session_state["native_camera_error"])
        self.assertIn("logs/native_camera.log", session_state["native_camera_error"])

    def test_preflight_reports_identity_db_and_liveness_status(self):
        from app.native_camera import get_native_camera_preflight

        preflight = get_native_camera_preflight(
            class_id=1,
            db_loader=lambda: {"Alice": [1.0], "Bob": [0.0]},
            active_db_builder=lambda db, class_id: {"Alice": db["Alice"]},
            sqlite_db_path="app/attendance.db",
            face_db_path="data/embeddings/db.pkl",
            liveness_enabled=True,
        )

        self.assertEqual(preflight["active_identity_count"], 1)
        self.assertEqual(preflight["face_db_status"], "available")
        self.assertEqual(preflight["sqlite_status"], "available")
        self.assertTrue(preflight["liveness_enabled"])

    def test_create_recognition_target_calls_process_frame_without_frame_skip(self):
        from app.native_camera_runner import create_recognition_target

        calls = []

        def fake_process_frame(frame, db, **kwargs):
            calls.append(kwargs)
            return frame

        target = create_recognition_target(
            fake_process_frame,
            frame="frame",
            active_db={"Person": [1.0]},
            class_id=4,
            deadline_hour=10,
            deadline_minute=5,
            recognition_scale=0.35,
        )
        target()

        self.assertEqual(calls[0]["class_id"], 4)
        self.assertFalse(calls[0]["respect_skip"])
        self.assertEqual(calls[0]["frame_scale"], 0.35)

    def test_hud_lines_include_liveness_snapshot(self):
        from app.native_camera_runner import _format_hud_lines

        lines = _format_hud_lines(
            recognition_running=False,
            last_model_ms=12.5,
            liveness_enabled=True,
            tracker_snapshot={
                "identity": "Alice Smith",
                "recognition_score": 0.91,
                "liveness_label": "SPOOF",
                "liveness_score": 0.12,
                "liveness_reason": "pad_low_score",
            },
        )

        self.assertIn("LIVE", lines[0])
        self.assertIn("Alice Smith", lines[1])
        self.assertIn("rec 0.91", lines[1])
        self.assertIn("SPOOF", lines[2])
        self.assertIn("live 0.12", lines[2])
        self.assertIn("pad_low_score", lines[2])

    def test_hud_lines_show_liveness_off_for_demo_mode(self):
        from app.native_camera_runner import _format_hud_lines

        lines = _format_hud_lines(
            recognition_running=False,
            last_model_ms=12.5,
            liveness_enabled=False,
            tracker_snapshot={
                "identity": "Alice Smith",
                "recognition_score": 0.91,
                "liveness_label": "LIVE",
                "liveness_score": 1.0,
            },
        )

        self.assertIn("Alice Smith", lines[1])
        self.assertIn("liveness OFF", lines[2])
        self.assertNotIn("LIVE 1.00", lines[2])

    def test_open_capture_applies_profile_properties(self):
        from app.camera_profiles import resolve_camera_profile
        from app.native_camera_runner import _open_capture

        class FakeCap:
            def __init__(self):
                self.set_calls = []

            def set(self, prop, value):
                self.set_calls.append((prop, value))
                return True

        class FakeCv2:
            CAP_DSHOW = 700
            CAP_PROP_FOURCC = 6
            CAP_PROP_FRAME_WIDTH = 3
            CAP_PROP_FRAME_HEIGHT = 4
            CAP_PROP_FPS = 5
            CAP_PROP_BUFFERSIZE = 38

            def __init__(self):
                self.capture_args = None
                self.cap = FakeCap()

            def VideoCapture(self, *args):
                self.capture_args = args
                return self.cap

            def VideoWriter_fourcc(self, *chars):
                return "".join(chars)

        cv2 = FakeCv2()
        profile = resolve_camera_profile("smooth")

        cap = _open_capture(cv2, camera_index=2, profile=profile)

        self.assertIs(cap, cv2.cap)
        self.assertEqual(cv2.capture_args[0], 2)
        self.assertEqual(
            cv2.cap.set_calls,
            [
                (cv2.CAP_PROP_FOURCC, "MJPG"),
                (cv2.CAP_PROP_FRAME_WIDTH, profile.width),
                (cv2.CAP_PROP_FRAME_HEIGHT, profile.height),
                (cv2.CAP_PROP_FPS, profile.fps),
                (cv2.CAP_PROP_BUFFERSIZE, 1),
            ],
        )


if __name__ == "__main__":
    unittest.main()
