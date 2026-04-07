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
import pickle
import argparse

import cv2
import numpy as np
from deepface import DeepFace
from tqdm import tqdm

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
            face_objs = DeepFace.extract_faces(
                img_path=img_path,
                detector_backend="opencv",
                enforce_detection=True,
                align=True
            )
            if face_objs:
                face_arr = face_objs[0]["face"]
                face_arr = cv2.resize(face_arr, TARGET_SIZE)
                face_bgr = cv2.cvtColor((face_arr * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
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

    for img_name in tqdm(img_names, desc=person_name):
        img_path = os.path.join(person_proc_dir, img_name)
        try:
            res = DeepFace.represent(
                img_path=img_path,
                model_name="ArcFace",
                detector_backend="skip",
                enforce_detection=False
            )
            if res and len(res) > 0:
                embeddings.append(res[0]["embedding"])
        except Exception:
            pass

    if not embeddings:
        print(f"ERROR: Could not extract any embeddings for {person_name}")
        return False

    avg_embedding = np.mean(embeddings, axis=0)

    # Load existing database (or create new)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as f:
            db = pickle.load(f)
        print(f"   Loaded existing database with {len(db)} identities.")
    else:
        db = {}
        print("   No existing database found – creating new one.")

    action = "Updated" if person_name in db else "Added"
    db[person_name] = avg_embedding

    with open(DB_PATH, "wb") as f:
        pickle.dump(db, f)

    print(f"  {action} '{person_name}' in database! ({len(embeddings)} valid embeddings)")
    print(f"   Database now has {len(db)} identities.\n")
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
