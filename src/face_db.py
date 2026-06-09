from datetime import datetime


FACE_DB_METADATA_KEY = "__metadata__"
EMBEDDING_BACKEND = "insightface"
EMBEDDING_MODEL_NAME = "buffalo_l"
EMBEDDING_MODEL_ID = f"{EMBEDDING_BACKEND}/{EMBEDDING_MODEL_NAME}"
EMBEDDING_DIM = 512


def ensure_metadata(db):
    metadata = db.get(FACE_DB_METADATA_KEY)
    if not isinstance(metadata, dict):
        metadata = {}
        db[FACE_DB_METADATA_KEY] = metadata

    metadata.setdefault("embedding_backend", EMBEDDING_BACKEND)
    metadata.setdefault("embedding_model", EMBEDDING_MODEL_ID)
    metadata.setdefault("embedding_dim", EMBEDDING_DIM)
    metadata.setdefault("identity_models", {})
    metadata.setdefault(
        "migration_note",
        (
            "DeepFace/ArcFace embeddings are not compatible with "
            "InsightFace buffalo_l embeddings. Rebuild db.pkl after migration "
            "before relying on recognition results."
        ),
    )
    metadata["updated_at"] = datetime.now().isoformat()
    return metadata


def set_identity_embedding(db, person_key, embedding, model_id=EMBEDDING_MODEL_ID):
    # Existing DeepFace/ArcFace vectors share the old key-only layout. New
    # writes mark per-identity model version so mixed DBs can be identified;
    # rebuild db.pkl after this migration to make every identity comparable.
    db[person_key] = embedding
    metadata = ensure_metadata(db)
    metadata["identity_models"][person_key] = model_id
    metadata["updated_at"] = datetime.now().isoformat()


def iter_identity_embeddings(db):
    for name, embedding in db.items():
        if name == FACE_DB_METADATA_KEY:
            continue
        yield name, embedding


def identity_count(db):
    return sum(1 for _ in iter_identity_embeddings(db))


def copy_metadata_if_present(source_db, target_db):
    metadata = source_db.get(FACE_DB_METADATA_KEY)
    if isinstance(metadata, dict):
        target_db[FACE_DB_METADATA_KEY] = metadata.copy()
        identity_models = metadata.get("identity_models")
        if isinstance(identity_models, dict):
            target_db[FACE_DB_METADATA_KEY]["identity_models"] = {
                key: value
                for key, value in identity_models.items()
                if key in target_db
            }
