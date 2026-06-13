"""Camera capture profiles for the native OpenCV attendance window."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraProfile:
    name: str
    label: str
    width: int
    height: int
    fps: int
    fourcc: str
    recognition_interval: float
    recognition_scale: float


DEFAULT_CAMERA_PROFILE = "smooth"


CAMERA_PROFILES = {
    "smooth": CameraProfile(
        name="smooth",
        label="Mượt nhất (640x360, 60 FPS)",
        width=640,
        height=360,
        fps=60,
        fourcc="MJPG",
        recognition_interval=0.18,
        recognition_scale=0.32,
    ),
}


def resolve_camera_profile(name):
    return CAMERA_PROFILES.get(name, CAMERA_PROFILES[DEFAULT_CAMERA_PROFILE])


def profile_options():
    return {name: profile.label for name, profile in CAMERA_PROFILES.items()}
