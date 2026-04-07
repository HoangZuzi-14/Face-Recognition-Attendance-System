"""
In-app face registration module.
Provides functions to capture faces from webcam within Streamlit,
preprocess them, extract embeddings, and merge into db.pkl.
"""

import os
import cv2
import numpy as np
import pickle
from deepface import DeepFace

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
DB_PATH = "data/embeddings/db.pkl"
TARGET_SIZE = (112, 112)


def save_captured_frame(person_key, frame, index):
    """Save a single captured frame to raw data directory."""
    person_dir = os.path.join(RAW_DIR, person_key)
    os.makedirs(person_dir, exist_ok=True)
    img_path = os.path.join(person_dir, f"{person_key}_{index:03d}.jpg")
    cv2.imwrite(img_path, frame)
    return img_path


def preprocess_person(person_key):
    """Align + crop face images for a single person.
    Returns number of valid images processed.
    """
    person_raw_dir = os.path.join(RAW_DIR, person_key)
    person_proc_dir = os.path.join(PROCESSED_DIR, person_key)
    os.makedirs(person_proc_dir, exist_ok=True)

    img_names = [f for f in os.listdir(person_raw_dir)
                 if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not img_names:
        return 0

    valid_count = 0
    for img_name in img_names:
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

    return valid_count


def extract_and_merge_embedding(person_key):
    """Extract embedding for one person and merge into existing db.pkl.
    Returns True on success.
    """
    person_proc_dir = os.path.join(PROCESSED_DIR, person_key)
    if not os.path.exists(person_proc_dir):
        return False

    img_names = [f for f in os.listdir(person_proc_dir)
                 if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not img_names:
        return False

    embeddings = []
    for img_name in img_names:
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
        return False

    avg_embedding = np.mean(embeddings, axis=0)

    # Load existing database or create new
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as f:
            db = pickle.load(f)
    else:
        db = {}

    db[person_key] = avg_embedding

    with open(DB_PATH, "wb") as f:
        pickle.dump(db, f)

    return True


def get_existing_count(person_key):
    """Get number of existing raw images for a person."""
    person_dir = os.path.join(RAW_DIR, person_key)
    if not os.path.exists(person_dir):
        return 0
    return len([f for f in os.listdir(person_dir)
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))])


def clear_person_data(person_key):
    """Clear all raw and processed data for a person."""
    import shutil
    raw_dir = os.path.join(RAW_DIR, person_key)
    proc_dir = os.path.join(PROCESSED_DIR, person_key)
    if os.path.exists(raw_dir):
        shutil.rmtree(raw_dir)
    if os.path.exists(proc_dir):
        shutil.rmtree(proc_dir)
