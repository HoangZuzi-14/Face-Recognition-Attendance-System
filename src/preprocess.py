import os
import cv2
import numpy as np
from deepface import DeepFace
from tqdm import tqdm

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
        for img_name in tqdm(img_names, desc=name):
            img_path = os.path.join(person_raw_dir, img_name)
            out_path = os.path.join(person_proc_dir, img_name)

            try:
                # Extract faces, align them (target_size is not supported in this DeepFace version)
                face_objs = DeepFace.extract_faces(
                    img_path=img_path,
                    detector_backend="opencv",
                    enforce_detection=True,
                    align=True
                )
                
                if face_objs:
                    # face_objs is a list. take the first face found.
                    # face is an RGB array with float32 values [0, 1]
                    face_arr = face_objs[0]["face"]
                    face_arr = cv2.resize(face_arr, TARGET_SIZE)
                    face_bgr = cv2.cvtColor((face_arr * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
                    cv2.imwrite(out_path, face_bgr)
                    valid_count += 1

            except Exception as e:
                # Face not detected
                pass
                
        print(f"Successfully processed {valid_count}/{len(img_names)} for {name}\n")

if __name__ == "__main__":
    preprocess_images()
    print("Preprocessing completed!")
