import unittest


class AppLayerNamespaceTests(unittest.TestCase):
    def test_repository_namespace_exports_existing_repositories(self):
        from app.repositories import ClassRepository, StudentRepository
        from app.repositories.class_repository import ClassRepository as NamespacedClassRepository
        from repositories.class_repository import ClassRepository as ExistingClassRepository

        self.assertIs(ClassRepository, ExistingClassRepository)
        self.assertIs(NamespacedClassRepository, ExistingClassRepository)
        self.assertTrue(callable(StudentRepository))

    def test_service_namespace_exports_existing_services(self):
        from app.services import AttendanceService, RecognitionService
        from app.services.attendance_service import AttendanceService as NamespacedAttendanceService
        from services.attendance_service import AttendanceService as ExistingAttendanceService

        self.assertIs(AttendanceService, ExistingAttendanceService)
        self.assertIs(NamespacedAttendanceService, ExistingAttendanceService)
        self.assertTrue(callable(RecognitionService))


if __name__ == "__main__":
    unittest.main()
