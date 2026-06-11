"""Lightweight rPPG pulse signal utilities."""

from collections import deque
from dataclasses import dataclass, field

import numpy as np

RPPG_LIVE = "LIVE"
RPPG_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RppgSample:
    timestamp: float
    rgb_mean: tuple[float, float, float]


@dataclass(frozen=True)
class RppgResult:
    label: str
    pulse_confidence: float
    bpm: float | None = None
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _validate_bbox(face_bbox, frame_shape):
    if face_bbox is None or len(face_bbox) != 4:
        raise ValueError("face_bbox_missing")
    frame_h, frame_w = frame_shape[:2]
    x1, y1, x2, y2 = [int(v) for v in face_bbox]
    x1 = max(0, min(frame_w, x1))
    x2 = max(0, min(frame_w, x2))
    y1 = max(0, min(frame_h, y1))
    y2 = max(0, min(frame_h, y2))
    if x2 <= x1 or y2 <= y1:
        raise ValueError("face_bbox_invalid")
    return x1, y1, x2, y2


def crop_stable_face_region(frame, face_bbox):
    """Crop a stable upper-middle face ROI for color signal tracking."""
    x1, y1, x2, y2 = _validate_bbox(face_bbox, frame.shape)
    w = x2 - x1
    h = y2 - y1
    rx1 = x1 + int(w * 0.20)
    rx2 = x2 - int(w * 0.20)
    ry1 = y1 + int(h * 0.15)
    ry2 = y1 + int(h * 0.65)
    if rx2 <= rx1 or ry2 <= ry1:
        return frame[y1:y2, x1:x2]
    return frame[ry1:ry2, rx1:rx2]


def mean_rgb(frame, face_bbox):
    roi = crop_stable_face_region(frame, face_bbox)
    if roi.size == 0:
        raise ValueError("face_roi_empty")
    # OpenCV frames are usually BGR; the signal math only needs consistent
    # channels, but expose RGB order for clearer downstream naming.
    bgr_mean = roi[:, :, :3].astype(np.float32).mean(axis=(0, 1))
    return (float(bgr_mean[2]), float(bgr_mean[1]), float(bgr_mean[0]))


class RppgFrameBuffer:
    def __init__(self, window_size=90):
        self.window_size = int(window_size)
        self._samples = deque(maxlen=self.window_size)

    def add_frame(self, frame, face_bbox, timestamp):
        sample = RppgSample(timestamp=float(timestamp), rgb_mean=mean_rgb(frame, face_bbox))
        self._samples.append(sample)
        return sample

    def rgb_series(self):
        if not self._samples:
            return np.empty((0, 3), dtype=np.float32)
        return np.array([sample.rgb_mean for sample in self._samples], dtype=np.float32)

    def timestamps(self):
        return [sample.timestamp for sample in self._samples]

    def __len__(self):
        return len(self._samples)


class RppgSessionStore:
    def __init__(self, window_size=90):
        self.window_size = window_size
        self._buffers = {}

    def buffer_for(self, session_key):
        if session_key not in self._buffers:
            self._buffers[session_key] = RppgFrameBuffer(self.window_size)
        return self._buffers[session_key]

    def drop(self, session_key):
        self._buffers.pop(session_key, None)


def _pos_signal(rgb):
    rgb = np.asarray(rgb, dtype=np.float32)
    rgb = rgb - np.mean(rgb, axis=0, keepdims=True)
    mean = np.mean(np.abs(rgb), axis=0, keepdims=True)
    mean[mean == 0] = 1.0
    normalized = rgb / mean
    x = normalized[:, 1] - normalized[:, 2]
    y = normalized[:, 1] + normalized[:, 2] - 2.0 * normalized[:, 0]
    alpha = np.std(x) / (np.std(y) + 1e-6)
    return x + alpha * y


def estimate_pulse(rgb_series, fps, min_hz=0.7, max_hz=4.0):
    rgb = np.asarray(rgb_series, dtype=np.float32)
    if rgb.ndim != 2 or rgb.shape[1] != 3:
        return RppgResult(
            label=RPPG_UNKNOWN,
            pulse_confidence=0.0,
            reasons=["rgb_series_invalid"],
            details={},
        )
    if rgb.shape[0] < max(30, int(float(fps) * 2)):
        return RppgResult(
            label=RPPG_UNKNOWN,
            pulse_confidence=0.0,
            reasons=["signal_too_short"],
            details={"samples": int(rgb.shape[0])},
        )
    if fps <= 0:
        return RppgResult(
            label=RPPG_UNKNOWN,
            pulse_confidence=0.0,
            reasons=["fps_invalid"],
            details={"fps": fps},
        )

    signal = _pos_signal(rgb)
    signal = signal - np.mean(signal)
    if float(np.std(signal)) <= 1e-6:
        return RppgResult(
            label=RPPG_UNKNOWN,
            pulse_confidence=0.0,
            reasons=["signal_flat"],
            details={"samples": int(rgb.shape[0]), "fps": float(fps)},
        )

    windowed = signal * np.hanning(signal.shape[0])
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(signal.shape[0], d=1.0 / float(fps))
    band = (freqs >= min_hz) & (freqs <= max_hz)
    if not np.any(band):
        return RppgResult(
            label=RPPG_UNKNOWN,
            pulse_confidence=0.0,
            reasons=["pulse_band_missing"],
            details={"samples": int(rgb.shape[0]), "fps": float(fps)},
        )

    band_power = spectrum[band]
    peak_idx = int(np.argmax(band_power))
    peak_freq = float(freqs[band][peak_idx])
    peak_power = float(band_power[peak_idx])
    total_power = float(np.sum(band_power)) + 1e-6
    confidence = float(np.clip(peak_power / total_power, 0.0, 1.0))
    label = RPPG_LIVE if confidence > 0.15 else RPPG_UNKNOWN
    reason = "pulse_detected" if label == RPPG_LIVE else "pulse_confidence_low"
    return RppgResult(
        label=label,
        pulse_confidence=confidence,
        bpm=peak_freq * 60.0,
        reasons=[reason],
        details={
            "samples": int(rgb.shape[0]),
            "fps": float(fps),
            "peak_hz": peak_freq,
            "min_hz": float(min_hz),
            "max_hz": float(max_hz),
        },
    )


def estimate_pulse_from_buffer(buffer):
    timestamps = buffer.timestamps()
    if len(timestamps) < 2:
        return RppgResult(
            label=RPPG_UNKNOWN,
            pulse_confidence=0.0,
            reasons=["signal_too_short"],
            details={"samples": len(timestamps)},
        )
    duration = timestamps[-1] - timestamps[0]
    if duration <= 0:
        return RppgResult(
            label=RPPG_UNKNOWN,
            pulse_confidence=0.0,
            reasons=["timestamps_invalid"],
            details={"samples": len(timestamps), "duration": duration},
        )
    fps = (len(timestamps) - 1) / duration
    return estimate_pulse(buffer.rgb_series(), fps=fps)
