import unittest

import numpy as np


class _FakeFace:
    def __init__(self, bbox, embedding, det_score):
        self.bbox = np.array(bbox, dtype=np.float32)
        self.embedding = np.array(embedding, dtype=np.float32)
        self.det_score = det_score

    @property
    def normed_embedding(self):
        return self.embedding / np.linalg.norm(self.embedding)


class _FakeInsightFaceApp:
    def __init__(self, faces):
        self.faces = faces
        self.prepared = False
        self.prepare_args = None

    def prepare(self, **kwargs):
        self.prepared = True
        self.prepare_args = kwargs

    def get(self, img_bgr):
        return self.faces


class FaceModelTests(unittest.TestCase):
    def test_get_faces_returns_bbox_score_and_normalized_embedding(self):
        from src.face_model import FaceModel

        app = _FakeInsightFaceApp([
            _FakeFace([1, 2, 11, 12], np.ones(512) * 2, 0.91),
        ])

        model = FaceModel(app=app, ctx_id=-1)
        faces = model.get_faces(np.zeros((32, 32, 3), dtype=np.uint8))

        self.assertTrue(app.prepared)
        self.assertEqual(app.prepare_args["ctx_id"], -1)
        self.assertEqual(len(faces), 1)
        self.assertEqual(faces[0]["bbox"], (1, 2, 11, 12))
        self.assertEqual(faces[0]["det_score"], 0.91)
        self.assertEqual(faces[0]["embedding"].shape, (512,))
        self.assertAlmostEqual(float(np.linalg.norm(faces[0]["embedding"])), 1.0, places=5)

    def test_get_embedding_returns_highest_score_face_embedding(self):
        from src.face_model import FaceModel

        low_score = _FakeFace([1, 1, 10, 10], [1.0] + [0.0] * 511, 0.20)
        high_score = _FakeFace([2, 2, 20, 20], [0.0, 1.0] + [0.0] * 510, 0.95)
        model = FaceModel(app=_FakeInsightFaceApp([low_score, high_score]), ctx_id=-1)

        embedding = model.get_embedding(np.zeros((32, 32, 3), dtype=np.uint8))

        self.assertEqual(embedding.shape, (512,))
        self.assertAlmostEqual(float(embedding[0]), 0.0)
        self.assertAlmostEqual(float(embedding[1]), 1.0)

    def test_get_embedding_returns_none_when_no_face_detected(self):
        from src.face_model import FaceModel

        model = FaceModel(app=_FakeInsightFaceApp([]), ctx_id=-1)

        self.assertIsNone(model.get_embedding(np.zeros((32, 32, 3), dtype=np.uint8)))


if __name__ == "__main__":
    unittest.main()
