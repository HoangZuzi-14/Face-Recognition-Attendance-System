"""MiniFASNet ONNX passive anti-spoofing wrapper."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np


class PADModelUnavailable(RuntimeError):
    """Raised when passive PAD inference cannot run."""


@dataclass(frozen=True)
class PADResult:
    live_score: float
    spoof_score: float


def _default_session_factory(model_path, providers):
    import onnxruntime as ort

    return ort.InferenceSession(str(model_path), providers=providers)


class MiniFASNetPAD:
    """Run MiniFASNet ONNX inference on a face crop."""

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

    def _preprocess(self, crop):
        crop = np.asarray(crop)
        if crop.ndim != 3 or crop.shape[2] < 3 or crop.size == 0:
            raise ValueError("face crop must be a non-empty HxWx3 image")

        try:
            import cv2

            resized = cv2.resize(crop[:, :, :3], self.input_size)
        except Exception:
            resized = np.resize(crop[:, :, :3], (*self.input_size[::-1], 3))

        tensor = resized.astype(np.float32) / 255.0
        tensor = np.transpose(tensor, (2, 0, 1))[None, ...]
        return tensor

    @staticmethod
    def _parse_scores(outputs):
        logits = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
        if logits.size < 2:
            raise PADModelUnavailable("PAD model output must contain at least 2 scores")

        if np.any(logits < 0) or not np.isclose(float(np.sum(logits[:2])), 1.0, atol=1e-3):
            shifted = logits[:2] - np.max(logits[:2])
            probs = np.exp(shifted) / np.sum(np.exp(shifted))
        else:
            probs = logits[:2]
        spoof_score = float(probs[0])
        live_score = float(probs[1])
        return PADResult(live_score=live_score, spoof_score=spoof_score)

    def predict(self, crop):
        session = self._ensure_session()
        tensor = self._preprocess(crop)
        try:
            outputs = session.run(None, {self._input_name: tensor})
        except Exception as exc:
            raise PADModelUnavailable(f"PAD inference failed: {exc}") from exc
        return self._parse_scores(outputs)
