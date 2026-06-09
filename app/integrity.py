import os
import pickle
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from src.face_db import FACE_DB_METADATA_KEY


@dataclass
class IntegrityReport:
    students_missing_face_embeddings: list[str] = field(default_factory=list)
    face_embeddings_missing_students: list[str] = field(default_factory=list)
    missing_raw_dirs: list[str] = field(default_factory=list)
    missing_processed_dirs: list[str] = field(default_factory=list)
    attendance_keys_missing_students: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self):
        return not any(
            [
                self.students_missing_face_embeddings,
                self.face_embeddings_missing_students,
                self.missing_raw_dirs,
                self.missing_processed_dirs,
                self.attendance_keys_missing_students,
                self.errors,
            ]
        )

    def to_lines(self, max_items=None):
        lines = [f"Integrity OK: {self.ok}"]
        sections = [
            ("Students missing face embeddings", self.students_missing_face_embeddings),
            ("Face embeddings missing students", self.face_embeddings_missing_students),
            ("Missing raw directories", self.missing_raw_dirs),
            ("Missing processed directories", self.missing_processed_dirs),
            ("Attendance keys missing students", self.attendance_keys_missing_students),
            ("Errors", self.errors),
        ]
        for title, values in sections:
            lines.append(f"{title}: {len(values)}")
            visible_values = values
            if max_items is not None:
                visible_values = values[:max_items]
            for value in visible_values:
                lines.append(f"  - {value}")
            if max_items is not None and len(values) > max_items:
                lines.append(f"  ... {len(values) - max_items} more")
        return lines


def _load_face_keys(face_db_path):
    path = Path(face_db_path)
    if not path.exists():
        return set(), [f"Face DB not found: {path}"]
    try:
        with open(path, "rb") as f:
            db = pickle.load(f)
    except Exception as exc:
        return set(), [f"Cannot read face DB {path}: {exc}"]
    if not isinstance(db, dict):
        return set(), [f"Face DB is not a dict: {path}"]
    return {str(key) for key in db.keys() if key != FACE_DB_METADATA_KEY}, []


def _fetch_single_column(conn, query):
    try:
        return {
            str(row[0])
            for row in conn.execute(query).fetchall()
            if row[0] is not None and str(row[0]).strip()
        }, []
    except sqlite3.Error as exc:
        return set(), [str(exc)]


def validate_integrity(
    sql_db_path="app/attendance.db",
    face_db_path="data/embeddings/db.pkl",
    raw_dir="data/raw",
    processed_dir="data/processed",
):
    """Check synchronization between SQLite, face DB, and face image folders."""
    report = IntegrityReport()

    face_keys, face_errors = _load_face_keys(face_db_path)
    report.errors.extend(face_errors)

    sql_path = Path(sql_db_path)
    if not sql_path.exists():
        report.errors.append(f"SQLite DB not found: {sql_path}")
        return report

    try:
        conn = sqlite3.connect(sql_path)
    except sqlite3.Error as exc:
        report.errors.append(f"Cannot connect SQLite DB {sql_path}: {exc}")
        return report

    try:
        student_keys, errors = _fetch_single_column(
            conn, "SELECT db_key FROM students WHERE db_key IS NOT NULL AND db_key != ''"
        )
        report.errors.extend(errors)

        attendance_keys, errors = _fetch_single_column(
            conn,
            "SELECT DISTINCT student_db_key FROM attendance "
            "WHERE student_db_key IS NOT NULL AND student_db_key != ''",
        )
        report.errors.extend(errors)
    finally:
        conn.close()

    report.students_missing_face_embeddings = sorted(student_keys - face_keys)
    report.face_embeddings_missing_students = sorted(face_keys - student_keys)
    report.attendance_keys_missing_students = sorted(attendance_keys - student_keys)

    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    for key in sorted(student_keys):
        if not os.path.isdir(raw_path / key):
            report.missing_raw_dirs.append(key)
        if not os.path.isdir(processed_path / key):
            report.missing_processed_dirs.append(key)

    return report
