# Data fix log

Generated: 2026-06-09

## Backup

Before data mutation, a full runtime backup was created:

```text
backups/20260609_193619
Files copied: 13292
Manifest: backups/20260609_193619/backup_manifest.json
```

The backup includes:

- `app/attendance.db`
- `data/embeddings/db.pkl`
- `data/raw`
- `data/processed`
- identity-related config files

## Task 0.3 - Missing embeddings

Target keys:

- `Duong_Ngo_Hoang_Vu`
- `Nguyen_Khanh_Toan`

Observed state before fix:

- Both keys existed in SQLite.
- Both keys were missing from `data/embeddings/db.pkl`.
- Both keys had raw image folders.
- Both keys had processed image folders.

First rebuild attempt:

```text
Duong_Ngo_Hoang_Vu False
Nguyen_Khanh_Toan False
```

Root cause:

- InsightFace detected faces in raw frames:
  - `Duong_Ngo_Hoang_Vu`: 10/10 raw images
  - `Nguyen_Khanh_Toan`: 14/14 raw images
- InsightFace detected no faces in processed 112x112 crops:
  - `Duong_Ngo_Hoang_Vu`: 0/10 processed images
  - `Nguyen_Khanh_Toan`: 0/14 processed images

Code fix:

- `app/add_face.py` now falls back to `data/raw/<person_key>` when processed crops cannot produce embeddings.
- Added regression test:
  - `tests/test_face_registration.py::test_extract_embedding_falls_back_to_raw_frames_when_processed_detection_fails`

Second rebuild attempt:

```text
Duong_Ngo_Hoang_Vu True
Nguyen_Khanh_Toan True
present {'Duong_Ngo_Hoang_Vu': True, 'Nguyen_Khanh_Toan': True}
models {'Duong_Ngo_Hoang_Vu': 'insightface/buffalo_l', 'Nguyen_Khanh_Toan': 'insightface/buffalo_l'}
```

## Task 0.4 - Orphan attendance key

Target key:

- `Tran_Binh_Minh`

Observed state before fix:

- No row in `students`.
- No row in `face_identities`.
- No key in `db.pkl`.
- One attendance row existed:
  - `attendance.id = 5`
  - `class_id = 1`
  - `date = 2026-05-18`
  - `status = PRESENT`

Fix applied:

```bash
rtk .\venv\Scripts\python.exe scripts\archive_orphan_attendance.py --key Tran_Binh_Minh
```

Result:

```json
{
  "key": "Tran_Binh_Minh",
  "archived_count": 1,
  "reason": "archived"
}
```

The row was moved to `attendance_orphans` and removed from active `attendance`. This is not a hard delete; original attendance id and key are preserved.

Current archive row:

```text
original_attendance_id = 5
student_db_key = Tran_Binh_Minh
archive_reason = student_db_key_missing_from_students_face_identities_and_face_db
```

## Scripts added

| Script | Purpose |
| --- | --- |
| `scripts/backup_runtime_data.py` | Full runtime backup with `backup_manifest.json` and SHA256 checksums. |
| `scripts/archive_orphan_attendance.py` | Archive orphan attendance rows after checking SQLite and face DB identities. |

## Verification

Focused tests:

```bash
rtk .\venv\Scripts\python.exe -m unittest tests.test_runtime_data_scripts -v
rtk .\venv\Scripts\python.exe -m unittest tests.test_face_registration -v
```

Integrity after fixes:

```text
Students missing face embeddings: 0
Attendance keys missing students: 0
```

Remaining integrity issues are documented in `docs/integrity_report.md`.
