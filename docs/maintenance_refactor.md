# Maintenance refactor checkpoint

Generated: 2026-06-11

## Goal

Epic 9 starts reducing `app/database.py` debt without changing behavior.

`app/database.py` still owns:

- SQLite connection
- schema creation
- idempotent migrations
- legacy function API used by existing scripts/tests

Business logic already exists in top-level packages:

- `repositories/`
- `services/`

This checkpoint adds the target namespaces:

- `app.repositories`
- `app.services`

They currently re-export the existing repository/service classes. New code can
import from the `app.*` namespace while older imports continue to work.

## Native Camera Diagnostics

`app/native_camera.py` now:

- captures native camera stdout/stderr
- writes logs to `logs/native_camera.log`
- stores preflight diagnostics in Streamlit session state
- maps known native exit codes to clear UI messages

Known exit codes:

- `2`: face DB missing
- `3`: no usable face embeddings for selected class
- `4`: cannot open selected camera index

Preflight reports:

- active identity count
- `db.pkl` load status
- SQLite DB file status
- liveness enabled/disabled

## Next Refactor Step

Move implementation bodies from top-level `repositories/` and `services/` into
`app/repositories/` and `app/services/`, then leave top-level packages as thin
compatibility shims. Keep tests green after each file move.
