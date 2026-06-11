"""Unit tests for the repository layer."""

import tempfile
import unittest
from pathlib import Path
import pandas as pd

from app import database
from repositories.class_repository import ClassRepository
from repositories.student_repository import StudentRepository
from repositories.attendance_repository import AttendanceRepository
from repositories.face_repository import FaceRepository
from repositories.audit_repository import AuditRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        database.DB_PATH = str(Path(self.tmp_dir.name) / "attendance.db")
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db_path
        self.tmp_dir.cleanup()

    def test_class_repo_crud(self):
        repo = ClassRepository()
        
        # Test creation
        class_id = repo.create_class("CS101")
        self.assertIsNotNone(class_id)
        
        # Duplicate class creation should return None
        duplicate_id = repo.create_class("CS101")
        self.assertIsNone(duplicate_id)

        # Test listing (only CS101 exists)
        df = repo.get_classes()
        self.assertEqual(len(df), 1)

        # Test default class assurance
        default_id = repo.ensure_default_class()
        self.assertIsNotNone(default_id)

        # Listing should now contain both
        df_both = repo.get_classes()
        self.assertEqual(len(df_both), 2)

        # Check has roster (should be False for newly created class)
        self.assertFalse(repo.class_has_roster(class_id))

        # Test deletion
        repo.delete_class(class_id)
        df_after = repo.get_classes()
        self.assertEqual(len(df_after), 1)  # Only default class left

    def test_student_repo_crud(self):
        student_repo = StudentRepository()
        class_repo = ClassRepository()

        class_id = class_repo.ensure_default_class()

        # Ensure student in class
        student_id = student_repo.ensure_student_in_class(
            class_id=class_id,
            full_name="Alice Smith",
            db_key="Alice_Smith",
            mssv="20260001"
        )
        self.assertIsNotNone(student_id)

        # Link face
        student_repo.link_student_face("20260001", "Alice_New_Key")

        # Get by db key
        info = student_repo.get_student_by_db_key("Alice_New_Key")
        self.assertIsNotNone(info)
        self.assertEqual(info["full_name"], "Alice Smith")

        # List all
        students_df = student_repo.get_all_students()
        self.assertGreaterEqual(len(students_df), 1)

    def test_student_repo_roster_upload(self):
        student_repo = StudentRepository()
        class_repo = ClassRepository()
        class_id = class_repo.create_class("Physics")

        roster_data = {
            "MSSV": ["PH001", "PH002"],
            "FullName": ["Robert Boyle", "Marie Curie"]
        }
        df = pd.DataFrame(roster_data)

        # Valid upload
        added, skipped = student_repo.upload_roster(class_id, df)
        self.assertEqual(added, 2)
        self.assertEqual(skipped, 0)

        # Check roster was added
        self.assertTrue(class_repo.class_has_roster(class_id))

    def test_attendance_repo_log_and_clear(self):
        att_repo = AttendanceRepository()
        class_repo = ClassRepository()
        student_repo = StudentRepository()

        class_id = class_repo.ensure_default_class()
        student_repo.ensure_student_in_class(
            class_id=class_id,
            full_name="Bob Builder",
            db_key="Bob_Builder",
            mssv="BOB01"
        )

        # Log attendance
        logged, status = att_repo.log_attendance("Bob_Builder", class_id, 0.95)
        self.assertTrue(logged)
        self.assertIn(status, ["PRESENT", "LATE"])

        # Try logging duplicate attendance
        logged2, status2 = att_repo.log_attendance("Bob_Builder", class_id, 0.98)
        self.assertFalse(logged2)

        # Get full attendance DataFrame
        full_df = att_repo.get_full_attendance(class_id)
        self.assertGreaterEqual(len(full_df), 1)
        self.assertIn("Bob Builder", full_df["Họ và Tên"].values)

        # Check today log
        today_set = att_repo.get_attended_today(class_id)
        self.assertIn("Bob_Builder", today_set)

        # Test clear
        att_repo.clear_today(class_id)
        cleared_set = att_repo.get_attended_today(class_id)
        self.assertNotIn("Bob_Builder", cleared_set)

    def test_face_repo_sync_and_crud(self):
        face_repo = FaceRepository()
        student_repo = StudentRepository()
        class_repo = ClassRepository()

        class_id = class_repo.ensure_default_class()
        student_repo.ensure_student_in_class(
            class_id=class_id,
            full_name="John Doe",
            db_key="John_Doe",
            mssv="JD01"
        )

        # Sync identities
        face_repo.sync_from_students()

        # Count active identities
        count = face_repo.count_active()
        self.assertGreaterEqual(count, 1)

        # Get identity details
        details = face_repo.get_identity_by_person_key("John_Doe")
        self.assertIsNotNone(details)
        self.assertEqual(details["mssv"], "JD01")

        # Deactivate
        face_repo.deactivate_identity("John_Doe")
        details_after = face_repo.get_identity_by_person_key("John_Doe")
        self.assertFalse(details_after["active"])

    def test_audit_repo_logs(self):
        audit_repo = AuditRepository()

        # Log action
        audit_repo.log("test.action", entity_type="test", entity_id="123", details="Hello Test")

        # Query recent logs
        logs = audit_repo.get_recent_logs(limit=5)
        self.assertGreaterEqual(len(logs), 1)
        self.assertIn("test.action", logs["action"].values)


if __name__ == "__main__":
    unittest.main()
