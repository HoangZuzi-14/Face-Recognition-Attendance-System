import cv2
import pickle
import numpy as np
import os
import sys
import time
from deepface import DeepFace
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import log_attendance, get_attended_today_for_class, get_student_by_db_key

DB_PATH = "data/embeddings/db.pkl"
THRESHOLD = 0.35
CONFIDENCE_GAP = 0.05
MODEL_NAME = "ArcFace"
VOTE_WINDOW = 4
VOTE_RATIO = 0.75
SKIP_FRAMES = 2
TRACKER_TIMEOUT = 1.5       # Remove tracker if face not seen for N seconds
MATCH_DISTANCE_PX = 150     # Max pixel distance to match face to existing tracker


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
        self.display_text = "..."
        self.display_color = (0, 255, 255)  # Yellow default

    def update_position(self, cx, cy):
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


# --- Module state ---
face_trackers: list[FaceTracker] = []
frame_counter = 0
_attended_cache = set()
_attended_cache_time = 0


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
    for name, db_embedding in db.items():
        dist = compute_cosine_distance(embedding, db_embedding)
        distances.append((name, dist))
    distances.sort(key=lambda x: x[1])
    if len(distances) >= 2:
        return distances[0], distances[1]
    elif len(distances) == 1:
        return distances[0], ("_none_", 1.0)
    else:
        return ("Unknown", 1.0), ("_none_", 1.0)


def _find_nearest_tracker(cx, cy):
    """Find the closest existing tracker to a face center."""
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


def process_frame(frame, db, class_id=None, deadline_hour=8, deadline_minute=0):
    global frame_counter
    frame_counter += 1

    # Cleanup old trackers
    _cleanup_trackers()

    # Get already-attended set
    attended = _get_attended_set(class_id)

    # Skip frames for performance
    if frame_counter % SKIP_FRAMES != 0:
        # Still draw existing tracker labels
        for tracker in face_trackers:
            if not tracker.is_expired():
                _draw_label(frame, tracker)
        return frame

    # Resize for faster face detection (reduced from 0.25 to 0.5 for stability)
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

    try:
        face_objs = DeepFace.extract_faces(
            img_path=small_frame,
            detector_backend="opencv",
            enforce_detection=False,
            align=True
        )

        matched_tracker_ids = set()

        for face_obj in face_objs:
            facial_area = face_obj["facial_area"]
            if facial_area['w'] == 0 or facial_area['h'] == 0:
                continue

            face_arr = face_obj["face"]

            # Scale back to original frame coords (multiplied by 2 since we resized by 0.5)
            x = facial_area['x'] * 2
            y = facial_area['y'] * 2
            w = facial_area['w'] * 2
            h = facial_area['h'] * 2
            cx = x + w // 2
            cy = y + h // 2

            frame_h, frame_w = frame.shape[:2]
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(frame_w, x + w), min(frame_h, y + h)

            # Find or create tracker
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

            # Extract embedding
            face_bgr = cv2.cvtColor((face_arr * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
            res = DeepFace.represent(
                img_path=face_bgr,
                model_name=MODEL_NAME,
                enforce_detection=False,
                detector_backend="skip"
            )

            if res and len(res) > 0:
                embedding = res[0]["embedding"]
                best, second = find_best_match(embedding, db)
                best_name, best_dist = best
                _, second_dist = second
                gap = second_dist - best_dist

                if best_dist < THRESHOLD and gap > CONFIDENCE_GAP:
                    tracker.add_vote(best_name)
                    display = get_display_name(best_name)

                    # Check if this person already attended
                    if best_name in attended:
                        tracker.confirmed_name = best_name
                        tracker.display_text = f"{display} (PRESENT)"
                        tracker.display_color = (0, 255, 0)
                    else:
                        tracker.display_text = f"{display} ({best_dist:.2f})"
                        tracker.display_color = (0, 255, 255)  # Yellow candidate
                else:
                    tracker.add_vote("Unknown")
                    tracker.display_text = "Unknown"
                    tracker.display_color = (0, 0, 255)

                # Temporal voting
                confirmed = tracker.get_voted_identity()
                if confirmed and confirmed not in attended:
                    if class_id is not None:
                        logged, status = log_attendance(confirmed, class_id,
                                                        round(1 - best_dist, 2),
                                                        deadline_hour, deadline_minute)
                        if logged:
                            # Update cache
                            _attended_cache.add(confirmed)
                            display = get_display_name(confirmed)
                            tracker.confirmed_name = confirmed
                            status_label = status if status else "PRESENT"
                            tracker.display_text = f"{display} ({status_label})"
                            tracker.display_color = (0, 255, 0)
                            tracker.vote_buffer.clear()

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


def reset_trackers():
    """Reset all tracking state."""
    global face_trackers, frame_counter, _attended_cache, _attended_cache_time
    face_trackers.clear()
    frame_counter = 0
    _attended_cache = set()
    _attended_cache_time = 0
    FaceTracker._next_id = 0


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
