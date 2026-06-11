import argparse
import json
import pickle
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.face_db import FACE_DB_METADATA_KEY, iter_identity_embeddings  # noqa: E402


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _load_face_db(face_db_path):
    with open(face_db_path, "rb") as handle:
        db = pickle.load(handle)
    if not isinstance(db, dict):
        raise ValueError(f"Face DB is not a dict: {face_db_path}")
    return db


def _student_map(sql_db_path):
    path = Path(sql_db_path)
    if not path.exists():
        return {}
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute(
            """
            SELECT full_name, db_key
            FROM students
            WHERE db_key IS NOT NULL AND TRIM(db_key) != ''
            """
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    return {db_key: full_name for full_name, db_key in rows}


def _image_count(identity_key, raw_dir, processed_dir):
    raw_path = Path(raw_dir) / identity_key
    processed_path = Path(processed_dir) / identity_key
    raw_count = (
        sum(1 for path in raw_path.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
        if raw_path.is_dir()
        else 0
    )
    if raw_count:
        return raw_count
    return (
        sum(1 for path in processed_path.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
        if processed_path.is_dir()
        else 0
    )


def build_embedding_metadata(
    face_db_path="data/embeddings/db.pkl",
    sql_db_path="app/attendance.db",
    raw_dir="data/raw",
    processed_dir="data/processed",
):
    db = _load_face_db(face_db_path)
    metadata = db.get(FACE_DB_METADATA_KEY) if isinstance(db.get(FACE_DB_METADATA_KEY), dict) else {}
    students = _student_map(sql_db_path)
    now = datetime.now().isoformat()

    identities = {}
    for identity_key, _ in iter_identity_embeddings(db):
        is_student = identity_key in students
        identities[identity_key] = {
            "identity_key": identity_key,
            "display_name": students.get(identity_key, identity_key.replace("_", " ")),
            "source": "student" if is_student else "demo",
            "created_at": now,
            "updated_at": now,
            "image_count": _image_count(identity_key, raw_dir, processed_dir),
        }

    return {
        "version": 1,
        "generated_at": now,
        "embedding_model": metadata.get("embedding_model"),
        "identities": dict(sorted(identities.items())),
    }


def write_embedding_metadata(metadata, metadata_path="data/embedding_metadata.json"):
    path = Path(metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)
    return path


def validate_embedding_metadata(
    metadata_path="data/embedding_metadata.json",
    face_db_path="data/embeddings/db.pkl",
):
    errors = []
    metadata_path = Path(metadata_path)
    if not metadata_path.exists():
        return [f"metadata file not found: {metadata_path}"]

    with open(metadata_path, "r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    identities = metadata.get("identities")
    if not isinstance(identities, dict):
        return ["metadata identities must be an object"]

    db = _load_face_db(face_db_path)
    face_keys = {key for key, _ in iter_identity_embeddings(db)}
    metadata_keys = set(identities)

    for key in sorted(face_keys - metadata_keys):
        errors.append(f"missing metadata for identity: {key}")
    for key in sorted(metadata_keys - face_keys):
        errors.append(f"metadata identity missing embedding: {key}")
    for key, value in sorted(identities.items()):
        if value.get("identity_key") != key:
            errors.append(f"identity_key mismatch for {key}")
        if value.get("source") not in {"demo", "student"}:
            errors.append(f"invalid source for {key}: {value.get('source')}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate or generate embedding metadata.")
    parser.add_argument("--face-db", default="data/embeddings/db.pkl")
    parser.add_argument("--sql-db", default="app/attendance.db")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--metadata", default="data/embedding_metadata.json")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    if args.write:
        metadata = build_embedding_metadata(
            face_db_path=args.face_db,
            sql_db_path=args.sql_db,
            raw_dir=args.raw_dir,
            processed_dir=args.processed_dir,
        )
        write_embedding_metadata(metadata, args.metadata)

    errors = validate_embedding_metadata(
        metadata_path=args.metadata,
        face_db_path=args.face_db,
    )
    if errors:
        print("Embedding metadata OK: False")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Embedding metadata OK: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
