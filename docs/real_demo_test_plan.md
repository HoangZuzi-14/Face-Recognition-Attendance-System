# End-to-End Real Demo Test for Face Attendance Biometrics

Generated: 2026-06-11

## Goal

Run one final real demo pass across integrity, login, recognition, liveness,
passive PAD, active challenge, fusion decision, recognition event logging, and
attendance logging.

This plan is intentionally manual-heavy because camera, spoof media, lighting,
and subject behavior must be observed in the real environment.

## Pre-Demo Setup

- Use the same camera, room, lighting, and laptop that will be used for the demo.
- Confirm `app/attendance.db` and `data/embeddings/db.pkl` are the intended runtime data.
- If using MiniFASNet PAD, set `PAD_MODEL_PATH` to the ONNX file.
- If testing liveness gates, set `LIVENESS_ENABLED=True`.
- If testing rPPG, set `RPPG_ENABLED=True` and keep the face steady long enough for the buffer.
- Start Streamlit:

```powershell
rtk .\venv\Scripts\streamlit.exe run app/main.py
```

## Required Checklist

- [ ] integrity check
- [ ] unit tests
- [ ] login/auth test
- [ ] real user attendance test
- [ ] unknown user test
- [ ] print attack test
- [ ] screen replay attack test
- [ ] active challenge test
- [ ] recognition event logging test
- [ ] attendance log verification

## 1. Integrity Check

Run:

```powershell
rtk .\venv\Scripts\python.exe src\validate_integrity.py --max-items 10
```

Pass criteria:

- `Students missing face embeddings: 0`
- `Attendance keys missing students: 0`
- Known demo-only warnings are documented before the demo starts.

## 2. Unit Tests

Run:

```powershell
rtk .\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Pass criteria:

- No test failures.

## 3. Login/Auth Test

Steps:

1. Open Streamlit.
2. Confirm the app shows login before any admin controls.
3. Try a wrong password.
4. Log in with an admin account.
5. Confirm admin-only controls are visible/enabled.

Pass criteria:

- Wrong credentials do not open the app.
- Admin session is stored without exposing password or password hash.
- Old role selector is not available.

## 4. Real User Attendance Test

Steps:

1. Select a class with a linked face identity.
2. Start native attendance camera.
3. Present the enrolled user.
4. Wait for temporal voting and liveness gate.
5. Stop camera.

Pass criteria:

- Attendance is written once for the user.
- Event decision is `ACCEPT`.
- Event includes:
  - `recognition_score`
  - `liveness_score`
  - `liveness_label`
  - `decision`
  - `timestamp`

## 5. Unknown User Test

Steps:

1. Present a person who is not enrolled in the selected class.
2. Keep the face visible long enough for recognition.

Pass criteria:

- No attendance row is written.
- Event decision is `REJECT_UNKNOWN` or equivalent unknown/review decision.

## 6. Print Attack Test

Steps:

1. Present a printed photo of an enrolled user.
2. Keep the print in front of the camera.

Pass criteria:

- Spoof attack does not write attendance.
- Event decision is `REJECT_SPOOF` or `CHALLENGE_REQUIRED`.
- If rejected as spoof, event includes `attack_type=print_attack`.

## 7. Screen Replay Attack Test

Steps:

1. Present a phone/laptop replay or displayed photo/video of an enrolled user.
2. Keep the screen in the same position a real user would occupy.

Pass criteria:

- Screen replay attack does not write attendance.
- Event decision is `REJECT_SPOOF` or `CHALLENGE_REQUIRED`.
- If rejected as spoof, event includes `attack_type=screen_replay_attack`.

## 8. Active Challenge Test

Steps:

1. Trigger a suspicious passive PAD score or force active challenge mode.
2. Run one pass where the real user completes the challenge.
3. Run one pass where a spoof cannot complete it.

Pass criteria:

- Passed challenge can continue to attendance only when recognition and liveness are valid.
- Failed challenge is rejected and does not write attendance.

## 9. Recognition Event Logging Test

Run:

```powershell
rtk .\venv\Scripts\python.exe scripts\validate_recognition_event_schema.py
```

Then export demo evidence:

```powershell
rtk .\venv\Scripts\python.exe scripts\export_demo_test_results.py --db app\attendance.db --reports-dir reports
```

By default the exporter uses the current date only, so old legacy events do
not pollute the real demo report. To inspect historical rows, run:

```powershell
rtk .\venv\Scripts\python.exe scripts\export_demo_test_results.py --db app\attendance.db --reports-dir reports --all-history
```

Pass criteria:

- Every event row has:
  - `recognition_score`
  - `liveness_score`
  - `liveness_label`
  - `attack_type` for spoof events
  - `decision`
  - `timestamp`

## 10. Attendance Log Verification

Review:

- `reports/demo_test_results.md`
- `reports/demo_test_results.csv`

Pass criteria:

- Real accepted user has attendance.
- Unknown user has no attendance.
- Print attack has no attendance.
- Screen replay attack has no attendance.
- `Spoof attendance violations` is `0`.

## Final Demo Evidence

Expected output files:

- `reports/demo_test_results.md`
- `reports/demo_test_results.csv`

Attach these files to the final project report after the real demo run.
