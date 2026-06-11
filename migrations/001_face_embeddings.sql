CREATE TABLE IF NOT EXISTS face_embeddings (
    embedding_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    identity_key TEXT NOT NULL,
    embedding BLOB NOT NULL,
    vector_dim INTEGER NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('demo', 'student')),
    model_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_face_embeddings_identity_active
ON face_embeddings(identity_key, is_active);

CREATE INDEX IF NOT EXISTS idx_face_embeddings_student_active
ON face_embeddings(student_id, is_active);
