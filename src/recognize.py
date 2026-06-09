import cv2
import pickle
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
    STATIC_FACE_TIMEOUT, RECOGNITION_FRAME_SCALE,
)
from app.database import (
    log_attendance, get_attended_today_for_class, get_student_by_db_key,
    record_recognition_event,
)
from src.face_db import FACE_DB_METADATA_KEY, copy_metadata_if_present, iter_identity_embeddings
from src.face_model import get_face_model

DB_PATH = "data/embeddings/db.pkl"


@dataclass(frozen=True)
class MatchDecision:
    status: str
    confidence: float
    reason: str


def confidence_from_distance(distance):
    return round(max(0.0, min(1.0, 1.0 - float(distance))), 4)


def classify_match(best_dist, gap):
    confidence = confidence_from_distance(best_dist)
    if best_dist < RECOGNITION_THRESHOLD and gap > CONFIDENCE_GAP:
        return MatchDecision("ACCEPT", confidence, "strong_match")
    if best_dist < REVIEW_THRESHOLD:
        return MatchDecision("NEED_REVIEW", confidence, "low_confidence_or_small_gap")
    return MatchDecision("UNKNOWN", confidence, "distance_above_review_threshold")


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
    if not os.path.exists(DB_PATH):
        return None
    with open(DB_PATH, "rb") as f:
        return pickle.load(f)


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

                if decision.status == "ACCEPT":
                    tracker.add_vote(best_name)
                    display = get_display_name(best_name)

                    # Check if this person already attended
                    if best_name in attended:
                        tracker.confirmed_name = best_name
                        tracker.display_text = f"{display} (PRESENT)"
                        tracker.display_color = (0, 255, 0)
                    else:
                        tracker.display_text = f"{display} ({decision.confidence:.2f})"
                        tracker.display_color = (0, 255, 255)  # Yellow candidate
                elif decision.status == "NEED_REVIEW":
                    tracker.add_vote("Unknown")
                    display = get_display_name(best_name)
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
                        )
                else:
                    tracker.add_vote("Unknown")
                    tracker.display_text = "Unknown"
                    tracker.display_color = (0, 0, 255)

                # Temporal voting
                confirmed = tracker.get_voted_identity()
                if confirmed and confirmed not in attended:
                    if class_id is not None:
                        logged, status = log_attendance(confirmed, class_id,
                                                        decision.confidence,
                                                        deadline_hour, deadline_minute)
                        if logged:
                            record_recognition_event(
                                class_id,
                                confirmed,
                                "ACCEPT",
                                decision.confidence,
                                distance=best_dist,
                                gap=gap,
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
