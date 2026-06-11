import pickle
import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np


class EmbeddingMetadataTests(unittest.TestCase):
    def test_build_metadata_marks_student_and_demo_sources(self):
        from scripts.validate_embedding_metadata import build_embedding_metadata

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            face_db_path = root / "db.pkl"
            sql_db_path = root / "attendance.db"
            raw_dir = root / "raw"
            processed_dir = root / "processed"
            (raw_dir / "Student_A").mkdir(parents=True)
            (processed_dir / "Demo_A").mkdir(parents=True)
            (raw_dir / "Student_A" / "one.jpg").write_bytes(b"raw")
            (processed_dir / "Demo_A" / "one.jpg").write_bytes(b"processed")
            (processed_dir / "Demo_A" / "two.jpg").write_bytes(b"processed")

            with open(face_db_path, "wb") as handle:
                pickle.dump(
                    {
                        "Student_A": np.ones(512, dtype=np.float32),
                        "Demo_A": np.zeros(512, dtype=np.float32),
                        "__metadata__": {"embedding_model": "insightface/buffalo_l"},
                    },
                    handle,
                )

            conn = sqlite3.connect(sql_db_path)
            conn.execute(
                "CREATE TABLE students (id INTEGER PRIMARY KEY, full_name TEXT, db_key TEXT)"
            )
            conn.execute(
                "INSERT INTO students (full_name, db_key) VALUES (?, ?)",
                ("Student A", "Student_A"),
            )
            conn.commit()
            conn.close()

            metadata = build_embedding_metadata(
                face_db_path=face_db_path,
                sql_db_path=sql_db_path,
                raw_dir=raw_dir,
                processed_dir=processed_dir,
            )

            self.assertEqual(metadata["version"], 1)
            self.assertEqual(metadata["embedding_model"], "insightface/buffalo_l")
            self.assertEqual(metadata["identities"]["Student_A"]["source"], "student")
            self.assertEqual(metadata["identities"]["Student_A"]["display_name"], "Student A")
            self.assertEqual(metadata["identities"]["Student_A"]["image_count"], 1)
            self.assertEqual(metadata["identities"]["Demo_A"]["source"], "demo")
            self.assertEqual(metadata["identities"]["Demo_A"]["display_name"], "Demo A")
            self.assertEqual(metadata["identities"]["Demo_A"]["image_count"], 2)

    def test_validate_metadata_reports_missing_identity_entries(self):
        from scripts.validate_embedding_metadata import validate_embedding_metadata

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            face_db_path = root / "db.pkl"
            metadata_path = root / "embedding_metadata.json"
            with open(face_db_path, "wb") as handle:
                pickle.dump({"Alice": np.ones(512, dtype=np.float32)}, handle)
            metadata_path.write_text(
                '{"version": 1, "identities": {}}',
                encoding="utf-8",
            )

            errors = validate_embedding_metadata(
                metadata_path=metadata_path,
                face_db_path=face_db_path,
            )

            self.assertIn("missing metadata for identity: Alice", errors)


if __name__ == "__main__":
    unittest.main()
