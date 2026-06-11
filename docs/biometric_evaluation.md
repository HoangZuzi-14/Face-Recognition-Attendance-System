# Biometric evaluation and fusion

Generated: 2026-06-11

## Fusion Decision

`src/fusion.py` defines `fuse_decision()` for score-level decision logic.

Inputs:

- `recognition_score`
- `recognition_matched`
- `liveness_score`
- `pad_score`
- `challenge_result`
- `rppg_confidence`
- `quality_score`

Outputs:

- `ACCEPT`
- `REJECT_SPOOF`
- `REJECT_UNKNOWN`
- `CHALLENGE_REQUIRED`

The policy is conservative:

- no recognition match -> `REJECT_UNKNOWN`
- failed active challenge -> `REJECT_SPOOF`
- passive PAD suspicious -> `CHALLENGE_REQUIRED`
- liveness failure -> `REJECT_SPOOF`
- low quality -> `REJECT_UNKNOWN`
- clear recognition + liveness -> `ACCEPT`

## PAD Dataset

Dataset skeleton:

```text
datasets/pad/
  genuine/
  print_attack/
  screen_attack/
  cutout_attack/
  metadata.csv
```

`metadata.csv` columns:

- `sample_id`
- `label`
- `attack_type`
- `subject_id`
- `device`
- `lighting`
- `note`

For genuine samples, place images in `datasets/pad/genuine/`.
For spoof samples, place images in the matching attack folder.

## PAD Metrics

Run:

```powershell
rtk .\venv\Scripts\python.exe scripts\evaluate_pad.py --dataset datasets/pad --reports-dir reports --threshold 0.70
```

Outputs:

- `reports/pad_metrics.json`
- `reports/pad_metrics.md`
- `reports/confusion_matrix.png`

Metrics:

- APCER: spoof samples incorrectly accepted as genuine.
- BPCER: genuine samples incorrectly rejected as spoof.
- ACER: average of APCER and BPCER.

## Recognition Threshold Metrics

Run with a score CSV:

```powershell
rtk .\venv\Scripts\python.exe scripts\evaluate_recognition_threshold.py --scores reports/recognition_scores.csv --reports-dir reports
```

CSV columns:

- `score`
- `label`: `genuine` or `impostor`

Alternative columns:

- `left_embedding`
- `right_embedding`
- `label`

Outputs:

- `reports/recognition_threshold_report.md`
- `reports/recognition_threshold_metrics.json`
- `reports/roc_curve.png`
- `reports/det_curve.png`

Metrics:

- FAR: impostor pairs accepted above threshold.
- FRR: genuine pairs rejected below threshold.
- EER: threshold where FAR and FRR are closest.
