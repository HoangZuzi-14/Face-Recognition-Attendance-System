"""MiniFASNet ONNX anti-spoofing model integration."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    from app.config import PAD_LIVE_THRESHOLD, PAD_SPOOF_THRESHOLD
except ImportError:
    PAD_LIVE_THRESHOLD = 0.70
    PAD_SPOOF_THRESHOLD = 0.35


class PADModelUnavailable(RuntimeError):
    """Raised when passive PAD inference cannot run."""


@dataclass(frozen=True)
class PADResult:
    live_score: float
    print_score: float
    replay_score: float
    spoof_score: float
    label: str


def _default_session_factory(model_path, providers):
    import onnxruntime as ort

    return ort.InferenceSession(str(model_path), providers=providers)


class MiniFASNetPAD:
    """Run MiniFASNet ONNX 3-class anti-spoofing inference."""

    def __init__(
        self,
        model_path,
        providers=None,
        input_size=(80, 80),
        session_factory=None,
    ):
        self.model_path = Path(model_path)
        self.providers = providers or ["CPUExecutionProvider"]
        self.input_size = tuple(input_size)
        self._session_factory = session_factory or _default_session_factory
        self._session = None
        self._input_name = None

    def _ensure_session(self):
        if not self.model_path.exists():
            raise PADModelUnavailable(f"PAD model file not found: {self.model_path}")
        if self._session is None:
            try:
                self._session = self._session_factory(self.model_path, self.providers)
                self._input_name = self._session.get_inputs()[0].name
            except Exception as exc:
                raise PADModelUnavailable(f"Cannot load PAD model: {exc}") from exc
        return self._session

    def crop_face(self, frame, face_bbox, margin_ratio=1.2):
        if face_bbox is None or len(face_bbox) != 4:
            raise ValueError("face_bbox must be a tuple/list of 4 coordinates")

        x1, y1, x2, y2 = [int(v) for v in face_bbox]
        frame_h, frame_w = frame.shape[:2]

        w = x2 - x1
        h = y2 - y1
        cx = x1 + w // 2
        cy = y1 + h // 2

        w_new = int(w * margin_ratio)
        h_new = int(h * margin_ratio)

        x1_new = max(0, cx - w_new // 2)
        y1_new = max(0, cy - h_new // 2)
        x2_new = min(frame_w, cx + w_new // 2)
        y2_new = min(frame_h, cy + h_new // 2)

        if x2_new <= x1_new or y2_new <= y1_new:
            x1_new = max(0, min(frame_w, x1))
            x2_new = max(0, min(frame_w, x2))
            y1_new = max(0, min(frame_h, y1))
            y2_new = max(0, min(frame_h, y2))

        return frame[y1_new:y2_new, x1_new:x2_new]

    def _preprocess(self, crop):
        crop = np.asarray(crop)
        if crop.ndim != 3 or crop.shape[2] < 3 or crop.size == 0:
            raise ValueError("face crop must be a non-empty HxWx3 image")

        try:
            import cv2

            resized = cv2.resize(crop[:, :, :3], self.input_size)
        except Exception:
            resized = np.resize(crop[:, :, :3], (*self.input_size[::-1], 3))

        tensor = resized.astype(np.float32)
        tensor = np.transpose(tensor, (2, 0, 1))[None, ...]
        return tensor

    @staticmethod
    def _parse_scores(outputs, spoof_threshold=PAD_SPOOF_THRESHOLD, live_threshold=PAD_LIVE_THRESHOLD):
        logits = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
        if logits.size < 3:
            raise PADModelUnavailable("PAD model output must contain at least 3 scores")

        # Softmax computation
        if np.any(logits < 0) or not np.isclose(float(np.sum(logits[:3])), 1.0, atol=1e-3):
            shifted = logits[:3] - np.max(logits[:3])
            probs = np.exp(shifted) / np.sum(np.exp(shifted))
        else:
            probs = logits[:3]

        print_score = float(probs[0])
        live_score = float(probs[1])
        replay_score = float(probs[2])
        spoof_score = print_score + replay_score

        if spoof_score >= spoof_threshold:
            label = "SPOOF"
        elif live_score >= live_threshold:
            label = "LIVE"
        else:
            label = "UNCERTAIN"

        return PADResult(
            live_score=live_score,
            print_score=print_score,
            replay_score=replay_score,
            spoof_score=spoof_score,
            label=label,
        )

    def predict(self, frame, face_bbox, margin_ratio=1.2, spoof_threshold=PAD_SPOOF_THRESHOLD, live_threshold=PAD_LIVE_THRESHOLD):
        session = self._ensure_session()
        crop = self.crop_face(frame, face_bbox, margin_ratio)
        tensor = self._preprocess(crop)
        try:
            outputs = session.run(None, {self._input_name: tensor})
        except Exception as exc:
            raise PADModelUnavailable(f"PAD inference failed: {exc}") from exc
        return self._parse_scores(outputs, spoof_threshold, live_threshold)
