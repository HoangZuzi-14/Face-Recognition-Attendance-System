"""Service for student management operations."""

from repositories.student_repository import StudentRepository


class StudentService:
    def __init__(self, repo=None):
        self._repo = repo or StudentRepository()

    def get_all_students(self):
        return self._repo.get_all_students()

    def get_student_by_db_key(self, db_key):
        return self._repo.get_student_by_db_key(db_key)

    def link_student_face(self, mssv, db_key):
        self._repo.link_student_face(mssv, db_key)

    def ensure_student_in_class(self, class_id, full_name, db_key, mssv=None):
        return self._repo.ensure_student_in_class(class_id, full_name, db_key, mssv)

    def upload_roster(self, class_id, df, existing_faces=None):
        return self._repo.upload_roster(class_id, df, existing_faces)

    def ensure_default_roster(self, class_id, existing_faces=None):
        return self._repo.ensure_default_roster(class_id, existing_faces)

    def validate_roster_dataframe(self, df):
        return self._repo.validate_roster_dataframe(df)
