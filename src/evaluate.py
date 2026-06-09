import os
import numpy as np
import time
import cv2
import sys
from itertools import combinations, product
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.face_db import EMBEDDING_MODEL_ID
from src.face_model import get_face_model

PROCESSED_DIR = "data/processed"
MODEL_NAME = EMBEDDING_MODEL_ID

def compute_cosine_distance(vec1, vec2):
    a = np.array(vec1)
    b = np.array(vec2)
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def extract_all_embeddings():
    person_names = [d for d in os.listdir(PROCESSED_DIR) if os.path.isdir(os.path.join(PROCESSED_DIR, d))]
    embeddings_dict = {}
    face_model = get_face_model()
    
    for name in person_names:
        person_proc_dir = os.path.join(PROCESSED_DIR, name)
        img_names = [f for f in os.listdir(person_proc_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        emb_list = []
        for img in tqdm(img_names, desc=f"Embedding {name}"):
            img_path = os.path.join(person_proc_dir, img)
            try:
                img_bgr = cv2.imread(img_path)
                embedding = face_model.get_embedding(img_bgr)
                if embedding is not None:
                    emb_list.append(embedding)
            except Exception:
                pass
        embeddings_dict[name] = emb_list
        
    return embeddings_dict

def evaluate():
    if not os.path.exists(PROCESSED_DIR):
        print(f"Error: {PROCESSED_DIR} not found.")
        return
        
    print("Step 1: Extracting embeddings for evaluation...")
    embeddings_dict = extract_all_embeddings()
    names = list(embeddings_dict.keys())
    
    if len(names) < 2:
        print("At least 2 individuals are needed in data/processed/ for proper FAR/FRR evaluation.")
        return
        
    print("\nStep 2: Generating Genuine and Impostor Pairs...")
    genuine_distances = []
    impostor_distances = []
    
    for name, embs in embeddings_dict.items():
        # Genuine pairs
        for emb1, emb2 in combinations(embs, 2):
            dist = compute_cosine_distance(emb1, emb2)
            genuine_distances.append(dist)
            
    for name1, name2 in combinations(names, 2):
        # Impostor pairs
        for emb1, emb2 in product(embeddings_dict[name1], embeddings_dict[name2]):
            dist = compute_cosine_distance(emb1, emb2)
            impostor_distances.append(dist)
            
    print(f"Generated {len(genuine_distances)} genuine pairs.")
    print(f"Generated {len(impostor_distances)} impostor pairs.")
    
    y_true = [1] * len(genuine_distances) + [0] * len(impostor_distances)
    y_scores = genuine_distances + impostor_distances
    
    # We want similarity, but we have distance. Invert distance for roc_curve where higher score = more positive
    y_scores = [-d for d in y_scores]
    
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    # Thresholds are also inverted back
    thresholds = [-t for t in thresholds]
    
    frr = 1 - tpr
    far = fpr
    
    eer_index = np.nanargmin(np.absolute(far - frr))
    eer = far[eer_index]
    eer_threshold = thresholds[eer_index]
    
    print("\nStep 3: Calculating Metrics...")
    print(f"Equal Error Rate (EER): {eer*100:.2f}%")
    print(f"Optimal Threshold for EER: {eer_threshold:.4f}")
    
    # Latency check
    print("\nStep 4: Checking Latency...")
    dummy_img = np.zeros((112, 112, 3), dtype=np.uint8)
    face_model = get_face_model()
    start = time.time()
    for _ in range(10):
        face_model.get_embedding(dummy_img)
    end = time.time()
    latency = (end - start) / 10 * 1000
    print(f"Average Inference Latency ({MODEL_NAME} dummy): {latency:.2f} ms")
    
    # Plot ROC Curve
    plt.figure()
    plt.plot(fpr, tpr, label=f'ROC curve (area = {auc(fpr, tpr):.2f})')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate (FAR)')
    plt.ylabel('True Positive Rate (1 - FRR)')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.savefig('report/roc_curve.png')
    print("Saved ROC curve to report/roc_curve.png")

if __name__ == "__main__":
    os.makedirs('report', exist_ok=True)
    evaluate()
