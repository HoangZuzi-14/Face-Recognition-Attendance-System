import pickle
import tempfile
import unittest
from pathlib import Path

import numpy as np


class EmbeddingStoreTests(unittest.TestCase):
    def test_save_embeddings_safely_backs_up_and_writes_valid_db(self):
        from src.embedding_store import load_embeddings, save_embeddings_safely

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "db.pkl"
            backup_root = root / "backups"
            with open(db_path, "wb") as handle:
                pickle.dump({"Old": np.zeros(512, dtype=np.float32)}, handle)

            result = save_embeddings_safely(
                {"New": np.ones(512, dtype=np.float32)},
                face_db_path=db_path,
                backup_root=backup_root,
                required_keys={"New"},
            )

            self.assertTrue(result["ok"])
            self.assertTrue(Path(result["backup_path"]).exists())
            loaded = load_embeddings(face_db_path=db_path, prefer_sqlite=False)
            self.assertIn("New", loaded)
            self.assertNotIn("Old", loaded)

    def test_load_embeddings_raises_for_corrupt_pickle(self):
        from src.embedding_store import EmbeddingStoreError, load_embeddings

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "db.pkl"
            db_path.write_bytes(b"not-a-pickle")

            with self.assertRaises(EmbeddingStoreError):
                load_embeddings(face_db_path=db_path, prefer_sqlite=False)

    def test_save_embeddings_safely_rolls_back_when_validation_fails(self):
        from src.embedding_store import save_embeddings_safely

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "db.pkl"
            with open(db_path, "wb") as handle:
                pickle.dump({"Old": np.zeros(512, dtype=np.float32)}, handle)

            result = save_embeddings_safely(
                {"Broken": np.ones(512, dtype=np.float32)},
                face_db_path=db_path,
                backup_root=root / "backups",
                validator=lambda db: (False, ["forced validation failure"]),
            )

            self.assertFalse(result["ok"])
            self.assertIn("forced validation failure", result["errors"])
            with open(db_path, "rb") as handle:
                restored = pickle.load(handle)
            self.assertIn("Old", restored)
            self.assertNotIn("Broken", restored)


if __name__ == "__main__":
    unittest.main()
