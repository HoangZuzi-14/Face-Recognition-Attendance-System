# Face Attendance

**Realtime face-recognition attendance with class-scoped identity matching and passive anti-spoofing.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=0B1220)
![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-Inference-005CED?style=for-the-badge&logo=onnx&logoColor=white)
![Liveness](https://img.shields.io/badge/Liveness-Passive_PAD-ce1628?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

A face-recognition attendance system with a Python API backend, a React frontend, and a native OpenCV camera flow. The project focuses on stable class-scoped recognition, one attendance record per student per day, and passive PAD/liveness checks for anti-spoofing.

## System Snapshot

| Layer | What it does | Main files |
| --- | --- | --- |
| Recognition engine | Detects, embeds, tracks, votes, and logs attendance decisions | `src/recognize.py` |
| Liveness gate | Runs passive PAD and fuses liveness decisions | `src/liveness.py`, `src/pad/` |
| API adapter | Exposes classes, roster, attendance, camera, and event endpoints | `app/api.py` |
| React console | Operator UI for live attendance and review workflows | `frontend/src/` |
| Data layer | Stores students, classes, attendance, audit, and recognition events | `repositories/`, `app/database.py` |

## Key Features

- Face recognition with InsightFace `buffalo_l` and ONNX Runtime.
- Class-scoped recognition candidate filtering to reduce false matches from students outside the selected class.
- Realtime face tracking with spatial trackers, temporal voting, and a cache of today's attendance records.
- Anti-spoofing with MiniFASNet ONNX passive PAD, median voting, and early-exit decisions for clearly live or clearly spoof samples.
- SQLite recognition event logs with confidence, distance, gap, liveness label, live/print/replay/spoof scores, and attendance logging status.
- React/Vite UI for dashboard, classes, enrollment, live attendance, events, reports, and settings.
- Legacy Streamlit UI remains available for existing workflows.
- UI typography uses `Be Vietnam Pro` for reliable Vietnamese text rendering.


## Technology Stack

| Area | Technology |
| --- | --- |
| Backend | Python, FastAPI, SQLite |
| Camera | Native OpenCV window |
| Recognition | InsightFace `buffalo_l`, ONNX Runtime |
| Anti-spoofing | MiniFASNet ONNX passive PAD |
| Frontend | React, TypeScript, Vite |
| UI font | Be Vietnam Pro, JetBrains Mono |
| Testing | pytest, ESLint, Vite build |

## Project Structure

```text
Face_attendance/
|-- app/                  # API, Streamlit UI, camera runners, config
|   |-- api.py            # FastAPI adapter
|   |-- config.py         # Thresholds, camera, and liveness config
|   |-- native_camera.py  # Native camera process management
|   `-- pages/            # Streamlit pages
|-- frontend/             # React + TypeScript + Vite UI
|-- services/             # Service layer
|-- repositories/         # SQLite repositories
|-- src/                  # Recognition, liveness, PAD, rPPG, evaluation
|   |-- recognize.py      # Realtime recognition, tracking, and voting
|   |-- liveness.py       # Liveness/PAD gate
|   `-- pad/              # MiniFASNet ONNX wrapper
|-- scripts/              # Migration, evaluation, and export tools
|-- tests/                # Automated tests
|-- models/               # Local model files
`-- data/                 # Runtime embeddings and data
```

## Installation

### Backend

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Place the PAD model at:

```text
models/pad/minifasnet.onnx
```

Or override the model path:

```bash
set PAD_MODEL_PATH=C:\path\to\minifasnet.onnx
```

### Frontend

```bash
cd frontend
npm install
```

## Running The App

### API Backend

```bash
python run_api.py
```

### React Frontend

```bash
cd frontend
npm run dev
```

### Legacy Streamlit UI

```bash
streamlit run app/main.py
```

## Demo Accounts

The app seeds two default demo users on startup:

| Role | Username | Password | Purpose |
| --- | --- | --- | --- |
| Admin | `admin` | `admin123` | Full system administration |
| Teacher | `teacher` | `teacher123` | Attendance and class operation |

These credentials can be overridden with environment variables:

```bash
set ATTENDANCE_ADMIN_USERNAME=admin
set ATTENDANCE_ADMIN_PASSWORD=admin123
set ATTENDANCE_TEACHER_USERNAME=teacher
set ATTENDANCE_TEACHER_PASSWORD=teacher123
```

## Basic Workflow

1. Create or select a class.
2. Import the student roster.
3. Enroll face images for each student.
4. Build or reload embeddings.
5. Open Live Attendance and start the native camera.
6. Review recognition logs in Events and export attendance reports in Reports.

## Important Configuration

| Variable | Default | Purpose |
| --- | ---: | --- |
| `RECOGNITION_THRESHOLD` | `0.35` | Strong recognition threshold |
| `REVIEW_THRESHOLD` | `0.45` | Identity review zone |
| `CONFIDENCE_GAP` | `0.05` | Minimum top-1 vs. top-2 distance gap |
| `VOTE_WINDOW` | `2` | Number of frames required to confirm identity |
| `LIVENESS_ENABLED` | `true` | Enables or disables the liveness gate |
| `PASSIVE_PAD_ENABLED` | `true` | Enables or disables MiniFASNet PAD |
| `PAD_VOTING_WINDOW` | `3` | Number of PAD samples retained for median voting |
| `RPPG_ENABLED` | `false` | rPPG is disabled by default to prioritize speed |

## Testing

Run the Python test suite:

```bash
pytest -q
```

Build the frontend:

```bash
cd frontend
npm run build
```

Frontend linting currently reports existing issues in code that has not been refactored yet:

```bash
cd frontend
npm run lint
```

## Operational Notes

- `NEED_REVIEW` means the identity match is not strong enough yet. It is not a spoof verdict.
- PAD/liveness only allows attendance logging after recognition is `ACCEPT` and the liveness gate allows it.
- Spoof and unknown cases do not create attendance rows. They only create recognition events for audit and tuning.
- In different lighting or camera environments, use Events to inspect `live_score`, `spoof_score`, `distance`, and `gap`, then tune thresholds if needed.
