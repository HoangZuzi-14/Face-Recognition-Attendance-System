import os
import pickle
import numpy as np
from deepface import DeepFace
from tqdm import tqdm

PROCESSED_DIR = "data/processed"
DB_PATH = "data/embeddings/db.pkl"

def build_database():
    if not os.path.exists(PROCESSED_DIR):
        print(f"Error: Directory {PROCESSED_DIR} not found.")
        return

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    person_names = [d for d in os.listdir(PROCESSED_DIR) if os.path.isdir(os.path.join(PROCESSED_DIR, d))]
    
    if not person_names:
        print(f"No processed data found in {PROCESSED_DIR}")
        return

    db = {}

    for name in person_names:
        person_proc_dir = os.path.join(PROCESSED_DIR, name)
        img_names = [f for f in os.listdir(person_proc_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not img_names:
            continue
            
        print(f"Extracting embeddings for {name} ({len(img_names)} images)...")
        embeddings = []
        
        for img_name in tqdm(img_names, desc=name):
            img_path = os.path.join(person_proc_dir, img_name)
            try:
                # Images are already preprocessed, aligned, detection can be skipped
                res = DeepFace.represent(
                    img_path=img_path,
                    model_name="ArcFace",
                    detector_backend="skip",
                    enforce_detection=False
                )
                if res and len(res) > 0:
                    embeddings.append(res[0]["embedding"])
            except Exception as e:
                pass
                
        if embeddings:
            avg_embedding = np.mean(embeddings, axis=0)
            db[name] = avg_embedding
            print(f"  Added {name} to db with {len(embeddings)} valid embeddings.")
        else:
            print(f"  Failed to extract embeddings for {name}.")

    with open(DB_PATH, "wb") as f:
        pickle.dump(db, f)

    print(f"\nDatabase built successfully with {len(db)} identities!")
    print(f"Saved at {DB_PATH}")

if __name__ == "__main__":
    build_database()
