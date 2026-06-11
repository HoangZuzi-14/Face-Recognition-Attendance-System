import tempfile
import unittest
from pathlib import Path


class RecognitionEventSchemaScriptTests(unittest.TestCase):
    def test_validate_schema_accepts_current_recognition_event_columns(self):
        from app import database
        from scripts.validate_recognition_event_schema import validate_schema

        with tempfile.TemporaryDirectory() as tmp:
            old_db_path = database.DB_PATH
            database.DB_PATH = str(Path(tmp) / "attendance.db")
            try:
                database.init_db()
                result = validate_schema(database.DB_PATH)

                self.assertTrue(result.ok)
                self.assertEqual(result.missing_columns, [])
            finally:
                database.DB_PATH = old_db_path


if __name__ == "__main__":
    unittest.main()
