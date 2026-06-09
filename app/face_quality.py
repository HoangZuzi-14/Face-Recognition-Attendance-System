from dataclasses import dataclass

import cv2
import numpy as np


MIN_BRIGHTNESS = 50
MAX_BRIGHTNESS = 220
MIN_SHARPNESS = 80.0
MIN_FACE_SIZE = 80

REASON_MESSAGES = {
    "OK": "Anh hop le",
    "NO_FACE": "Khong thay khuon mat",
    "MULTIPLE_FACES": "Chi duoc co 1 khuon mat trong khung hinh",
    "TOO_DARK": "Anh qua toi",
    "TOO_BRIGHT": "Anh qua sang",
    "BLURRY": "Anh bi mo",
    "FACE_TOO_SMALL": "Khuon mat qua xa camera",
}


@dataclass
class FaceQualityResult:
    ok: bool
    reason: str
    message: str
    brightness: float = 0.0
    sharpness: float = 0.0


def _clip_face(frame, face):
    x, y, w, h = [int(v) for v in face]
    frame_h, frame_w = frame.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(frame_w, x + w), min(frame_h, y + h)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]


def _result(reason, brightness=0.0, sharpness=0.0):
    return FaceQualityResult(
        ok=reason == "OK",
        reason=reason,
        message=REASON_MESSAGES[reason],
        brightness=round(float(brightness), 2),
        sharpness=round(float(sharpness), 2),
    )


def assess_capture_frame(frame, faces):
    """Validate whether a webcam frame is good enough to save for enrollment."""
    if len(faces) == 0:
        return _result("NO_FACE")
    if len(faces) > 1:
        return _result("MULTIPLE_FACES")

    x, y, w, h = [int(v) for v in faces[0]]
    if min(w, h) < MIN_FACE_SIZE:
        return _result("FACE_TOO_SMALL")

    face_roi = _clip_face(frame, faces[0])
    if face_roi is None:
        return _result("NO_FACE")

    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if brightness < MIN_BRIGHTNESS:
        return _result("TOO_DARK", brightness, sharpness)
    if brightness > MAX_BRIGHTNESS:
        return _result("TOO_BRIGHT", brightness, sharpness)
    if sharpness < MIN_SHARPNESS:
        return _result("BLURRY", brightness, sharpness)

    return _result("OK", brightness, sharpness)
