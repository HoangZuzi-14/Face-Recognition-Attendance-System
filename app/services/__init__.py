"""Application service namespace.

This package is a compatibility bridge while service implementations move out
of the legacy top-level `services` package.
"""

from app.path_setup import ensure_repo_root_first

ensure_repo_root_first(__file__)

from services.attendance_service import AttendanceService
from services.audit_service import AuditService
from services.class_service import ClassService
from services.recognition_service import RecognitionService
from services.student_service import StudentService

__all__ = [
    "AttendanceService",
    "AuditService",
    "ClassService",
    "RecognitionService",
    "StudentService",
]
