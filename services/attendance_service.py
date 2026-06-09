"""Service for attendance operations."""

from repositories.attendance_repository import AttendanceRepository


class AttendanceService:
    def __init__(self, repo=None):
        self._repo = repo or AttendanceRepository()

    def log_attendance(self, db_key, class_id, confidence, deadline_hour=8, deadline_minute=0):
        return self._repo.log_attendance(db_key, class_id, confidence, deadline_hour, deadline_minute)

    def get_full_attendance(self, class_id, deadline_hour=8, deadline_minute=0):
        return self._repo.get_full_attendance(class_id, deadline_hour, deadline_minute)

    def get_attended_today(self, class_id):
        return self._repo.get_attended_today(class_id)

    def export_csv(self, class_id=None, export_path="app/attendance_export.csv"):
        return self._repo.export_csv(class_id, export_path)

    def clear_today(self, class_id=None):
        self._repo.clear_today(class_id)

    def get_recognition_stats(self, class_id=None, limit=50):
        return self._repo.get_recognition_stats(class_id, limit)
