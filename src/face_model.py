import numpy as np


class FaceModel:
    def __init__(
        self,
        model_name="buffalo_l",
        ctx_id=None,
        det_size=(640, 640),
        det_thresh=0.5,
        app=None,
    ):
        self.model_name = model_name
        self.ctx_id = self._resolve_ctx_id(ctx_id)
        self.det_size = det_size
        self.det_thresh = det_thresh
        self.app = app if app is not None else self._create_app(model_name)
        self.app.prepare(ctx_id=self.ctx_id, det_size=self.det_size, det_thresh=self.det_thresh)

    @staticmethod
    def _resolve_ctx_id(ctx_id):
        if ctx_id is not None:
            return ctx_id
        try:
            import onnxruntime

            return 0 if "CUDAExecutionProvider" in onnxruntime.get_available_providers() else -1
        except Exception:
            return -1

    @staticmethod
    def _create_app(model_name):
        from insightface.app import FaceAnalysis

        return FaceAnalysis(
            name=model_name,
            allowed_modules=["detection", "recognition"],
        )

    @staticmethod
    def _normalized_embedding(face):
        embedding = getattr(face, "normed_embedding", None)
        if embedding is None:
            embedding = getattr(face, "embedding", None)
        if embedding is None:
            return None

        embedding = np.asarray(embedding, dtype=np.float32).reshape(-1)
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return None
        return embedding / norm

    def get_faces(self, img_bgr):
        if img_bgr is None:
            return []

        faces = []
        for face in self.app.get(img_bgr):
            embedding = self._normalized_embedding(face)
            if embedding is None:
                continue

            bbox = np.asarray(face.bbox, dtype=np.float32).reshape(-1)
            if bbox.shape[0] < 4:
                continue

            faces.append(
                {
                    "bbox": tuple(int(round(v)) for v in bbox[:4]),
                    "embedding": embedding,
                    "det_score": float(getattr(face, "det_score", 0.0) or 0.0),
                }
            )
        return faces

    def get_embedding(self, img_bgr):
        faces = self.get_faces(img_bgr)
        if not faces:
            return None
        best_face = max(faces, key=lambda face: face["det_score"])
        return best_face["embedding"]


_MODEL = None


def get_face_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = FaceModel()
    return _MODEL
