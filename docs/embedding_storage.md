# Embedding storage design

Generated: 2026-06-09

## Current state

The active face embedding store remains:

```text
data/embeddings/db.pkl
```

The pickle format is still compatible with the existing recognition pipeline:

```python
{
    "Identity_Key": np.ndarray(shape=(512,), dtype=float32),
    "__metadata__": {
        "embedding_model": "insightface/buffalo_l",
        "identity_models": {
            "Identity_Key": "insightface/buffalo_l"
        }
    }
}
```

## Task 1.1 - Metadata source

Because a full SQLite migration must remain backward compatible, identity source metadata is stored in a sidecar file:

```text
data/embedding_metadata.json
```

Schema:

```json
{
  "version": 1,
  "generated_at": "ISO-8601 timestamp",
  "embedding_model": "insightface/buffalo_l",
  "identities": {
    "Identity_Key": {
      "identity_key": "Identity_Key",
      "display_name": "Display Name",
      "source": "demo | student",
      "created_at": "ISO-8601 timestamp",
      "updated_at": "ISO-8601 timestamp",
      "image_count": 10
    }
  }
}
```

Source rules:

- `student`: identity key exists in SQLite `students.db_key`.
- `demo`: identity key exists in `db.pkl` but not in SQLite students.

Generate or validate metadata:

```bash
rtk .\venv\Scripts\python.exe scripts\validate_embedding_metadata.py --write
rtk .\venv\Scripts\python.exe scripts\validate_embedding_metadata.py
```

## Task 1.2 - Safe pickle writes

New module:

```text
src/embedding_store.py
```

Functions:

- `load_embeddings()`
- `save_embeddings_safely()`
- `backup_embeddings()`
- `validate_embeddings()`

Write policy:

1. Validate in-memory embedding dictionary.
2. Backup existing `db.pkl` if present.
3. Write to a temporary pickle file.
4. Atomically replace the target file.
5. Reload the pickle file.
6. Validate required identities and embedding dimensions.
7. Roll back from backup if post-write validation fails.

Integrated writers:

- `app/add_face.py`
- `src/add_person.py`
- `src/build_db.py`
- `src/clean_orphans.py`
- `src/rename_person.py`

Note: full repository integrity can still report expected demo/orphan conditions, so `save_embeddings_safely()` performs file-level validation and supports an injected validator for stricter future checks.

## Task 1.3 - SQLite migration design

Migration SQL:

```text
migrations/001_face_embeddings.sql
```

Target table:

```sql
face_embeddings (
    embedding_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    identity_key TEXT NOT NULL,
    embedding BLOB NOT NULL,
    vector_dim INTEGER NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('demo', 'student')),
    model_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
)
```

Migration script:

```bash
rtk .\venv\Scripts\python.exe scripts\migrate_pkl_to_sqlite.py
```

The script:

- Reads `data/embeddings/db.pkl`.
- Creates `face_embeddings` if needed.
- Stores vectors as float32 BLOBs.
- Marks previous rows for the same identity inactive.
- Keeps source metadata as `demo` or `student`.

## Parallel read mode

`src.embedding_store.load_embeddings()` supports:

```python
load_embeddings(
    face_db_path="data/embeddings/db.pkl",
    sqlite_db_path="app/attendance.db",
    prefer_sqlite=True,
)
```

Behavior:

1. If SQLite has active `face_embeddings`, load from SQLite.
2. Otherwise fallback to `db.pkl`.

`src.recognize.load_db()` now uses this path, so recognition remains compatible before and after migration.

## Rollback

Before running migration against runtime data:

```bash
rtk .\venv\Scripts\python.exe scripts\backup_runtime_data.py
```

Rollback options:

1. If only SQLite migration was run, drop or ignore `face_embeddings`; recognition will fallback to `db.pkl` if no active SQLite rows are present.
2. Restore `app/attendance.db` from the latest runtime backup if the migration must be fully undone.
3. Restore `data/embeddings/db.pkl` from backup if pickle writes were involved.

Do not delete `db.pkl` until SQLite-backed recognition has been verified with real camera data.
