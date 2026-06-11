# Auth and audit design

Generated: 2026-06-09

## Login

The Streamlit app no longer exposes a role selector. Users must log in before
the main dashboard renders.

Initial admin seeding is handled by `app.database.init_db()`:

- Default username: `admin`
- Default password: `admin123`
- Override username with `ATTENDANCE_ADMIN_USERNAME`
- Override password with `ATTENDANCE_ADMIN_PASSWORD`

Passwords are hashed with bcrypt before they are stored in SQLite.

## Session State

`st.session_state["current_user"]` stores only:

- `id`
- `username`
- `role`

It does not store plaintext passwords or password hashes.

## Authorization

Existing permission checks continue to use `app.auth.can_perform(role,
permission)`, but `st.session_state.user_role` is now derived from the
authenticated user session.

Admin-only actions remain gated by the permission matrix, including:

- `attendance.clear`
- `class.delete`
- `roster.import`

## Audit Log

`audit_logs` keeps legacy columns and adds user-aware fields:

- `actor_user_id`
- `actor_username`
- `target`
- `timestamp`
- `status`

The UI sets the current user in `app.audit_context`. Database writes that call
`write_audit_log()` automatically attach that user unless an explicit actor is
provided.

When no authenticated user is available, audit writes still use `system`.

## Tests

Coverage for this change lives in:

- `tests/test_auth.py`
- `tests/test_schema_audit.py`
- `tests/test_streamlit_auth_ui.py`
