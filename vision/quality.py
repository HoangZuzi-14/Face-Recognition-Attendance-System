from app.face_quality import assess_capture_frame


class FaceQualityChecker:
    def assess(self, frame, faces):
        return assess_capture_frame(frame, faces)
