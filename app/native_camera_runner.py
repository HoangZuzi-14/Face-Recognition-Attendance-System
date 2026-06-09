"""Native OpenCV attendance camera runner.

This module is launched as a separate Python process by the Streamlit app.
The preview window is rendered by OpenCV directly, while attendance updates
continue to be written through the existing recognition pipeline.
"""

import argparse
import os
import sys
import threading
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.camera_profiles import DEFAULT_CAMERA_PROFILE, resolve_camera_profile  # noqa: E402
from src.face_db import identity_count  # noqa: E402


WINDOW_NAME = "Native Attendance Camera"


def create_recognition_target(
    process_frame_func,
    frame,
    active_db,
    class_id=None,
    deadline_hour=8,
    deadline_minute=0,
    recognition_scale=None,
):
    def target():
        process_frame_func(
            frame,
            active_db,
            class_id=class_id,
            deadline_hour=deadline_hour,
            deadline_minute=deadline_minute,
            respect_skip=False,
            frame_scale=recognition_scale,
        )

    return target


def _open_capture(cv2, camera_index, profile):
    if os.name == "nt":
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*profile.fourcc))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, profile.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, profile.height)
    cap.set(cv2.CAP_PROP_FPS, profile.fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _put_hud(cv2, frame, recognition_running=False, last_model_ms=0.0):
    status = "REC..." if recognition_running else "LIVE"
    cv2.putText(
        frame,
        f"{status} | model {last_model_ms:.0f} ms | Q/ESC: close",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2,
    )


def _build_active_db(db, class_id):
    if class_id is None:
        return db
    from services.recognition_service import RecognitionService

    return RecognitionService().build_active_face_db(db, class_id)


def run_native_camera(
    camera_index=0,
    class_id=None,
    deadline_hour=8,
    deadline_minute=0,
    profile_name=DEFAULT_CAMERA_PROFILE,
    recognition_interval=None,
):
    import cv2

    from src.recognize import draw_tracker_labels, load_db, process_frame, reset_trackers

    db = load_db()
    if db is None:
        print("Face DB not found. Build data/embeddings/db.pkl first.")
        return 2

    active_db = _build_active_db(db, class_id)
    if identity_count(active_db) == 0:
        print("No usable face embeddings for the selected class.")
        return 3

    profile = resolve_camera_profile(profile_name)
    if recognition_interval is None:
        recognition_interval = profile.recognition_interval

    reset_trackers()
    cap = _open_capture(cv2, camera_index, profile)
    if not cap.isOpened():
        print(f"Cannot open camera index {camera_index}.")
        return 4

    recog_lock = threading.Lock()
    recog_thread = None
    recognition_running = False
    last_recognition_started = 0.0
    last_model_ms = 0.0

    def start_recognition(frame):
        nonlocal recognition_running, last_model_ms
        started = time.monotonic()
        try:
            create_recognition_target(
                process_frame,
                frame,
                active_db,
                class_id=class_id,
                deadline_hour=deadline_hour,
                deadline_minute=deadline_minute,
                recognition_scale=profile.recognition_scale,
            )()
            last_model_ms = (time.monotonic() - started) * 1000.0
        except Exception:
            import traceback

            traceback.print_exc()
        finally:
            with recog_lock:
                recognition_running = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            now = time.monotonic()
            with recog_lock:
                can_recognize = (
                    not recognition_running
                    and now - last_recognition_started >= recognition_interval
                )
                if can_recognize:
                    recognition_running = True
                    last_recognition_started = now
                    recog_thread = threading.Thread(
                        target=start_recognition,
                        args=(frame.copy(),),
                        daemon=True,
                    )
                    recog_thread.start()

            display_frame = draw_tracker_labels(frame)
            _put_hud(cv2, display_frame, recognition_running, last_model_ms)
            cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if recog_thread is not None and recog_thread.is_alive():
            recog_thread.join(timeout=1.0)

    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run native OpenCV attendance camera.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--class-id", type=int, default=None)
    parser.add_argument("--deadline-hour", type=int, default=8)
    parser.add_argument("--deadline-minute", type=int, default=0)
    parser.add_argument("--profile", default=DEFAULT_CAMERA_PROFILE)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    return run_native_camera(
        camera_index=args.camera_index,
        class_id=args.class_id,
        deadline_hour=args.deadline_hour,
        deadline_minute=args.deadline_minute,
        profile_name=args.profile,
    )


if __name__ == "__main__":
    raise SystemExit(main())
