"""Native OpenCV face-registration capture runner."""

import argparse
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.camera_profiles import DEFAULT_CAMERA_PROFILE, resolve_camera_profile  # noqa: E402


WINDOW_NAME = "Native Face Capture"


def save_valid_capture(save_frame_func, person_key, frame, index, quality):
    if not quality.ok:
        return False, quality.message
    save_frame_func(person_key, frame, index)
    return True, quality.message


def _put_capture_hud(cv2, frame, person_key, saved_count, quality_message):
    cv2.putText(
        frame,
        f"Person: {person_key} | saved: {saved_count}",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2,
    )
    cv2.putText(
        frame,
        "SPACE: save valid frame | Q/ESC: close",
        (12, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 0),
        2,
    )
    if quality_message:
        cv2.putText(
            frame,
            quality_message,
            (12, 88),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )


def run_native_capture(
    camera_index=0,
    person_key="",
    start_index=0,
    profile_name=DEFAULT_CAMERA_PROFILE,
):
    import cv2

    from app.add_face import save_captured_frame
    from app.face_quality import assess_capture_frame
    from app.native_camera_runner import _open_capture

    profile = resolve_camera_profile(profile_name)
    cap = _open_capture(cv2, camera_index, profile)
    if not cap.isOpened():
        print(f"Cannot open camera index {camera_index}.")
        return 4

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    next_index = int(start_index)
    saved_count = 0
    last_message = ""

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
            quality = assess_capture_frame(frame, faces)
            display_frame = frame.copy()

            for (x, y, w, h) in faces:
                color = (0, 255, 0) if quality.ok else (0, 0, 255)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)

            _put_capture_hud(
                cv2,
                display_frame,
                person_key,
                saved_count,
                last_message or quality.message,
            )
            cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key == 32:
                saved, last_message = save_valid_capture(
                    save_captured_frame,
                    person_key,
                    frame,
                    next_index,
                    quality,
                )
                if saved:
                    next_index += 1
                    saved_count += 1
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run native OpenCV face capture.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--person-key", required=True)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--profile", default=DEFAULT_CAMERA_PROFILE)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    return run_native_capture(
        camera_index=args.camera_index,
        person_key=args.person_key,
        start_index=args.start_index,
        profile_name=args.profile,
    )


if __name__ == "__main__":
    raise SystemExit(main())
