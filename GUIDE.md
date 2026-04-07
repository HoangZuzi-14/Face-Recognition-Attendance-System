# Face Recognition Attendance System — Project Guide

> Stack: Python 3.12 · DeepFace · OpenCV · SQLite · Streamlit  
> Team: 2 people · OS: Windows · Hardware: CPU only  
> Course: IT4432 Biometric Systems — HUST  

---

## Project Overview

Build a **face recognition-based attendance system** that:
1. Collects face data via webcam
2. Builds an embedding database using DeepFace (ArcFace model)
3. Recognizes faces in real-time and logs attendance to SQLite
4. Provides a Streamlit UI for live demo and attendance report export
5. Evaluates performance with FAR, FRR, EER, ROC curve

---

## Folder Structure

```
face_attendance/
├── data/
│   ├── raw/                  # Original captured images, one folder per person
│   │   ├── john_doe/
│   │   │   ├── john_doe_000.jpg
│   │   │   └── ...
│   │   └── jane_doe/
│   ├── processed/            # Aligned/cropped face images (output of preprocess)
│   └── embeddings/
│       └── db.pkl            # Serialized embedding database
├── models/                   # Saved model weights (if fine-tuned)
├── src/
│   ├── collect_data.py       # Webcam capture tool
│   ├── preprocess.py         # Face detection, alignment, normalization
│   ├── build_db.py           # Extract embeddings and build db.pkl
│   ├── recognize.py          # Real-time recognition via webcam
│   └── evaluate.py           # FAR, FRR, EER, ROC curve computation
├── app/
│   ├── app.py                # Streamlit UI — live camera + attendance log
│   └── database.py           # SQLite CRUD for students and attendance
├── notebooks/
│   └── eda.ipynb             # Exploratory analysis, visualizations
├── report/                   # Technical report + slides
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Tech Stack & Rationale

| Component | Library | Why |
|-----------|---------|-----|
| Face detection | OpenCV Haar Cascade | Lightweight, CPU-friendly |
| Face embedding | DeepFace + ArcFace | State-of-art accuracy, no compile needed |
| Distance metric | Cosine similarity | Better than Euclidean for high-dim embeddings |
| Attendance DB | SQLite | Zero setup, file-based, enough for demo |
| UI | Streamlit | Fast to build, looks clean for demo |
| Evaluation | scikit-learn + matplotlib | ROC curve, metrics |

**Why DeepFace over face_recognition/dlib:**  
`dlib` requires C++ compilation on Windows — too error-prone. DeepFace wraps multiple pretrained models (ArcFace, Facenet, VGG-Face) and installs cleanly via pip.

---

## Pipeline

```
Webcam / Dataset
      │
      ▼
[1] collect_data.py        — capture 50 images per person via webcam
      │
      ▼
[2] preprocess.py          — detect face → align → crop → normalize → save to data/processed/
      │
      ▼
[3] build_db.py            — extract 512-d ArcFace embedding per image → average per person → save db.pkl
      │
      ▼
[4] recognize.py           — load db.pkl → webcam frame → embed → cosine similarity → identity / unknown
      │
      ▼
[5] app.py                 — Streamlit UI wrapping recognize.py + log to SQLite + export CSV
      │
      ▼
[6] evaluate.py            — compute FAR, FRR, EER, draw ROC curve, measure latency
```

---

## Key Parameters

```python
THRESHOLD = 0.40          # Cosine distance cutoff — below = same person
MODEL_NAME = "ArcFace"    # DeepFace model: ArcFace | Facenet | VGG-Face
DETECTOR = "opencv"       # Face detector backend: opencv | retinaface | mtcnn
IMG_SIZE = (112, 112)     # Standard input size for ArcFace
MIN_IMAGES = 30           # Minimum images per person for reliable embedding
```

**Tuning threshold:**
- Lower threshold → stricter → more FRR, less FAR
- Higher threshold → looser → more FAR, less FRR
- Sweet spot (EER point) found from ROC curve in `evaluate.py`

---

## Files — Implementation Plan

### `src/collect_data.py`
- Open webcam with OpenCV
- Detect face with Haar Cascade
- On SPACE press: save frame to `data/raw/{name}/`
- Target: 50 images per person, vary angle/distance/lighting

### `src/preprocess.py`
- Loop over `data/raw/`
- For each image: detect face → crop ROI → resize to 112×112 → save to `data/processed/`
- Use DeepFace's `extract_faces()` for detection + alignment

### `src/build_db.py`
- Loop over `data/processed/`
- For each person: extract ArcFace embedding per image using `DeepFace.represent()`
- Average all embeddings per person → 1 vector per person
- Save as `{"name": embedding_vector}` dict to `data/embeddings/db.pkl`

### `src/recognize.py`
- Load `db.pkl`
- Open webcam, read frame, resize to 25% for speed
- Detect face → extract embedding → compute cosine distance to all DB entries
- If min distance < THRESHOLD → recognized, else → Unknown
- Draw bounding box + name on frame

### `app/database.py`
- SQLite schema:
  ```sql
  CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, registered_at TEXT);
  CREATE TABLE attendance (id INTEGER PRIMARY KEY, student_name TEXT, timestamp TEXT, confidence REAL);
  ```
- Functions: `log_attendance()`, `get_today_log()`, `export_csv()`

### `app/app.py`
- Streamlit layout:
  - Left: live webcam feed with face boxes
  - Right: today's attendance table (auto-refresh)
  - Bottom: export CSV button
- On recognition: call `log_attendance()` with name + confidence score
- Cooldown: only log same person once every 60 seconds

### `src/evaluate.py`
- Split `data/processed/` into genuine pairs (same person) and impostor pairs (different)
- Compute cosine distance for all pairs
- Sweep threshold → compute FAR and FRR at each step
- Plot ROC curve, find EER (point where FAR = FRR)
- Measure average inference time per frame (latency)

---

## Evaluation Metrics (required by rubric)

| Metric | Definition | Target |
|--------|-----------|--------|
| FAR | False Acceptance Rate — impostors accepted | < 5% |
| FRR | False Rejection Rate — genuine users rejected | < 10% |
| EER | Equal Error Rate — FAR = FRR crossover point | < 8% |
| Latency | Avg inference time per frame | < 500ms on CPU |

**Qualitative analysis to include in report:**
- Performance under low light
- Performance with partial occlusion (glasses, mask)
- Performance with pose variation (side angle)
- Failure cases and why they occur

---

## Team Split (2 people)

| Person A — ML / Core | Person B — App / Eval / Report |
|----------------------|-------------------------------|
| `collect_data.py` | Project setup, repo, README |
| `preprocess.py` | `database.py` (SQLite) |
| `build_db.py` | `app.py` (Streamlit UI) |
| `recognize.py` | `evaluate.py` |
| Model tuning, threshold search | Technical report writing |
| Edge case testing | Slide deck + demo video |

**Weekly sync:** Both review each other's code, merge via Git.

---

## Timeline

| Week | Milestone |
|------|-----------|
| Week 1–2 (now → Apr 10) | Data collection, preprocessing, repo setup |
| Week 3–4 (Apr 11–25) | `build_db.py` + `recognize.py` working end-to-end |
| Week 5–6 (Apr 26–May 10) | Streamlit UI + attendance log + evaluation metrics |
| Week 7–8 (May 11–end) | Edge case testing, report, slide, demo |

**Immediate deadline: Register group by 05/04/2026**  
Upload `Group_XX.docx` to TEAM + email to ngoctn@soict.hust.edu.vn

---

## Installation (from scratch)

```cmd
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

**requirements.txt:**
```
deepface==0.0.93
opencv-python==4.9.0.80
numpy==1.26.4
scikit-learn==1.4.2
matplotlib==3.8.4
streamlit==1.33.0
Pillow==10.3.0
tqdm==4.66.2
tf-keras
```

**Verify install:**
```cmd
python -c "from deepface import DeepFace; print('DeepFace OK')"
```

---

## Running the Project

```cmd
# Step 1: Collect face data
python src/collect_data.py

# Step 2: Preprocess images
python src/preprocess.py

# Step 3: Build embedding database
python src/build_db.py

# Step 4: Test real-time recognition
python src/recognize.py

# Step 5: Run full attendance app
streamlit run app/app.py

# Step 6: Evaluate performance
python src/evaluate.py
```

---

## Current Status

- [x] Virtual environment created
- [x] DeepFace + OpenCV installed successfully
- [x] `collect_data.py` written
- [ ] `preprocess.py`
- [ ] `build_db.py`
- [ ] `recognize.py`
- [ ] `database.py`
- [ ] `app.py`
- [ ] `evaluate.py`

---

## Notes for IDE Agent

- All code is **Python 3.12**, Windows environment
- Virtual environment is at `./venv/` — always activate before running
- DeepFace first-run downloads model weights (~500MB) automatically
- `cv2.data.haarcascades` path works on Windows with opencv-python installed
- Streamlit runs on `localhost:8501` by default
- SQLite database file will be created at `app/attendance.db` on first run
- Cosine distance via DeepFace: use `DeepFace.verify()` or manually with `numpy`
- For CPU speed: resize frames to 25% before face detection, restore coords after
