import os
import cv2
import sys
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.face_model import get_face_model

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
TARGET_SIZE = (112, 112)

def preprocess_images():
    if not os.path.exists(RAW_DIR):
        print(f"Error: Directory {RAW_DIR} not found.")
        return

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    person_names = [d for d in os.listdir(RAW_DIR) if os.path.isdir(os.path.join(RAW_DIR, d))]

    if not person_names:
        print(f"No personnel found in {RAW_DIR}")
        return

    for name in person_names:
        person_raw_dir = os.path.join(RAW_DIR, name)
        person_proc_dir = os.path.join(PROCESSED_DIR, name)
        os.makedirs(person_proc_dir, exist_ok=True)

        img_names = [f for f in os.listdir(person_raw_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        print(f"Processing {len(img_names)} images for {name}...")

        valid_count = 0
        face_model = get_face_model()
        for img_name in tqdm(img_names, desc=name):
            img_path = os.path.join(person_raw_dir, img_name)
            out_path = os.path.join(person_proc_dir, img_name)

            try:
                img_bgr = cv2.imread(img_path)
                face_objs = face_model.get_faces(img_bgr)
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

            except Exception as e:
                pass
                
        print(f"Successfully processed {valid_count}/{len(img_names)} for {name}\n")

if __name__ == "__main__":
    preprocess_images()
    print("Preprocessing completed!")
