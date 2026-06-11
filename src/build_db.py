import os
import sys
import numpy as np
import cv2
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import write_audit_log
from src.embedding_store import save_embeddings_safely
from src.face_db import EMBEDDING_MODEL_ID, identity_count, set_identity_embedding
from src.face_model import get_face_model

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
    face_model = get_face_model()

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
                img_bgr = cv2.imread(img_path)
                embedding = face_model.get_embedding(img_bgr)
                if embedding is not None:
                    embeddings.append(embedding)
            except Exception as e:
                pass
                
        if embeddings:
            avg_embedding = np.mean(embeddings, axis=0)
            set_identity_embedding(db, name, avg_embedding)
            print(f"  Added {name} to db with {len(embeddings)} valid embeddings.")
        else:
            print(f"  Failed to extract embeddings for {name}.")

    result = save_embeddings_safely(db, face_db_path=DB_PATH)
    if not result["ok"]:
        print(f"Failed to save database safely: {result['errors']}")
        return

    print(f"\nDatabase built successfully with {identity_count(db)} identities!")
    print(f"Saved at {DB_PATH}")
    print(f"Embedding model: {EMBEDDING_MODEL_ID}")
    print("NOTE: Rebuild db.pkl after migration; DeepFace/ArcFace embeddings are not compatible with InsightFace embeddings.")
    write_audit_log(
        "embedding.rebuilt",
        entity_type="face_db",
        entity_id=DB_PATH,
        details=f"identities={identity_count(db)};model={EMBEDDING_MODEL_ID}",
    )

if __name__ == "__main__":
    build_database()
