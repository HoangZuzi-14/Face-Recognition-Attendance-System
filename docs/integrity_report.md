# Integrity report

Generated: 2026-06-09

Scope:

- SQLite database: `app/attendance.db`
- Face database: `data/embeddings/db.pkl`
- Raw image folders: `data/raw/<person_key>`
- Processed image folders: `data/processed/<person_key>`
- Attendance log keys in SQLite

## Current result

Command:

```bash
rtk .\venv\Scripts\python.exe src\validate_integrity.py --max-items 10
```

Result after Task 0.3 and Task 0.4 fixes:

```text
Integrity OK: False
Students missing face embeddings: 0
Face embeddings missing students: 5711
  - AJ_Cook
  - AJ_Lamas
  - Aaron_Eckhart
  - Aaron_Guiel
  - Aaron_Patterson
  - Aaron_Peirsol
  - Aaron_Pena
  - Aaron_Sorkin
  - Aaron_Tippin
  - Abba_Eban
  ... 5701 more
Missing raw directories: 26
  - Angela_Merkel
  - Angelina_Jolie
  - Ariel_Sharon
  - Bill_Clinton
  - Bill_Gates
  - Brad_Pitt
  - Colin_Powell
  - David_Beckham
  - Donald_Rumsfeld
  - Donald_Trump
  ... 16 more
Missing processed directories: 0
Attendance keys missing students: 0
Errors: 0
```

## Runtime snapshot

SQLite counts:

| Table | Rows |
| --- | ---: |
| `classes` | 2 |
| `students` | 42 |
| `class_students` | 43 |
| `attendance` | 5 |
| `attendance_orphans` | 1 |
| `face_identities` | 28 |
| `audit_logs` | 3 |

Face DB:

| Metric | Value |
| --- | ---: |
| Identities in `db.pkl` | 5739 |
| `Duong_Ngo_Hoang_Vu` embedding | present |
| `Nguyen_Khanh_Toan` embedding | present |
| Target embedding model metadata | `insightface/buffalo_l` |

Backup created before data fixes:

```text
backups/20260609_193619
Files copied: 13292
Manifest: backups/20260609_193619/backup_manifest.json
```

## Fixed in this task

### SQLite keys missing embeddings

Initial failing keys:

- `Duong_Ngo_Hoang_Vu`
- `Nguyen_Khanh_Toan`

Both identities had raw and processed images. The existing processed 112x112 crops produced 0 InsightFace detections, while raw 480x640 frames produced detections for every image checked. `app/add_face.py` now falls back to raw frames if processed crops cannot produce embeddings.

Both embeddings were rebuilt successfully and written to `db.pkl` with `insightface/buffalo_l` metadata.

### Attendance orphan

Initial orphan attendance key:

- `Tran_Binh_Minh`

No matching student, face identity, or face DB embedding was found. The row was archived instead of hard-deleted:

```text
attendance_orphans.original_attendance_id = 5
attendance_orphans.student_db_key = Tran_Binh_Minh
archive_reason = student_db_key_missing_from_students_face_identities_and_face_db
```

## Remaining integrity issues

### 1. Face embeddings missing students

Count: 5711

Likely cause: `db.pkl` contains LFW/demo identities that are not intended to be students in SQLite.

Recommended fix:

1. Decide whether these are expected demo/reference embeddings or stale production data.
2. If expected, add metadata or a separate store/namespace so integrity does not treat them as student identities.
3. If stale, run a reviewed cleanup using `src/clean_orphans.py --clean` only after confirming the latest backup.

Do not delete these embeddings blindly.

### 2. Missing raw directories

Count: 26

These students have linked `db_key` values but no `data/raw/<db_key>` folder. Processed folders exist.

Recommended fix:

1. For real enrolled students, restore raw folders from backup or recapture enrollment images.
2. For seeded/demo students, document that processed-only identities are allowed or move them to seed/demo metadata.
3. Consider changing integrity policy to distinguish `required_raw=True` from imported/demo identities.

## Conclusion

Task-critical blocking mismatches were fixed:

- No student `db_key` is missing from `db.pkl`.
- No current attendance row points to a missing student key.

Integrity is still not fully clean because the project contains many face embeddings without SQLite students and several linked students without raw image folders.
