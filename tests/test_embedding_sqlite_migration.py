import pickle
import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np


class EmbeddingSqliteMigrationTests(unittest.TestCase):
    def test_migrate_pkl_to_sqlite_writes_active_embedding_rows(self):
        from scripts.migrate_pkl_to_sqlite import migrate_pkl_to_sqlite

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            face_db_path = root / "db.pkl"
            sql_db_path = root / "attendance.db"
            with open(face_db_path, "wb") as handle:
                pickle.dump(
                    {
                        "Alice": np.ones(512, dtype=np.float32),
                        "__metadata__": {
                            "embedding_model": "insightface/buffalo_l",
                            "identity_models": {"Alice": "insightface/buffalo_l"},
                        },
                    },
                    handle,
                )

            result = migrate_pkl_to_sqlite(
                face_db_path=face_db_path,
                sql_db_path=sql_db_path,
            )

            self.assertEqual(result["migrated_count"], 1)
            conn = sqlite3.connect(sql_db_path)
            row = conn.execute(
                "SELECT identity_key, source, model_name, is_active, vector_dim, embedding FROM face_embeddings"
            ).fetchone()
            conn.close()

            self.assertEqual(row[0], "Alice")
            self.assertEqual(row[1], "demo")
            self.assertEqual(row[2], "insightface/buffalo_l")
            self.assertEqual(row[3], 1)
            self.assertEqual(row[4], 512)
            self.assertEqual(len(row[5]), 512 * 4)

    def test_load_embeddings_prefers_sqlite_when_available(self):
        from scripts.migrate_pkl_to_sqlite import migrate_pkl_to_sqlite
        from src.embedding_store import load_embeddings

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            face_db_path = root / "db.pkl"
            sql_db_path = root / "attendance.db"
            with open(face_db_path, "wb") as handle:
                pickle.dump({"From_Pickle": np.zeros(512, dtype=np.float32)}, handle)

            sqlite_source = root / "sqlite.pkl"
            with open(sqlite_source, "wb") as handle:
                pickle.dump({"From_SQLite": np.ones(512, dtype=np.float32)}, handle)
            migrate_pkl_to_sqlite(face_db_path=sqlite_source, sql_db_path=sql_db_path)

            loaded = load_embeddings(
                face_db_path=face_db_path,
                sqlite_db_path=sql_db_path,
                prefer_sqlite=True,
            )

            self.assertIn("From_SQLite", loaded)
            self.assertNotIn("From_Pickle", loaded)


if __name__ == "__main__":
    unittest.main()
