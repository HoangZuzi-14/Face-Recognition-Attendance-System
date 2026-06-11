"""Application repository namespace.

This package is a compatibility bridge while repository implementations move
out of the legacy top-level `repositories` package.
"""

from app.path_setup import ensure_repo_root_first

ensure_repo_root_first(__file__)

from repositories.attendance_repository import AttendanceRepository
from repositories.audit_repository import AuditRepository
from repositories.class_repository import ClassRepository
from repositories.face_repository import FaceRepository
from repositories.student_repository import StudentRepository

__all__ = [
    "AttendanceRepository",
    "AuditRepository",
    "ClassRepository",
    "FaceRepository",
    "StudentRepository",
]
