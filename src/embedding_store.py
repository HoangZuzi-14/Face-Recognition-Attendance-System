import hashlib
import os
import pickle
import shutil
import sqlite3
from pathlib import Path

import numpy as np

from app.backup import backup_file
from src.face_db import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL_ID,
    FACE_DB_METADATA_KEY,
    ensure_metadata,
    iter_identity_embeddings,
)


DEFAULT_FACE_DB_PATH = "data/embeddings/db.pkl"
DEFAULT_SQLITE_DB_PATH = "app/attendance.db"


class EmbeddingStoreError(Exception):
    pass


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_pickle_embeddings(face_db_path):
    path = Path(face_db_path)
    if not path.exists():
        return None
    try:
        with open(path, "rb") as handle:
            db = pickle.load(handle)
    except Exception as exc:
        raise EmbeddingStoreError(f"Cannot load embedding pickle {path}: {exc}") from exc
    if not isinstance(db, dict):
        raise EmbeddingStoreError(f"Embedding pickle is not a dict: {path}")
    return db


def _sqlite_table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _load_sqlite_embeddings(sqlite_db_path):
    path = Path(sqlite_db_path)
    if not path.exists():
        return None
    conn = sqlite3.connect(path)
    try:
        if not _sqlite_table_exists(conn, "face_embeddings"):
            return None
        rows = conn.execute(
            """
            SELECT identity_key, embedding, vector_dim, model_name
            FROM face_embeddings
            WHERE is_active = 1
            ORDER BY identity_key, embedding_id
            """
        ).fetchall()
        if not rows:
            return None

        db = {}
        identity_models = {}
        for identity_key, blob, vector_dim, model_name in rows:
            vector = np.frombuffer(blob, dtype=np.float32).copy()
            if vector_dim and int(vector_dim) != vector.size:
                raise EmbeddingStoreError(
                    f"SQLite embedding dimension mismatch for {identity_key}: "
                    f"declared={vector_dim}, actual={vector.size}"
                )
            db[identity_key] = vector
            identity_models[identity_key] = model_name or EMBEDDING_MODEL_ID
        metadata = ensure_metadata(db)
        metadata["embedding_model"] = EMBEDDING_MODEL_ID
        metadata["identity_models"].update(identity_models)
        metadata["storage"] = "sqlite"
        return db
    finally:
        conn.close()


def load_embeddings(
    face_db_path=DEFAULT_FACE_DB_PATH,
    sqlite_db_path=DEFAULT_SQLITE_DB_PATH,
    prefer_sqlite=True,
):
    if prefer_sqlite and sqlite_db_path:
        sqlite_db = _load_sqlite_embeddings(sqlite_db_path)
        if sqlite_db is not None:
            return sqlite_db
    return _load_pickle_embeddings(face_db_path)


def backup_embeddings(face_db_path=DEFAULT_FACE_DB_PATH, backup_root="backups"):
    path = Path(face_db_path)
    if not path.exists():
        return {"backup_path": None, "source_checksum": None}
    backup_path = backup_file(path, backup_root=backup_root, label="face_db")
    return {
        "backup_path": str(backup_path) if backup_path else None,
        "source_checksum": _sha256(path),
    }


def validate_embeddings(db, required_keys=None):
    errors = []
    if not isinstance(db, dict):
        return False, ["embedding store is not a dict"]

    required_keys = set(required_keys or [])
    identity_keys = {name for name, _ in iter_identity_embeddings(db)}
    missing = sorted(required_keys - identity_keys)
    for key in missing:
        errors.append(f"missing required identity: {key}")

    for name, embedding in iter_identity_embeddings(db):
        try:
            vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        except Exception as exc:
            errors.append(f"invalid embedding for {name}: {exc}")
            continue
        if vector.size != EMBEDDING_DIM:
            errors.append(f"invalid embedding dimension for {name}: {vector.size}")
        if not np.all(np.isfinite(vector)):
            errors.append(f"non-finite embedding values for {name}")

    return not errors, errors


def _restore_backup(backup_path, face_db_path):
    if not backup_path:
        return
    source = Path(backup_path)
    if source.exists():
        shutil.copy2(source, face_db_path)


def save_embeddings_safely(
    db,
    face_db_path=DEFAULT_FACE_DB_PATH,
    backup_root="backups",
    required_keys=None,
    validator=None,
):
    face_db_path = Path(face_db_path)
    face_db_path.parent.mkdir(parents=True, exist_ok=True)

    backup = backup_embeddings(face_db_path, backup_root=backup_root)
    backup_path = backup.get("backup_path")
    temp_path = face_db_path.with_suffix(face_db_path.suffix + ".tmp")

    try:
        file_ok, file_errors = validate_embeddings(db, required_keys=required_keys)
        if not file_ok:
            return {
                "ok": False,
                "backup_path": backup_path,
                "errors": file_errors,
                "rolled_back": False,
            }

        with open(temp_path, "wb") as handle:
            pickle.dump(db, handle)
        os.replace(temp_path, face_db_path)

        reloaded = _load_pickle_embeddings(face_db_path)
        post_ok, post_errors = validate_embeddings(
            reloaded,
            required_keys=required_keys,
        )
        if validator is not None:
            custom_ok, custom_errors = validator(reloaded)
            post_ok = post_ok and custom_ok
            post_errors.extend(custom_errors)

        if not post_ok:
            _restore_backup(backup_path, face_db_path)
            return {
                "ok": False,
                "backup_path": backup_path,
                "errors": post_errors,
                "rolled_back": bool(backup_path),
            }

        return {
            "ok": True,
            "backup_path": backup_path,
            "source_checksum": backup.get("source_checksum"),
            "saved_checksum": _sha256(face_db_path),
            "errors": [],
            "rolled_back": False,
        }
    finally:
        if temp_path.exists():
            temp_path.unlink()
