"""
add_person.py  –  Add a single person to the face attendance database.

Usage:
    python src/add_person.py
    python src/add_person.py --name Nguyen_Van_A --num 30

This script does everything in one shot:
  1. Collect face images from webcam  (data/raw/<name>/)
  2. Preprocess (align + crop)         (data/processed/<name>/)
  3. Extract embedding & merge into    (data/embeddings/db.pkl)

No need to rebuild the entire database!
"""

import os
import sys
import argparse

import cv2
import numpy as np
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.embedding_store import load_embeddings, save_embeddings_safely
from src.face_db import EMBEDDING_MODEL_ID, identity_count, set_identity_embedding
from src.face_model import get_face_model

RAW_DIR       = "data/raw"
PROCESSED_DIR = "data/processed"
DB_PATH       = "data/embeddings/db.pkl"
TARGET_SIZE   = (112, 112)


def collect_faces(person_name, num_images=50):
    """Open webcam and let the user capture face images."""
    person_dir = os.path.join(RAW_DIR, person_name)
    os.makedirs(person_dir, exist_ok=True)

    # Check if images already exist
    existing = [f for f in os.listdir(person_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if existing:
        print(f"\nFound {len(existing)} existing images for '{person_name}' in {person_dir}")
        choice = input("   Overwrite (o) / Append more (a) / Skip collection (s)? [o/a/s]: ").strip().lower()
        if choice == 's':
            print("   Skipping collection, using existing images.\n")
            return len(existing)
        elif choice == 'o':
            for f in existing:
                os.remove(os.path.join(person_dir, f))
            print("   Cleared old images.\n")
            start_idx = 0
        else:  # append
            start_idx = len(existing)
            num_images = num_images  # collect more on top
            print(f"   Will append starting from index {start_idx}.\n")
    else:
        start_idx = 0

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam!")
        return 0

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    count = 0
    print(f"  Collecting images for: {person_name}")
    print("   Press SPACE to capture | Q to finish early\n")

    while count < num_images:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.putText(frame, f"Captured: {count}/{num_images}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, "SPACE=capture  Q=quit", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.imshow("Add Person – Collect Data", frame)

        key = cv2.waitKey(1)
        if key == ord(' '):
            if len(faces) > 0:
                idx = start_idx + count
                img_path = os.path.join(person_dir, f"{person_name}_{idx:03d}.jpg")
                cv2.imwrite(img_path, frame)
                count += 1
                print(f"  [{count}/{num_images}] Saved: {img_path}")
            else:
                print("  No face detected - try again!")
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    total = start_idx + count
    print(f"\n  Collection done! Total images for '{person_name}': {total}\n")
    return total



def preprocess_person(person_name):
    """Align + crop face images for a single person."""
    person_raw_dir = os.path.join(RAW_DIR, person_name)
    person_proc_dir = os.path.join(PROCESSED_DIR, person_name)
    os.makedirs(person_proc_dir, exist_ok=True)

    img_names = [f for f in os.listdir(person_raw_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not img_names:
        print(f"No images found for {person_name} in {person_raw_dir}")
        return 0

    print(f" Preprocessing {len(img_names)} images for {person_name}...")
    valid_count = 0

    for img_name in tqdm(img_names, desc=person_name):
        img_path = os.path.join(person_raw_dir, img_name)
        out_path = os.path.join(person_proc_dir, img_name)

        try:
            img_bgr = cv2.imread(img_path)
            face_objs = get_face_model().get_faces(img_bgr)
            if face_objs:
                face = max(face_objs, key=lambda item: item["det_score"])
                x1, y1, x2, y2 = face["bbox"]
                frame_h, frame_w = img_bgr.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame_w, x2), min(frame_h, y2)
                if x2 <= x1 or y2 <= y1:
                    continue
                face_bgr = cv2.resize(img_bgr[y1:y2, x1:x2], TARGET_SIZE)
                cv2.imwrite(out_path, face_bgr)
                valid_count += 1
        except Exception:
            pass

    print(f"  Preprocessed {valid_count}/{len(img_names)} images for {person_name}\n")
    return valid_count



def add_to_database(person_name):
    """Extract embedding for one person and merge into existing db.pkl."""
    person_proc_dir = os.path.join(PROCESSED_DIR, person_name)
    if not os.path.exists(person_proc_dir):
        print(f"ERROR: No processed images at {person_proc_dir}")
        return False

    img_names = [f for f in os.listdir(person_proc_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not img_names:
        print(f"No processed images found for {person_name}")
        return False

    print(f"  Extracting embeddings for {person_name} ({len(img_names)} images)...")
    embeddings = []
    face_model = get_face_model()

    for img_name in tqdm(img_names, desc=person_name):
        img_path = os.path.join(person_proc_dir, img_name)
        try:
            img_bgr = cv2.imread(img_path)
            embedding = face_model.get_embedding(img_bgr)
            if embedding is not None:
                embeddings.append(embedding)
        except Exception:
            pass

    if not embeddings:
        print(f"ERROR: Could not extract any embeddings for {person_name}")
        return False

    avg_embedding = np.mean(embeddings, axis=0)

    # Load existing database (or create new)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        db = load_embeddings(face_db_path=DB_PATH, prefer_sqlite=False)
        print(f"   Loaded existing database with {identity_count(db)} identities.")
    else:
        db = {}
        print("   No existing database found – creating new one.")

    action = "Updated" if person_name in db else "Added"
    set_identity_embedding(db, person_name, avg_embedding)

    result = save_embeddings_safely(db, face_db_path=DB_PATH, required_keys={person_name})
    if not result["ok"]:
        print(f"ERROR: Safe embedding save failed: {result['errors']}")
        return False

    print(f"  {action} '{person_name}' in database! ({len(embeddings)} valid embeddings)")
    print(f"   Database now has {identity_count(db)} identities.")
    print(f"   Embedding model: {EMBEDDING_MODEL_ID}")
    print("   NOTE: Rebuild db.pkl after migration; DeepFace/ArcFace embeddings are not compatible with InsightFace embeddings.\n")
    return True



def main():
    parser = argparse.ArgumentParser(description="Add a single person to the face attendance database.")
    parser.add_argument("--name", type=str, help="Person name (no spaces, e.g. Nguyen_Van_A)")
    parser.add_argument("--num", type=int, default=50, help="Number of images to capture (default: 50)")
    parser.add_argument("--skip-collect", action="store_true", help="Skip webcam collection (use existing raw images)")
    parser.add_argument("--skip-preprocess", action="store_true", help="Skip preprocessing (use existing processed images)")
    args = parser.parse_args()

    name = args.name
    if not name:
        name = input("Enter person name (no spaces, e.g. Nguyen_Van_A): ").strip()
    if not name:
        print("Invalid name!")
        return

    print("=" * 60)
    print(f"  Adding person: {name}")
    print("=" * 60)

    # Step 1: Collect
    if not args.skip_collect:
        total = collect_faces(name, num_images=args.num)
        if total == 0:
            print("No images collected. Aborting.")
            return
    else:
        print(" Skipping collection (--skip-collect)\n")

    # Step 2: Preprocess
    if not args.skip_preprocess:
        valid = preprocess_person(name)
        if valid == 0:
            print("No images preprocessed successfully. Aborting.")
            return
    else:
        print("  Skipping preprocessing (--skip-preprocess)\n")

    # Step 3: Add to database
    success = add_to_database(name)

    if success:
        print("=" * 60)
        print(f" '{name}' has been added successfully!")
        print(f"  You can now use the attendance system immediately.")
        print("=" * 60)
    else:
        print("  Failed to add person to database.")


if __name__ == "__main__":
    main()
