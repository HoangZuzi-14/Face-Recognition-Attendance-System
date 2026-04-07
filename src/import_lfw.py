import os
import cv2
from tqdm import tqdm

LFW_SRC = "data/LFW_dataset"
PROCESSED_DIR = "data/processed"
TARGET_SIZE = (112, 112)

def import_lfw():
    if not os.path.exists(LFW_SRC):
        print(f"LFW source path {LFW_SRC} not found!")
        return
        
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    person_folders = [d for d in os.listdir(LFW_SRC) if os.path.isdir(os.path.join(LFW_SRC, d))]
    
    print(f"Found {len(person_folders)} people in LFW. Beginning resize (112x112) & copy to {PROCESSED_DIR}...")
    
    for person in tqdm(person_folders, desc="Importing LFW"):
        src_path = os.path.join(LFW_SRC, person)
        dest_path = os.path.join(PROCESSED_DIR, person)
        
        # If dest folder doesn't exist, we iteratively process images
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
            for file_name in os.listdir(src_path):
                if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(src_path, file_name)
                    out_path = os.path.join(dest_path, file_name)
                    
                    # Read, cleanly resize, and save to output directory
                    img = cv2.imread(img_path)
                    if img is not None:
                        resized = cv2.resize(img, TARGET_SIZE)
                        cv2.imwrite(out_path, resized)
            
    print("\nLFW dataset resized and imported successfully!")

if __name__ == "__main__":
    import_lfw()
