import argparse
import pickle
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.validate_embedding_metadata import build_embedding_metadata  # noqa: E402
from src.face_db import EMBEDDING_MODEL_ID, FACE_DB_METADATA_KEY, iter_identity_embeddings  # noqa: E402


CREATE_FACE_EMBEDDINGS_SQL = """
CREATE TABLE IF NOT EXISTS face_embeddings (
    embedding_id INTEGER PRIMARY KEY,
    student_id INTEGER,
    identity_key TEXT NOT NULL,
    embedding BLOB NOT NULL,
    vector_dim INTEGER NOT NULL,
    source TEXT NOT NULL,
    model_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
)
"""

CREATE_FACE_EMBEDDINGS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_face_embeddings_identity_active
ON face_embeddings(identity_key, is_active)
"""


def _load_face_db(face_db_path):
    with open(face_db_path, "rb") as handle:
        db = pickle.load(handle)
    if not isinstance(db, dict):
        raise ValueError(f"Face DB is not a dict: {face_db_path}")
    return db


def _student_id_map(conn):
    try:
        rows = conn.execute(
            """
            SELECT id, db_key
            FROM students
            WHERE db_key IS NOT NULL AND TRIM(db_key) != ''
            """
        ).fetchall()
    except sqlite3.Error:
        return {}
    return {db_key: student_id for student_id, db_key in rows}


def migrate_pkl_to_sqlite(
    face_db_path="data/embeddings/db.pkl",
    sql_db_path="app/attendance.db",
    metadata_path=None,
):
    face_db_path = Path(face_db_path)
    sql_db_path = Path(sql_db_path)
    sql_db_path.parent.mkdir(parents=True, exist_ok=True)

    db = _load_face_db(face_db_path)
    metadata = (
        build_embedding_metadata(face_db_path=face_db_path, sql_db_path=sql_db_path)
        if metadata_path is None
        else None
    )
    if metadata_path is not None:
        import json

        with open(metadata_path, "r", encoding="utf-8") as handle:
            metadata = json.load(handle)

    db_metadata = db.get(FACE_DB_METADATA_KEY) if isinstance(db.get(FACE_DB_METADATA_KEY), dict) else {}
    identity_models = db_metadata.get("identity_models", {}) if isinstance(db_metadata.get("identity_models"), dict) else {}

    conn = sqlite3.connect(sql_db_path)
    try:
        conn.execute(CREATE_FACE_EMBEDDINGS_SQL)
        conn.execute(CREATE_FACE_EMBEDDINGS_INDEX_SQL)
        student_ids = _student_id_map(conn)
        now = datetime.now().isoformat()
        migrated = 0

        for identity_key, embedding in iter_identity_embeddings(db):
            vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
            conn.execute(
                "UPDATE face_embeddings SET is_active=0 WHERE identity_key=?",
                (identity_key,),
            )
            identity_meta = metadata.get("identities", {}).get(identity_key, {})
            conn.execute(
                """
                INSERT INTO face_embeddings (
                    student_id, identity_key, embedding, vector_dim,
                    source, model_name, created_at, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    student_ids.get(identity_key),
                    identity_key,
                    vector.astype(np.float32).tobytes(),
                    int(vector.size),
                    identity_meta.get("source", "demo"),
                    identity_models.get(identity_key, db_metadata.get("embedding_model", EMBEDDING_MODEL_ID)),
                    now,
                ),
            )
            migrated += 1

        conn.commit()
        return {"migrated_count": migrated, "sql_db_path": str(sql_db_path)}
    finally:
        conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Migrate db.pkl embeddings to SQLite.")
    parser.add_argument("--face-db", default="data/embeddings/db.pkl")
    parser.add_argument("--sql-db", default="app/attendance.db")
    parser.add_argument("--metadata", default=None)
    args = parser.parse_args(argv)
    result = migrate_pkl_to_sqlite(
        face_db_path=args.face_db,
        sql_db_path=args.sql_db,
        metadata_path=args.metadata,
    )
    print(f"Migrated embeddings: {result['migrated_count']}")
    print(f"SQLite DB: {result['sql_db_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
