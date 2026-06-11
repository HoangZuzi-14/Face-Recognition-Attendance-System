# Liveness gate design

Generated: 2026-06-09

## Current Scope

`src/liveness.py` defines the liveness API and a rule-based placeholder.
It is ready for later passive PAD, active challenge, and rPPG implementations.

Current behavior:

- Missing or invalid frame: `UNKNOWN`
- Missing or invalid face bbox: `UNKNOWN`
- Valid frame and bbox with no PAD model: `LIVE` with reason `rule_placeholder_live`
- Valid frame and bbox with PAD model: PAD `live_score` controls `LIVE` vs `SPOOF`

This is not a production anti-spoofing model. It exists to make the pipeline,
schema, config, and HUD ready for a stronger liveness implementation.

## Config

Config is defined in `app/config.py` and can be overridden with environment
variables:

- `LIVENESS_ENABLED` default `False`
- `LIVENESS_THRESHOLD` default `0.70`
- `CHALLENGE_TIMEOUT` default `5`
- `RPPG_WINDOW` default `90`
- `PASSIVE_PAD_ENABLED` default `True`
- `ACTIVE_CHALLENGE_ENABLED` default `False`
- `RPPG_ENABLED` default `False`
- `PAD_MODEL_PATH` default `models/pad/minifasnet.onnx`
- `PAD_THRESHOLD` default `0.70`

`LIVENESS_ENABLED` defaults to `False` so the demo attendance flow remains
compatible until a real anti-spoofing method is implemented.

## Recognition Decisions

When liveness is enabled and face recognition returns an accepted match:

- `LIVE`: continue temporal voting and attendance logging.
- `SPOOF`: reject attendance and record `REJECT_SPOOF`.
- `UNKNOWN`: reject immediate attendance and record `REJECT_UNKNOWN`.
- `CHALLENGE`: reject immediate attendance and record `CHALLENGE_REQUIRED`.

When liveness is disabled, recognition follows the previous attendance flow
and records liveness as `DISABLED` for accepted events.

## Passive PAD

`src/pad/minifasnet.py` wraps MiniFASNet ONNX inference with onnxruntime.

The wrapper:

- loads ONNX with CPU execution provider by default
- preprocesses a face crop into `NCHW` float tensor
- returns `live_score` and `spoof_score`
- raises `PADModelUnavailable` with a clear message when the model file is
  missing or inference cannot run

`assess_liveness()` catches `PADModelUnavailable`, records `pad_error` in
details, and keeps the demo pipeline alive.

## Texture Baseline

`assess_texture_liveness()` computes lightweight image features from the face
crop:

- sharpness / blur
- FFT high-frequency ratio
- LBP texture score, with a gradient fallback if LBP is unavailable

Texture is recorded in `LivenessResult.details` and is not used as the only
decision source.

## rPPG Fusion Hook

`src/rppg.py` provides frame buffers and a POS-style pulse estimator. When
`RPPG_ENABLED=True`, the recognition tracker collects RGB means and passes the
latest pulse result into `assess_liveness()`.

## Event Schema

`recognition_events` keeps legacy columns and adds:

- `liveness_score`
- `liveness_label`
- `attack_type`
- `liveness_reasons`
- `recognition_score`

Run the schema check with:

```powershell
rtk .\venv\Scripts\python.exe scripts\validate_recognition_event_schema.py
```

## Native HUD

The native camera HUD shows:

- identity
- recognition score
- liveness label
- liveness score
- short liveness reason

Spoof decisions are drawn with a red warning color and do not log attendance.
