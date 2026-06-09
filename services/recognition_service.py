"""Service for face recognition operations."""

from repositories.class_repository import ClassRepository
from src.recognize import filter_face_db
from repositories.attendance_repository import AttendanceRepository
from src.face_db import iter_identity_embeddings


class RecognitionService:
    def __init__(self, class_repo=None, attendance_repo=None):
        self._class_repo = class_repo or ClassRepository()
        self._attendance_repo = attendance_repo or AttendanceRepository()

    def build_active_face_db(self, full_face_db, class_id):
        """Build a face DB containing only students linked to the given class."""
        if class_id is None:
            return full_face_db
        class_keys = self._class_repo.get_class_db_keys(class_id)
        return filter_face_db(full_face_db, class_keys)

    def get_missing_face_keys(self, full_face_db, class_id):
        """Return class-linked db_keys that do not have embeddings in db.pkl."""
        if class_id is None:
            return []
        class_keys = self._class_repo.get_class_db_keys(class_id)
        face_keys = {name for name, _ in iter_identity_embeddings(full_face_db or {})}
        return sorted(key for key in class_keys if key not in face_keys)

    def get_stats(self, class_id=None):
        """Get recognition event statistics."""
        return self._attendance_repo.get_recognition_stats(class_id)
