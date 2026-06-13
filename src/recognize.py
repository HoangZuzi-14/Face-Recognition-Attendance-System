import cv2
import numpy as np
import os
import sys
import time
import threading
from collections import Counter
from dataclasses import dataclass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.config import (
    RECOGNITION_THRESHOLD, REVIEW_THRESHOLD, CONFIDENCE_GAP,
    VOTE_WINDOW, VOTE_RATIO, SKIP_FRAMES, TRACKER_TIMEOUT, MATCH_DISTANCE_PX,
    STATIC_FACE_TIMEOUT, RECOGNITION_FRAME_SCALE, LIVENESS_ENABLED,
    RPPG_ENABLED, RPPG_WINDOW,
    FACE_DB_PATH,
    PAD_SPOOF_THRESHOLD, PAD_LIVE_THRESHOLD, PAD_VOTING_WINDOW,
)
from app.database import (
    log_attendance, get_attended_today_for_class, get_student_by_db_key,
    record_recognition_event,
)
from src.embedding_store import load_embeddings
from src.face_db import FACE_DB_METADATA_KEY, copy_metadata_if_present, iter_identity_embeddings
from src.face_model import get_face_model
from src.fusion import (
    DECISION_ACCEPT,
    DECISION_CHALLENGE_REQUIRED,
    DECISION_REJECT_SPOOF,
    DECISION_REJECT_UNKNOWN,
    fuse_decision,
)
from src.liveness import (
    LIVENESS_CHALLENGE,
    LIVENESS_LIVE,
    LIVENESS_SPOOF,
    LIVENESS_UNKNOWN,
    LivenessResult,
    assess_liveness,
)
from src.rppg import RppgFrameBuffer, RppgResult, estimate_pulse_from_buffer

DB_PATH = "data/embeddings/db.pkl"


@dataclass(frozen=True)
class MatchDecision:
    status: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class LivenessGateDecision:
    allowed: bool
    decision: str
    result: LivenessResult
    short_reason: str


def confidence_from_distance(distance):
    return round(max(0.0, min(1.0, 1.0 - float(distance))), 4)


def classify_match(best_dist, gap):
    confidence = confidence_from_distance(best_dist)
    if best_dist < RECOGNITION_THRESHOLD and gap > CONFIDENCE_GAP:
        return MatchDecision("ACCEPT", confidence, "strong_match")
    if best_dist < REVIEW_THRESHOLD:
        return MatchDecision("NEED_REVIEW", confidence, "low_confidence_or_small_gap")
    return MatchDecision("UNKNOWN", confidence, "distance_above_review_threshold")


def evaluate_liveness_gate(
    frame,
    face_bbox,
    landmarks=None,
    enabled=None,
    assessor=assess_liveness,
    rppg_result=None,
    tracker=None,
):
    if enabled is None:
        enabled = LIVENESS_ENABLED
    if not enabled:
        result = LivenessResult(
            score=1.0,
            label="DISABLED",
            reasons=["liveness_disabled"],
            details={},
        )
        return LivenessGateDecision(True, "ACCEPT", result, "liveness_disabled")

    try:
        result = assessor(
            frame,
            landmarks=landmarks,
            face_bbox=face_bbox,
            rppg_result=rppg_result,
        )
    except TypeError:
        result = assessor(frame, landmarks=landmarks, face_bbox=face_bbox)
    short_reason = result.reasons[0] if result.reasons else ""
    label = str(result.label).upper()
    pad_score = None
    rppg_confidence = None
    if isinstance(result.details, dict):
        pad_details = result.details.get("pad")
        rppg_confidence = (result.details.get("rppg") or {}).get("pulse_confidence")
        if pad_details and "live_score" in pad_details:
            live_sc = pad_details["live_score"]
            print_sc = pad_details.get("print_score", 0.0)
            replay_sc = pad_details.get("replay_score", 0.0)
            spoof_sc = pad_details.get("spoof_score", 1.0 - live_sc)

            if tracker is not None:
                tracker.liveness_history.append((live_sc, print_sc, replay_sc, spoof_sc))
                if len(tracker.liveness_history) > PAD_VOTING_WINDOW:
                    tracker.liveness_history = tracker.liveness_history[-PAD_VOTING_WINDOW:]

                med_live = float(np.median([h[0] for h in tracker.liveness_history]))
                med_print = float(np.median([h[1] for h in tracker.liveness_history]))
                med_replay = float(np.median([h[2] for h in tracker.liveness_history]))
                med_spoof = float(np.median([h[3] for h in tracker.liveness_history]))
            else:
                med_live = live_sc
                med_print = print_sc
                med_replay = replay_sc
                med_spoof = spoof_sc

            pad_details["live_score"] = med_live
            pad_details["print_score"] = med_print
            pad_details["replay_score"] = med_replay
            pad_details["spoof_score"] = med_spoof

            if med_spoof >= PAD_SPOOF_THRESHOLD:
                label = LIVENESS_SPOOF
                short_reason = "pad_low_score"
            elif med_live >= PAD_LIVE_THRESHOLD:
                label = LIVENESS_LIVE
                short_reason = "pad_live"
            else:
                label = LIVENESS_CHALLENGE
                short_reason = "pad_uncertain"

            result = LivenessResult(
                score=med_live,
                label=label,
                reasons=[short_reason] + result.reasons[1:],
                details=result.details,
            )
            pad_score = med_live
        else:
            pad_score = result.score

    challenge_res = None
    if label == LIVENESS_CHALLENGE:
        challenge_res = "required"
    elif label == LIVENESS_SPOOF:
        challenge_res = "failed"
    elif label == LIVENESS_LIVE:
        challenge_res = "passed"

    if label == LIVENESS_CHALLENGE:
        fusion = fuse_decision(
            recognition_score=1.0,
            recognition_matched=True,
            liveness_score=result.score,
            pad_score=pad_score,
            challenge_result="required",
            rppg_confidence=rppg_confidence,
        )
    elif label == LIVENESS_UNKNOWN:
        fusion = fuse_decision(
            recognition_score=0.0,
            recognition_matched=False,
            liveness_score=result.score,
            pad_score=pad_score,
            rppg_confidence=rppg_confidence,
        )
    else:
        fusion = fuse_decision(
            recognition_score=1.0,
            recognition_matched=True,
            liveness_score=result.score,
            pad_score=pad_score,
            challenge_result=challenge_res,
            rppg_confidence=rppg_confidence,
        )
    if label == LIVENESS_SPOOF and fusion.decision == DECISION_ACCEPT:
        fusion_decision = DECISION_REJECT_SPOOF
    else:
        fusion_decision = fusion.decision
    allowed = fusion_decision == DECISION_ACCEPT
    if fusion_decision not in {
        DECISION_ACCEPT,
        DECISION_REJECT_SPOOF,
        DECISION_REJECT_UNKNOWN,
        DECISION_CHALLENGE_REQUIRED,
    }:
        fusion_decision = DECISION_REJECT_UNKNOWN
    return LivenessGateDecision(allowed, fusion_decision, result, short_reason)


def _liveness_suffix(gate):
    if gate is None or gate.result.label == "DISABLED":
        return ""
    return f" | {gate.result.label} {gate.result.score:.2f} {gate.short_reason}".rstrip()


class FaceTracker:
    """Track a single face across frames using spatial matching."""

    _next_id = 0

    def __init__(self, cx, cy):
        self.id = FaceTracker._next_id
        FaceTracker._next_id += 1
        self.cx = cx
        self.cy = cy
        self.vote_buffer = []
        self.confirmed_name = None
        self.last_seen = time.time()
        self.first_seen = self.last_seen
        self.movement_total = 0.0
        self.last_event_time = 0.0
        self.display_text = "..."
        self.display_color = (0, 255, 255)  # Yellow default
        self.match_identity = None
        self.recognition_score = None
        self.liveness_label = "UNKNOWN"
        self.liveness_score = None
        self.liveness_reason = ""
        self.rppg_buffer = RppgFrameBuffer(RPPG_WINDOW)
        self.liveness_history = []

    def update_position(self, cx, cy):
        self.movement_total += float(np.sqrt((self.cx - cx) ** 2 + (self.cy - cy) ** 2))
        self.cx = cx
        self.cy = cy
        self.last_seen = time.time()

    def add_vote(self, name):
        self.vote_buffer.append(name)
        if len(self.vote_buffer) > VOTE_WINDOW * 3:
            self.vote_buffer = self.vote_buffer[-VOTE_WINDOW * 3:]

    def get_voted_identity(self):
        if len(self.vote_buffer) < VOTE_WINDOW:
            return None
        recent = self.vote_buffer[-VOTE_WINDOW:]
        known = [v for v in recent if v != "Unknown"]
        if not known:
            return None
        counter = Counter(known)
        most_common, count = counter.most_common(1)[0]
        if count >= VOTE_WINDOW * VOTE_RATIO:
            return most_common
        return None

    def is_expired(self):
        return (time.time() - self.last_seen) > TRACKER_TIMEOUT

    def is_static_spoof_risk(self):
        age = time.time() - self.first_seen
        return age > STATIC_FACE_TIMEOUT and self.movement_total < 20.0

    def should_log_event(self, interval=2.0):
        now = time.time()
        if now - self.last_event_time < interval:
            return False
        self.last_event_time = now
        return True


# --- Module state ---
face_trackers: list[FaceTracker] = []
frame_counter = 0
_attended_cache = set()
_attended_cache_time = 0
_tracker_lock = threading.RLock()


def load_db():
    return load_embeddings(face_db_path=DB_PATH, sqlite_db_path="app/attendance.db", prefer_sqlite=True)


def reload_db():
    """Reload database from disk (used after adding a new person)."""
    return load_db()


def compute_cosine_distance(vec1, vec2):
    a = np.array(vec1)
    b = np.array(vec2)
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def find_best_match(embedding, db):
    distances = []
    for name, db_embedding in iter_identity_embeddings(db):
        dist = compute_cosine_distance(embedding, db_embedding)
        distances.append((name, dist))
    distances.sort(key=lambda x: x[1])
    if len(distances) >= 2:
        return distances[0], distances[1]
    elif len(distances) == 1:
        return distances[0], ("_none_", 1.0)
    else:
        return ("Unknown", 1.0), ("_none_", 1.0)


def filter_face_db(db, allowed_keys):
    """Limit matching candidates to linked students in the selected class."""
    if allowed_keys is None:
        return db
    filtered = {name: embedding for name, embedding in iter_identity_embeddings(db) if name in allowed_keys}
    if FACE_DB_METADATA_KEY in db:
        copy_metadata_if_present(db, filtered)
    return filtered


def scale_bbox_to_frame(bbox, scale, frame_shape):
    """Scale a bbox from resized inference coordinates back to the camera frame."""
    if scale <= 0:
        raise ValueError("scale must be positive")
    frame_h, frame_w = frame_shape[:2]
    inv_scale = 1.0 / scale
    x1, y1, x2, y2 = [int(round(value * inv_scale)) for value in bbox]
    return (
        max(0, x1),
        max(0, y1),
        min(frame_w, x2),
        min(frame_h, y2),
    )


def _find_nearest_tracker(cx, cy):
    """Find the closest existing tracker to a face center."""
    with _tracker_lock:
        best_tracker = None
        best_dist = float('inf')
        for tracker in face_trackers:
            dist = np.sqrt((tracker.cx - cx) ** 2 + (tracker.cy - cy) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_tracker = tracker
        if best_dist < MATCH_DISTANCE_PX:
            return best_tracker
    return None


def _cleanup_trackers():
    """Remove expired trackers."""
    global face_trackers
    with _tracker_lock:
        face_trackers = [t for t in face_trackers if not t.is_expired()]


def _get_attended_set(class_id):
    """Get attended set with caching (refresh every 2 seconds)."""
    global _attended_cache, _attended_cache_time
    now = time.time()
    if now - _attended_cache_time > 2.0:
        if class_id is not None:
            _attended_cache = get_attended_today_for_class(class_id)
        else:
            _attended_cache = set()
        _attended_cache_time = now
    return _attended_cache


def get_display_name(db_key):
    """Get display name: full_name if linked, otherwise db_key."""
    student = get_student_by_db_key(db_key)
    if student:
        return student["full_name"]
    return db_key


def _update_tracker_match(tracker, identity, recognition_score, gate=None):
    tracker.match_identity = identity
    tracker.recognition_score = recognition_score
    if gate is None:
        tracker.liveness_label = "UNKNOWN"
        tracker.liveness_score = None
        tracker.liveness_reason = ""
        return
    tracker.liveness_label = gate.result.label
    tracker.liveness_score = gate.result.score
    tracker.liveness_reason = gate.short_reason


def _record_liveness_event(class_id, best_name, gate, decision, best_dist, gap):
    attack_type = "presentation_attack" if gate.result.label == LIVENESS_SPOOF else None
    pad_details = gate.result.details.get("pad") or {}
    live_sc = pad_details.get("live_score")
    print_sc = pad_details.get("print_score")
    replay_sc = pad_details.get("replay_score")
    spoof_sc = pad_details.get("spoof_score")
    record_recognition_event(
        class_id,
        best_name,
        gate.decision,
        decision.confidence,
        distance=best_dist,
        gap=gap,
        liveness_score=gate.result.score,
        liveness_label=gate.result.label,
        attack_type=attack_type,
        liveness_reasons=gate.result.reasons,
        recognition_score=decision.confidence,
        live_score=live_sc,
        print_score=print_sc,
        replay_score=replay_sc,
        spoof_score=spoof_sc,
        attendance_logged=0,
    )


def _update_rppg_result(tracker, frame, face_bbox):
    if not RPPG_ENABLED:
        return None
    try:
        tracker.rppg_buffer.add_frame(frame, face_bbox, timestamp=time.time())
        return estimate_pulse_from_buffer(tracker.rppg_buffer)
    except Exception as exc:
        return RppgResult(
            label="UNKNOWN",
            pulse_confidence=0.0,
            reasons=["rppg_error"],
            details={"error": str(exc)},
        )


def process_frame(
    frame,
    db,
    class_id=None,
    deadline_hour=8,
    deadline_minute=0,
    respect_skip=True,
    frame_scale=None,
):
    global frame_counter
    frame_counter += 1
    scale = frame_scale if frame_scale is not None else RECOGNITION_FRAME_SCALE

    # Cleanup old trackers
    _cleanup_trackers()

    # Get already-attended set
    attended = _get_attended_set(class_id)

    # Skip frames for performance
    if respect_skip and frame_counter % SKIP_FRAMES != 0:
        # Still draw existing tracker labels
        for tracker in face_trackers:
            if not tracker.is_expired():
                _draw_label(frame, tracker)
        return frame

    small_frame = cv2.resize(
        frame,
        (0, 0),
        fx=scale,
        fy=scale,
    )

    try:
        face_objs = get_face_model().get_faces(small_frame)

        matched_tracker_ids = set()

        for face_obj in face_objs:
            x_small, y_small, x2_small, y2_small = face_obj["bbox"]
            w_small = x2_small - x_small
            h_small = y2_small - y_small
            if w_small <= 0 or h_small <= 0:
                continue

            x1, y1, x2, y2 = scale_bbox_to_frame(
                (x_small, y_small, x2_small, y2_small),
                scale,
                frame.shape,
            )
            w = x2 - x1
            h = y2 - y1
            cx = x1 + w // 2
            cy = y1 + h // 2

            if w <= 0 or h <= 0:
                continue

            # Find or create tracker
            with _tracker_lock:
                tracker = _find_nearest_tracker(cx, cy)
                if tracker and tracker.id not in matched_tracker_ids:
                    tracker.update_position(cx, cy)
                    matched_tracker_ids.add(tracker.id)
                else:
                    tracker = FaceTracker(cx, cy)
                    face_trackers.append(tracker)
                    matched_tracker_ids.add(tracker.id)

                # Store bbox for drawing
                tracker.bbox = (x1, y1, x2, y2)

            # If already confirmed and attended, just show green label
            if tracker.confirmed_name and tracker.confirmed_name in attended:
                display = get_display_name(tracker.confirmed_name)
                tracker.display_text = f"{display} (PRESENT)"
                tracker.display_color = (0, 255, 0)
                _draw_label(frame, tracker)
                continue

            embedding = face_obj["embedding"]
            if embedding is not None:
                best, second = find_best_match(embedding, db)
                best_name, best_dist = best
                _, second_dist = second
                gap = second_dist - best_dist

                decision = classify_match(best_dist, gap)
                display = get_display_name(best_name)
                liveness_gate = None

                if decision.status == "ACCEPT":
                    rppg_result = _update_rppg_result(
                        tracker,
                        frame,
                        (x1, y1, x2, y2),
                    )
                    liveness_gate = evaluate_liveness_gate(
                        frame,
                        face_bbox=(x1, y1, x2, y2),
                        landmarks=face_obj.get("landmarks"),
                        rppg_result=rppg_result,
                        tracker=tracker,
                    )
                    _update_tracker_match(
                        tracker,
                        display,
                        decision.confidence,
                        liveness_gate,
                    )

                    if not liveness_gate.allowed:
                        tracker.add_vote("Unknown")
                        tracker.display_text = (
                            f"{display} ({decision.confidence:.2f})"
                            f"{_liveness_suffix(liveness_gate)}"
                        )
                        tracker.display_color = (
                            (0, 0, 255)
                            if liveness_gate.decision == DECISION_REJECT_SPOOF
                            else (0, 165, 255)
                        )
                        if class_id is not None and tracker.should_log_event():
                            _record_liveness_event(
                                class_id,
                                best_name,
                                liveness_gate,
                                decision,
                                best_dist,
                                gap,
                            )
                        _draw_label(frame, tracker)
                        continue

                    tracker.add_vote(best_name)

                    # Check if this person already attended
                    if best_name in attended:
                        tracker.confirmed_name = best_name
                        tracker.display_text = f"{display} (PRESENT){_liveness_suffix(liveness_gate)}"
                        tracker.display_color = (0, 255, 0)
                    else:
                        tracker.display_text = (
                            f"{display} ({decision.confidence:.2f})"
                            f"{_liveness_suffix(liveness_gate)}"
                        )
                        tracker.display_color = (0, 255, 255)  # Yellow candidate
                elif decision.status == "NEED_REVIEW":
                    _update_tracker_match(tracker, display, decision.confidence)
                    tracker.add_vote("Unknown")
                    tracker.display_text = f"REVIEW {display} ({decision.confidence:.2f})"
                    tracker.display_color = (0, 165, 255)
                    if class_id is not None and tracker.should_log_event():
                        record_recognition_event(
                            class_id,
                            best_name,
                            "NEED_REVIEW",
                            decision.confidence,
                            distance=best_dist,
                            gap=gap,
                            liveness_score=None,
                            liveness_label=None,
                            liveness_reasons=None,
                            recognition_score=decision.confidence,
                            live_score=None,
                            print_score=None,
                            replay_score=None,
                            spoof_score=None,
                            attendance_logged=0,
                        )
                else:
                    _update_tracker_match(tracker, "Unknown", decision.confidence)
                    tracker.add_vote("Unknown")
                    tracker.display_text = "Unknown"
                    tracker.display_color = (0, 0, 255)

                # Temporal voting
                confirmed = tracker.get_voted_identity()
                if decision.status == "ACCEPT" and liveness_gate.allowed and confirmed and confirmed not in attended:
                    if class_id is not None:
                        logged, status = log_attendance(confirmed, class_id,
                                                        decision.confidence,
                                                        deadline_hour, deadline_minute)
                        if logged:
                            event_liveness = liveness_gate.result if liveness_gate else None
                            pad_details = event_liveness.details.get("pad") if event_liveness else None
                            if pad_details:
                                live_sc = pad_details.get("live_score")
                                print_sc = pad_details.get("print_score")
                                replay_sc = pad_details.get("replay_score")
                                spoof_sc = pad_details.get("spoof_score")
                            else:
                                live_sc = None
                                print_sc = None
                                replay_sc = None
                                spoof_sc = None
                            record_recognition_event(
                                class_id,
                                confirmed,
                                "ACCEPT",
                                decision.confidence,
                                distance=best_dist,
                                gap=gap,
                                liveness_score=event_liveness.score if event_liveness else None,
                                liveness_label=event_liveness.label if event_liveness else None,
                                liveness_reasons=event_liveness.reasons if event_liveness else None,
                                recognition_score=decision.confidence,
                                live_score=live_sc,
                                print_score=print_sc,
                                replay_score=replay_sc,
                                spoof_score=spoof_sc,
                                attendance_logged=1,
                            )
                            # Update cache
                            _attended_cache.add(confirmed)
                            display = get_display_name(confirmed)
                            tracker.confirmed_name = confirmed
                            status_label = status if status else "PRESENT"
                            tracker.display_text = f"{display} ({status_label})"
                            tracker.display_color = (0, 255, 0)
                            tracker.vote_buffer.clear()

                if tracker.is_static_spoof_risk():
                    tracker.display_text = f"{tracker.display_text} | LIVE?"
                    tracker.display_color = (0, 165, 255)

            _draw_label(frame, tracker)

    except Exception:
        import traceback
        traceback.print_exc()

    return frame


def _draw_label(frame, tracker):
    """Draw bounding box and label for a tracked face."""
    if not hasattr(tracker, 'bbox'):
        return
    x1, y1, x2, y2 = tracker.bbox
    color = tracker.display_color
    text = tracker.display_text

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(frame, text, (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def draw_tracker_labels(frame):
    """Draw the latest tracker labels without running detection or recognition."""
    _cleanup_trackers()
    with _tracker_lock:
        trackers = list(face_trackers)
    for tracker in trackers:
        if not tracker.is_expired():
            _draw_label(frame, tracker)
    return frame


def get_tracker_hud_snapshot():
    """Return the most recent tracker status for the native camera HUD."""
    _cleanup_trackers()
    with _tracker_lock:
        trackers = [tracker for tracker in face_trackers if not tracker.is_expired()]
    if not trackers:
        return None
    tracker = max(trackers, key=lambda item: item.last_seen)
    return {
        "identity": tracker.match_identity or "Unknown",
        "recognition_score": tracker.recognition_score,
        "liveness_label": tracker.liveness_label,
        "liveness_score": tracker.liveness_score,
        "liveness_reason": tracker.liveness_reason,
        "display_text": tracker.display_text,
    }


def reset_trackers():
    """Reset all tracking state."""
    global face_trackers, frame_counter, _attended_cache, _attended_cache_time
    with _tracker_lock:
        face_trackers.clear()
        FaceTracker._next_id = 0
    frame_counter = 0
    _attended_cache = set()
    _attended_cache_time = 0


def run_recognition():
    db = load_db()
    if db is None:
        print("Database not found! Please run build_db.py first.")
        return

    cap = cv2.VideoCapture(0)
    print("Starting webcam... Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame = process_frame(frame, db)
        cv2.imshow("Real-Time Face Attendance", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_recognition()
