"""Rule-based liveness placeholder.

This module provides the public gate shape for future passive PAD, active
challenge, and rPPG implementations. The first version only validates inputs
and returns LIVE for a valid frame + face bbox so the recognition pipeline can
integrate without changing camera behavior.
"""

from dataclasses import dataclass, field

import numpy as np

from app.config import PAD_MODEL_PATH, PAD_THRESHOLD, PASSIVE_PAD_ENABLED

LIVENESS_LIVE = "LIVE"
LIVENESS_SPOOF = "SPOOF"
LIVENESS_CHALLENGE = "CHALLENGE"
LIVENESS_UNKNOWN = "UNKNOWN"

_PAD_MODEL_CACHE = None


@dataclass(frozen=True)
class LivenessResult:
    score: float
    label: str
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _valid_frame_shape(frame):
    shape = getattr(frame, "shape", None)
    return shape is not None and len(shape) >= 2 and shape[0] > 0 and shape[1] > 0


def _validate_bbox(face_bbox, frame_shape):
    if face_bbox is None:
        return None, "face_bbox_missing"
    if len(face_bbox) != 4:
        return None, "face_bbox_invalid"

    try:
        x1, y1, x2, y2 = [int(v) for v in face_bbox]
    except (TypeError, ValueError):
        return None, "face_bbox_invalid"

    frame_h, frame_w = frame_shape[:2]
    x1 = max(0, min(frame_w, x1))
    x2 = max(0, min(frame_w, x2))
    y1 = max(0, min(frame_h, y1))
    y2 = max(0, min(frame_h, y2))
    if x2 <= x1 or y2 <= y1:
        return None, "face_bbox_invalid"
    return (x1, y1, x2, y2), None


def crop_face(frame, face_bbox):
    bbox, error = _validate_bbox(face_bbox, frame.shape)
    if error:
        raise ValueError(error)
    x1, y1, x2, y2 = bbox
    return frame[y1:y2, x1:x2], bbox


def _to_gray(image):
    image = np.asarray(image)
    if image.ndim == 2:
        return image.astype(np.float32)
    rgb = image[:, :, :3].astype(np.float32)
    return 0.114 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.299 * rgb[:, :, 2]


def _sharpness(gray):
    try:
        import cv2

        return float(cv2.Laplacian(gray.astype(np.float32), cv2.CV_32F).var())
    except Exception:
        gy, gx = np.gradient(gray.astype(np.float32))
        return float((gx.var() + gy.var()) / 2.0)


def _fft_high_frequency_ratio(gray):
    gray = gray.astype(np.float32)
    if gray.size == 0:
        return 0.0
    spectrum = np.fft.fftshift(np.fft.fft2(gray))
    magnitude = np.abs(spectrum)
    h, w = gray.shape[:2]
    yy, xx = np.ogrid[:h, :w]
    cy, cx = h // 2, w // 2
    radius = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    high_mask = radius > min(h, w) * 0.18
    total = float(magnitude.sum())
    if total <= 0:
        return 0.0
    return float(magnitude[high_mask].sum() / total)


def _lbp_texture(gray):
    try:
        from skimage.feature import local_binary_pattern

        lbp = local_binary_pattern(gray.astype(np.uint8), P=8, R=1, method="uniform")
        hist, _ = np.histogram(lbp, bins=np.arange(0, 11), density=True)
        return float(np.clip(np.std(hist) * 4.0, 0.0, 1.0))
    except Exception:
        gy, gx = np.gradient(gray.astype(np.float32))
        return float(np.clip((np.std(gx) + np.std(gy)) / 128.0, 0.0, 1.0))


def _normalize_feature(value, scale):
    return float(np.clip(value / scale, 0.0, 1.0))


def assess_texture_liveness(frame, face_bbox):
    crop, bbox = crop_face(frame, face_bbox)
    gray = _to_gray(crop)
    sharpness = _sharpness(gray)
    fft_ratio = _fft_high_frequency_ratio(gray)
    lbp_texture = _lbp_texture(gray)
    score = float(
        np.clip(
            0.35 * _normalize_feature(sharpness, 250.0)
            + 0.35 * np.clip(fft_ratio * 3.0, 0.0, 1.0)
            + 0.30 * lbp_texture,
            0.0,
            1.0,
        )
    )
    return LivenessResult(
        score=score,
        label=LIVENESS_UNKNOWN,
        reasons=["texture_baseline"],
        details={
            "bbox": bbox,
            "sharpness": sharpness,
            "fft_high_frequency_ratio": fft_ratio,
            "lbp_texture": lbp_texture,
        },
    )


def _get_default_pad_model():
    global _PAD_MODEL_CACHE
    if _PAD_MODEL_CACHE is None:
        from src.pad.minifasnet import MiniFASNetPAD

        _PAD_MODEL_CACHE = MiniFASNetPAD(PAD_MODEL_PATH)
    return _PAD_MODEL_CACHE


def assess_liveness(
    frame,
    landmarks=None,
    face_bbox=None,
    pad_model=None,
    pad_threshold=None,
    rppg_result=None,
):
    if frame is None or not _valid_frame_shape(frame):
        return LivenessResult(
            score=0.0,
            label=LIVENESS_UNKNOWN,
            reasons=["frame_missing"],
            details={},
        )

    bbox, error = _validate_bbox(face_bbox, frame.shape)
    if error:
        return LivenessResult(
            score=0.0,
            label=LIVENESS_UNKNOWN,
            reasons=[error],
            details={"frame_shape": tuple(frame.shape[:2])},
        )

    x1, y1, x2, y2 = bbox
    bbox_area = (x2 - x1) * (y2 - y1)
    crop = frame[y1:y2, x1:x2]
    texture_result = assess_texture_liveness(frame, bbox)
    threshold = PAD_THRESHOLD if pad_threshold is None else float(pad_threshold)
    details = {
        "bbox": bbox,
        "bbox_area": bbox_area,
        "landmarks_present": landmarks is not None,
        "texture": texture_result.details,
        "texture_score": texture_result.score,
    }
    reasons = ["rule_placeholder_live"]

    pad_result = None
    selected_pad_model = pad_model
    if selected_pad_model is None and PASSIVE_PAD_ENABLED:
        selected_pad_model = _get_default_pad_model()
    if selected_pad_model is not None:
        try:
            pad_result = selected_pad_model.predict(crop)
            details["pad"] = {
                "live_score": pad_result.live_score,
                "spoof_score": pad_result.spoof_score,
                "threshold": threshold,
            }
        except Exception as exc:
            from src.pad.minifasnet import PADModelUnavailable

            if isinstance(exc, PADModelUnavailable):
                reasons.append("pad_model_unavailable")
                details["pad_error"] = str(exc)
            else:
                reasons.append("pad_inference_error")
                details["pad_error"] = str(exc)

    if rppg_result is not None:
        details["rppg"] = {
            "label": rppg_result.label,
            "pulse_confidence": rppg_result.pulse_confidence,
            "bpm": rppg_result.bpm,
            "reasons": list(rppg_result.reasons),
            "details": dict(rppg_result.details),
        }

    if pad_result is not None:
        if pad_result.live_score >= threshold:
            reasons.append("pad_live")
            label = LIVENESS_LIVE
        else:
            reasons.append("pad_low_score")
            label = LIVENESS_SPOOF
        return LivenessResult(
            score=float(pad_result.live_score),
            label=label,
            reasons=reasons,
            details=details,
        )

    return LivenessResult(
        score=1.0,
        label=LIVENESS_LIVE,
        reasons=reasons,
        details=details,
    )
