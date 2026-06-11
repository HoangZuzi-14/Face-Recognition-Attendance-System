"""
In-app face registration module.
Provides functions to capture faces from webcam within Streamlit,
preprocess them, extract embeddings, and merge into db.pkl.
"""

import os
import cv2
import numpy as np
from dataclasses import dataclass
from src.face_db import EMBEDDING_MODEL_ID, set_identity_embedding
from src.embedding_store import load_embeddings, save_embeddings_safely
from src.face_model import get_face_model

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
DB_PATH = "data/embeddings/db.pkl"
TARGET_SIZE = (112, 112)


@dataclass
class FaceRegistrationResult:
    ok: bool
    stage: str
    message: str
    valid_images: int = 0


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
    face_model = get_face_model()
    for img_name in img_names:
        img_path = os.path.join(person_proc_dir, img_name)
        try:
            img_bgr = cv2.imread(img_path)
            embedding = face_model.get_embedding(img_bgr)
            if embedding is not None:
                embeddings.append(embedding)
        except Exception:
            pass

    if not embeddings:
        person_raw_dir = os.path.join(RAW_DIR, person_key)
        if os.path.exists(person_raw_dir):
            raw_img_names = [
                f for f in os.listdir(person_raw_dir)
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))
            ]
            for img_name in raw_img_names:
                img_path = os.path.join(person_raw_dir, img_name)
                try:
                    img_bgr = cv2.imread(img_path)
                    embedding = face_model.get_embedding(img_bgr)
                    if embedding is not None:
                        embeddings.append(embedding)
                except Exception:
                    pass

    if not embeddings:
        return False

    avg_embedding = np.mean(embeddings, axis=0)

    # Load existing database or create new
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = load_embeddings(face_db_path=DB_PATH, prefer_sqlite=False) or {}

    set_identity_embedding(db, person_key, avg_embedding)

    result = save_embeddings_safely(db, face_db_path=DB_PATH, required_keys={person_key})
    return bool(result["ok"])


def finalize_face_registration(person_key):
    """Preprocess captured images, extract embeddings, and return a user-facing result."""
    valid = preprocess_person(person_key)
    if valid <= 0:
        return FaceRegistrationResult(
            ok=False,
            stage="preprocess",
            valid_images=valid,
            message=(
                "Khong co anh hop le sau buoc cat/can chinh khuon mat. "
                "Hay chup lai voi anh sang tot hon, nhin thang camera va chi co mot nguoi trong khung hinh."
            ),
        )

    if not extract_and_merge_embedding(person_key):
        return FaceRegistrationResult(
            ok=False,
            stage="embedding",
            valid_images=valid,
            message=(
                f"Da xu ly {valid} anh nhung khong trich xuat duoc embedding. "
                f"Hay chup them anh ro hon hoac kiem tra lai model {EMBEDDING_MODEL_ID}."
            ),
        )

    return FaceRegistrationResult(
        ok=True,
        stage="complete",
        valid_images=valid,
        message=f"Da dang ky khuon mat thanh cong voi {valid} anh hop le.",
    )


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
