import os


def _env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name, default):
    value = os.environ.get(name)
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


RECOGNITION_THRESHOLD = 0.35
REVIEW_THRESHOLD = 0.45
CONFIDENCE_GAP = 0.05
MODEL_NAME = "buffalo_l"
VOTE_WINDOW = 4
VOTE_RATIO = 0.75
SKIP_FRAMES = 4
TRACKER_TIMEOUT = 1.5
MATCH_DISTANCE_PX = 150
STATIC_FACE_TIMEOUT = 8.0
RECOGNITION_FRAME_SCALE = 0.4
NATIVE_CAMERA_WIDTH = 1280
NATIVE_CAMERA_HEIGHT = 720
NATIVE_CAMERA_FPS = 30
NATIVE_CAMERA_RECOGNITION_INTERVAL = 0.20
NATIVE_DASHBOARD_REFRESH_SECONDS = 2.0
LIVENESS_ENABLED = _env_bool("LIVENESS_ENABLED", False)
LIVENESS_THRESHOLD = _env_float("LIVENESS_THRESHOLD", 0.70)
CHALLENGE_TIMEOUT = _env_int("CHALLENGE_TIMEOUT", 5)
RPPG_WINDOW = _env_int("RPPG_WINDOW", 90)
PASSIVE_PAD_ENABLED = _env_bool("PASSIVE_PAD_ENABLED", True)
ACTIVE_CHALLENGE_ENABLED = _env_bool("ACTIVE_CHALLENGE_ENABLED", False)
RPPG_ENABLED = _env_bool("RPPG_ENABLED", False)
PAD_MODEL_PATH = os.environ.get(
    "PAD_MODEL_PATH",
    "models/pad/minifasnet.onnx",
)
PAD_THRESHOLD = _env_float("PAD_THRESHOLD", 0.70)
