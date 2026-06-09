# 🛡️ Face Recognition Attendance System

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58-FF4B4B.svg)](https://streamlit.io/)
[![InsightFace](https://img.shields.io/badge/InsightFace-buffalo_l-brightgreen.svg)](https://github.com/deepinsight/insightface)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A sophisticated, real-time biometric attendance solution leveraging **InsightFace buffalo_l** through **ONNX Runtime** and a modern **Streamlit** interface. Designed for accuracy, performance, and ease of use in professional environments.

---

## ✨ Key Features

- **⚡ High-Performance Recognition**: Utilizes **InsightFace buffalo_l** through ONNX Runtime, avoiding the TensorFlow/tf-keras runtime path.
- **🎯 Motion-Aware Tracking**: Implements spatial face tracking and temporal voting logic to provide stable identifiers and minimize flickering or false negatives.
- **📊 Real-time Dashboard**: A sleek, reactive web interface built with Streamlit for live monitoring, student registration, and attendance logging.
- **🗄️ Robust Data Management**: Automated pipeline for building facial embedding databases (SQLite backup) and bulk processing datasets.
- **📈 Professional Evaluation**: Built-in benchmarking tools to measure **FAR** (False Acceptance Rate), **FRR** (False Rejection Rate), and system latency.

---

## 🛠️ Technology Stack

| Category | Tools |
| :--- | :--- |
| **Core** | Python 3.12 |
| **Computer Vision** | OpenCV, Mediapipe |
| **Deep Learning** | InsightFace buffalo_l, ONNX Runtime |
| **Frontend/App** | Streamlit |
| **Storage** | SQLite3, Pandas |
| **Utilities** | Scikit-learn, Numpy, Matplotlib |

---

## 📂 Project Architecture

```text
Face_attendance/
├── app/                # Streamlit UI & Application Logic
│   ├── main.py         # Entry point for the Dashboard
│   ├── database.py     # SQLite interaction layer
│   └── ui_components.py# Custom UI modules
├── src/                # Backend Core & ML Pipelines
│   ├── recognize.py    # Main engine (Inference + Tracking)
│   ├── build_db.py     # Vector database generator
│   ├── collect_data.py # Webcam data acquisition
│   └── evaluate.py     # Performance metric suite
├── assets/             # Styling & Visual resources
├── requirements.txt    # Project dependencies
└── .gitignore          # Repository hygiene
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.12+
- A webcam for real-time recognition

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/HoangZuzi-14/Face-Recognition-Attendance-System.git
cd Face-Recognition-Attendance-System

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # On Linux/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Usage

#### **A. Register a New Subject**
Capture images via webcam to add a person to the system:
```bash
python src/add_person.py
```

#### **B. Update Embedding Database**
Process captured images into 512-dimensional embeddings:
```bash
python src/build_db.py
```

#### **C. Launch the Dashboard**
Start the real-time attendance system:
```bash
streamlit run app/main.py
```

---

## 🔍 System Evaluation
The system performance is validated using standard biometric metrics:
- **Accuracy**: Measured using Equal Error Rate (EER) on standardized datasets.
- **Latency**: Sub-300ms inference time on standard CPUs (with frame skipping optimization).
- **Metric Scripts**: Run `python src/evaluate.py` to generate ROC curves and latency reports.

---
*Developed with a focus on Deep Learning integration and high UX standards.*
