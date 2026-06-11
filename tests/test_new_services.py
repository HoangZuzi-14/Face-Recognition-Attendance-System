"""Unit tests for the service layer."""

import tempfile
import unittest
from pathlib import Path
import pandas as pd

from app import database
from services.class_service import ClassService
from services.student_service import StudentService
from services.attendance_service import AttendanceService
from services.audit_service import AuditService
from services.recognition_service import RecognitionService


class ServiceLayerTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        database.DB_PATH = str(Path(self.tmp_dir.name) / "attendance.db")
        database.init_db()

        self.class_service = ClassService()
        self.student_service = StudentService()
        self.attendance_service = AttendanceService()
        self.audit_service = AuditService()
        self.recognition_service = RecognitionService()

    def tearDown(self):
        database.DB_PATH = self.old_db_path
        self.tmp_dir.cleanup()

    def test_class_service_workflow(self):
        # Create class via service
        class_id = self.class_service.create_class("Math_101")
        self.assertIsNotNone(class_id)

        # Check default class creation
        default_id = self.class_service.ensure_default_class()
        self.assertIsNotNone(default_id)

        # Get all classes
        classes_df = self.class_service.get_classes()
        self.assertEqual(len(classes_df), 2)

        # Class has roster (should be False)
        self.assertFalse(self.class_service.class_has_roster(class_id))

        # Delete class
        self.class_service.delete_class(class_id)
        self.assertEqual(len(self.class_service.get_classes()), 1)

    def test_student_service_workflow(self):
        class_id = self.class_service.ensure_default_class()
        
        # Add student
        student_id = self.student_service.ensure_student_in_class(
            class_id, "Jane Doe", "Jane_Doe", "JD002"
        )
        self.assertIsNotNone(student_id)

        # Link face
        self.student_service.link_student_face("JD002", "Jane_Modified_Key")

        # Query student
        info = self.student_service.get_student_by_db_key("Jane_Modified_Key")
        self.assertEqual(info["full_name"], "Jane Doe")

        # Get all students
        students = self.student_service.get_all_students()
        self.assertGreaterEqual(len(students), 1)

    def test_student_service_roster_upload(self):
        class_id = self.class_service.ensure_default_class()
        
        # Create roster dataframe
        df = pd.DataFrame({
            "MSSV": ["ST001", "ST002"],
            "FullName": ["Grace Hopper", "Ada Lovelace"]
        })

        # Validate DataFrame
        valid, msg = self.student_service.validate_roster_dataframe(df)
        self.assertTrue(valid)

        # Upload
        added, skipped = self.student_service.upload_roster(class_id, df)
        self.assertEqual(added, 2)
        self.assertEqual(skipped, 0)

        # Roster ready flag check
        self.assertTrue(self.class_service.class_has_roster(class_id))

    def test_attendance_service_workflow(self):
        class_id = self.class_service.ensure_default_class()
        self.student_service.ensure_student_in_class(
            class_id, "Alan Turing", "Alan_Turing", "AT001"
        )

        # Log attendance
        logged, status = self.attendance_service.log_attendance("Alan_Turing", class_id, 0.99)
        self.assertTrue(logged)
        self.assertIn(status, ["PRESENT", "LATE"])

        # Fetch today attended db keys
        attended = self.attendance_service.get_attended_today(class_id)
        self.assertIn("Alan_Turing", attended)

        # Export CSV
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "attendance.csv"
            self.attendance_service.export_csv(class_id, str(csv_path))
            self.assertTrue(csv_path.exists())

        # Clear attendance
        self.attendance_service.clear_today(class_id)
        self.assertEqual(len(self.attendance_service.get_attended_today(class_id)), 0)

    def test_audit_service_workflow(self):
        # Log action via AuditService
        self.audit_service.log(
            "service.test",
            entity_type="service",
            entity_id="test_id",
            details="Service check details"
        )

        # Get logs
        logs = self.audit_service.get_recent_logs()
        self.assertGreaterEqual(len(logs), 1)
        self.assertIn("service.test", logs["action"].values)

    def test_class_service_ensure_default_class_existing(self):
        # Multiple calls should return the same class ID
        id1 = self.class_service.ensure_default_class()
        id2 = self.class_service.ensure_default_class()
        self.assertEqual(id1, id2)

    def test_student_service_ensure_default_roster(self):
        class_id = self.class_service.ensure_default_class()
        added, skipped = self.student_service.ensure_default_roster(class_id)
        self.assertEqual(added, 30)
        self.assertTrue(self.class_service.class_has_roster(class_id))

    def test_attendance_service_log_attendance_deadline(self):
        class_id = self.class_service.ensure_default_class()
        self.student_service.ensure_student_in_class(
            class_id, "Turing Test", "Turing_Test", "TT99"
        )
        # Log late (deadline: 0:00, current time will always be greater than 00:00)
        logged, status = self.attendance_service.log_attendance("Turing_Test", class_id, 0.95, deadline_hour=0, deadline_minute=0)
        self.assertTrue(logged)
        self.assertEqual(status, "LATE")

    def test_audit_service_limit(self):
        # Write 5 audit logs
        for i in range(5):
            self.audit_service.log(f"test.limit.{i}", entity_type="test", entity_id=str(i))
        
        # Query with limit 3
        logs = self.audit_service.get_recent_logs(limit=3)
        self.assertEqual(len(logs), 3)

    def test_recognition_service_workflow(self):
        class_id = self.class_service.ensure_default_class()
        self.student_service.ensure_student_in_class(
            class_id, "Jane Austin", "Jane_Austin", "JA01"
        )
        
        # Build face DB (should contain Jane_Austin, skip Out_Of_Class)
        face_db = {
            "Jane_Austin": [0.1, 0.2],
            "Out_Of_Class": [0.3, 0.4]
        }
        active_db = self.recognition_service.build_active_face_db(face_db, class_id)
        self.assertIn("Jane_Austin", active_db)
        self.assertNotIn("Out_Of_Class", active_db)


if __name__ == "__main__":
    unittest.main()
