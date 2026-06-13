# Face Attendance

A face-recognition attendance system with a Python API backend, a React frontend, and a native OpenCV camera flow. The project focuses on stable class-scoped recognition, one attendance record per student per day, and passive PAD/liveness checks for anti-spoofing.

## Key Features

- Face recognition with InsightFace `buffalo_l` and ONNX Runtime.
- Class-scoped recognition candidate filtering to reduce false matches from students outside the selected class.
- Realtime face tracking with spatial trackers, temporal voting, and a cache of today's attendance records.
- Anti-spoofing with MiniFASNet ONNX passive PAD, median voting, and early-exit decisions for clearly live or clearly spoof samples.
- SQLite recognition event logs with confidence, distance, gap, liveness label, live/print/replay/spoof scores, and attendance logging status.
- React/Vite UI for dashboard, classes, enrollment, live attendance, events, reports, and settings.
- Legacy Streamlit UI remains available for existing workflows.
- UI typography uses `Be Vietnam Pro` for reliable Vietnamese text rendering.

## Recent Liveness Optimization

The PAD flow was tuned to reduce the waiting time before deciding `real` or `spoof`:

- Default `PAD_VOTING_WINDOW` was reduced from `5` to `3`.
- If `spoof_score >= 0.80`, the system immediately decides `SPOOF`.
- If `live_score >= 0.90` and `spoof_score <= 0.15`, the system immediately decides `LIVE`.
- Unclear cases still use median voting for stability.

These values can be overridden with environment variables:

```bash
PAD_VOTING_WINDOW=3
PAD_CLEAR_SPOOF_THRESHOLD=0.80
PAD_CLEAR_LIVE_THRESHOLD=0.90
PAD_CLEAR_LIVE_MAX_SPOOF=0.15
```

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
