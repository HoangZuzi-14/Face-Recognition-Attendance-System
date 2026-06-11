-- Auth and user-aware audit schema.
-- Runtime migration is implemented idempotently in app.database.init_db().

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

-- Add these columns to audit_logs when they are missing:
-- actor_user_id INTEGER
-- actor_username TEXT
-- target TEXT
-- timestamp TEXT
-- status TEXT DEFAULT 'SUCCESS'
