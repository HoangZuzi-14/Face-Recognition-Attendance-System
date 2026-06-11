import unittest

import numpy as np


class FaceDbMetadataTests(unittest.TestCase):
    def test_metadata_is_added_without_changing_identity_dict_shape(self):
        from src.face_db import (
            FACE_DB_METADATA_KEY,
            EMBEDDING_MODEL_ID,
            iter_identity_embeddings,
            set_identity_embedding,
        )

        db = {"Legacy": np.array([1.0, 0.0])}

        set_identity_embedding(db, "New", np.array([0.0, 1.0]))

        self.assertIn(FACE_DB_METADATA_KEY, db)
        self.assertEqual(db[FACE_DB_METADATA_KEY]["embedding_model"], EMBEDDING_MODEL_ID)
        self.assertEqual(
            db[FACE_DB_METADATA_KEY]["identity_models"]["New"],
            EMBEDDING_MODEL_ID,
        )
        self.assertNotIn("Legacy", db[FACE_DB_METADATA_KEY]["identity_models"])
        self.assertEqual(
            [name for name, _ in iter_identity_embeddings(db)],
            ["Legacy", "New"],
        )

    def test_recognition_helpers_ignore_metadata_key(self):
        from src.face_db import FACE_DB_METADATA_KEY, EMBEDDING_MODEL_ID
        from src.recognize import filter_face_db, find_best_match

        db = {
            FACE_DB_METADATA_KEY: {
                "embedding_model": EMBEDDING_MODEL_ID,
                "identity_models": {"A": EMBEDDING_MODEL_ID},
            },
            "A": np.array([1.0, 0.0]),
            "B": np.array([0.0, 1.0]),
        }

        best, second = find_best_match(np.array([1.0, 0.0]), db)
        filtered = filter_face_db(db, {"A"})

        self.assertEqual(best[0], "A")
        self.assertEqual(second[0], "B")
        self.assertEqual(set(filtered.keys()), {FACE_DB_METADATA_KEY, "A"})


if __name__ == "__main__":
    unittest.main()
