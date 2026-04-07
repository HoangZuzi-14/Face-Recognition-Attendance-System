# Face Attendance System (Hệ thống Điểm danh Khuôn mặt)

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.33-red.svg)](https://streamlit.io/)
[![DeepFace](https://img.shields.io/badge/DeepFace-ArcFace-green.svg)](https://github.com/serengil/deepface)

A robust, real-time face recognition attendance system built with Deep Learning and Streamlit. This project implements a full pipeline from data acquisition and preprocessing to real-time recognition and performance evaluation.

## 🚀 Features

- **Real-time Recognition**: High-performance face detection and recognition using **ArcFace** model via DeepFace.
- **Stability & Accuracy**: Implements **Face Tracking** (spatially-aware) and **Temporal Voting** to ensure reliable identification even with motion blur or slight occlusions.
- **Automated Attendance**: Logs attendance session-wise with status tracking (Present/Late) in an SQLite database.
- **Interactive Dashboard**: A modern Streamlit GUI for:
    - Registering new students/faces.
    - Managing class schedules and student records.
    - Visualizing attendance reports and exporting data.
- **Data Management**: Scripts for bulk importing datasets (like LFW) and building facial embedding databases efficiently.
- **Evaluation Module**: Comprehensive benchmarking for FAR, FRR, and system latency.

## 🛠️ Tech Stack

- **Core**: Python 3.9+
- **Computer Vision**: OpenCV, MediaPipe
- **Deep Learning**: DeepFace (Model: ArcFace), TensorFlow/Keras
- **Web UI**: Streamlit
- **Database**: SQLite3
- **Data Utils**: Numpy, Pandas, Scikit-learn, Openpyxl

## 📂 Project Structure

```text
Face_attendance/
├── app/                # Streamlit UI & Database models
│   ├── main.py         # Main dashboard entry point
│   ├── database.py     # SQLite interaction logic
│   └── ...
├── src/                # Core logic & Utility scripts
│   ├── recognize.py    # Main recognition engine with tracking/voting
│   ├── collect_data.py # Data acquisition utility
│   ├── build_db.py     # Facial embedding generator
│   └── evaluate.py     # Performance benchmarking script
├── data/               # Face images and embeddings storage
├── models/             # Local models or weights (if any)
├── requirements.txt    # Project dependencies
└── README.md           # You are here!
```
2. **Setup Virtual Environment** (Recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 📖 Usage Guide

### 1. Data Collection
Register a new person by capturing face samples from the webcam:
```bash
python src/add_person.py
```

### 2. Build Database
Generate embeddings for all registered faces to prepare the recognition engine:
```bash
python src/build_db.py
```

### 3. Run the Dashboard
Launch the Streamlit web application to start taking attendance:
```bash
streamlit run app/main.py
```

## 📊 Evaluation Results
The system is evaluated based on the **PROJECT_SPECIFICATION.md** requirements:
- **Model**: ArcFace (DeepFace implementation)
- **Distance Metric**: Cosine Similarity
- **Optimizations**: Reduced resolution detection (0.5x), Frame skipping (2 frames), and Spatial tracking.

## 📝 License & Disclaimer
This project is part of the **OOP_2024-1** course coursework. It is intended for educational purposes and demonstrates the application of biometric systems in real-world scenarios.

---
*Created with ❤️ by the project team.*
