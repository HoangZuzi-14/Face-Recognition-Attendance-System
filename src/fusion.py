"""Score-level fusion for final attendance decisions."""

from dataclasses import dataclass, field

DECISION_ACCEPT = "ACCEPT"
DECISION_REJECT_SPOOF = "REJECT_SPOOF"
DECISION_REJECT_UNKNOWN = "REJECT_UNKNOWN"
DECISION_CHALLENGE_REQUIRED = "CHALLENGE_REQUIRED"


@dataclass(frozen=True)
class FusionResult:
    decision: str
    score: float
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _score(value, default=None):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def fuse_decision(
    recognition_score,
    recognition_matched,
    liveness_score=None,
    pad_score=None,
    challenge_result=None,
    rppg_confidence=None,
    quality_score=None,
    recognition_threshold=0.65,
    liveness_threshold=0.70,
    pad_threshold=0.70,
    pad_spoof_threshold=0.35,
    rppg_threshold=0.15,
    quality_threshold=0.20,
):
    """Fuse recognition and liveness signals into a final decision."""
    recognition_score = _score(recognition_score, 0.0)
    liveness_score = _score(liveness_score)
    pad_score = _score(pad_score)
    rppg_confidence = _score(rppg_confidence)
    quality_score = _score(quality_score)
    challenge = str(challenge_result or "").strip().lower()
    details = {
        "recognition_score": recognition_score,
        "recognition_matched": bool(recognition_matched),
        "liveness_score": liveness_score,
        "pad_score": pad_score,
        "challenge_result": challenge or None,
        "rppg_confidence": rppg_confidence,
        "quality_score": quality_score,
        "thresholds": {
            "recognition": recognition_threshold,
            "liveness": liveness_threshold,
            "pad": pad_threshold,
            "pad_spoof": pad_spoof_threshold,
            "rppg": rppg_threshold,
            "quality": quality_threshold,
        },
    }

    if not recognition_matched or recognition_score < recognition_threshold:
        return FusionResult(
            DECISION_REJECT_UNKNOWN,
            recognition_score,
            ["recognition_no_match"],
            details,
        )

    if challenge in {"failed", "fail", "spoof"}:
        return FusionResult(
            DECISION_REJECT_SPOOF,
            min(recognition_score, liveness_score or 0.0),
            ["challenge_failed"],
            details,
        )
    if challenge in {"required", "pending", "challenge"}:
        return FusionResult(
            DECISION_CHALLENGE_REQUIRED,
            recognition_score,
            ["challenge_required"],
            details,
        )

    if quality_score is not None and quality_score < quality_threshold:
        return FusionResult(
            DECISION_REJECT_UNKNOWN,
            min(recognition_score, quality_score),
            ["quality_low"],
            details,
        )

    if pad_score is not None:
        if pad_score < pad_spoof_threshold:
            return FusionResult(
                DECISION_REJECT_SPOOF,
                min(recognition_score, pad_score),
                ["pad_spoof_score"],
                details,
            )
        if pad_score < pad_threshold and challenge not in {"passed", "pass", "live"}:
            return FusionResult(
                DECISION_CHALLENGE_REQUIRED,
                min(recognition_score, pad_score),
                ["pad_suspicious"],
                details,
            )

    if liveness_score is not None and liveness_score < liveness_threshold:
        return FusionResult(
            DECISION_REJECT_SPOOF,
            min(recognition_score, liveness_score),
            ["liveness_low_score"],
            details,
        )

    if rppg_confidence is not None and rppg_confidence < rppg_threshold:
        return FusionResult(
            DECISION_CHALLENGE_REQUIRED,
            min(recognition_score, rppg_confidence),
            ["rppg_low_confidence"],
            details,
        )

    fused_score = min(
        score
        for score in [
            recognition_score,
            liveness_score if liveness_score is not None else 1.0,
            pad_score if pad_score is not None else 1.0,
            quality_score if quality_score is not None else 1.0,
        ]
    )
    return FusionResult(
        DECISION_ACCEPT,
        fused_score,
        ["live_clear"],
        details,
    )
