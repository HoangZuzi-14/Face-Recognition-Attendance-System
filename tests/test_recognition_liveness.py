import unittest


class RecognitionLivenessGateTests(unittest.TestCase):
    def test_disabled_liveness_allows_attendance_flow(self):
        from src.recognize import evaluate_liveness_gate

        gate = evaluate_liveness_gate(
            frame="frame",
            face_bbox=(0, 0, 10, 10),
            enabled=False,
        )

        self.assertTrue(gate.allowed)
        self.assertEqual(gate.decision, "ACCEPT")
        self.assertEqual(gate.result.label, "DISABLED")

    def test_spoof_liveness_rejects_attendance_flow(self):
        from src.liveness import LivenessResult
        from src.recognize import evaluate_liveness_gate

        def assessor(frame, landmarks=None, face_bbox=None):
            return LivenessResult(
                score=0.1,
                label="SPOOF",
                reasons=["pad_low_score"],
                details={},
            )

        gate = evaluate_liveness_gate(
            frame="frame",
            face_bbox=(0, 0, 10, 10),
            enabled=True,
            assessor=assessor,
        )

        self.assertFalse(gate.allowed)
        self.assertEqual(gate.decision, "REJECT_SPOOF")
        self.assertEqual(gate.result.label, "SPOOF")
        self.assertEqual(gate.short_reason, "pad_low_score")

    def test_unknown_and_challenge_do_not_allow_attendance_flow(self):
        from src.liveness import LivenessResult
        from src.recognize import evaluate_liveness_gate

        def unknown_assessor(frame, landmarks=None, face_bbox=None):
            return LivenessResult(0.0, "UNKNOWN", ["face_bbox_missing"], {})

        def challenge_assessor(frame, landmarks=None, face_bbox=None):
            return LivenessResult(0.5, "CHALLENGE", ["blink_required"], {})

        unknown_gate = evaluate_liveness_gate(
            frame="frame",
            face_bbox=None,
            enabled=True,
            assessor=unknown_assessor,
        )
        challenge_gate = evaluate_liveness_gate(
            frame="frame",
            face_bbox=(0, 0, 10, 10),
            enabled=True,
            assessor=challenge_assessor,
        )

        self.assertFalse(unknown_gate.allowed)
        self.assertEqual(unknown_gate.decision, "REJECT_UNKNOWN")
        self.assertFalse(challenge_gate.allowed)
        self.assertEqual(challenge_gate.decision, "CHALLENGE_REQUIRED")

    def test_gate_passes_rppg_result_to_assessor_when_available(self):
        from src.liveness import LivenessResult
        from src.recognize import evaluate_liveness_gate
        from src.rppg import RppgResult

        observed = {}

        def assessor(frame, landmarks=None, face_bbox=None, rppg_result=None):
            observed["rppg_result"] = rppg_result
            return LivenessResult(1.0, "LIVE", ["pulse_detected"], {})

        pulse = RppgResult(label="LIVE", pulse_confidence=0.7, bpm=72.0)
        gate = evaluate_liveness_gate(
            frame="frame",
            face_bbox=(0, 0, 10, 10),
            enabled=True,
            assessor=assessor,
            rppg_result=pulse,
        )

        self.assertTrue(gate.allowed)
        self.assertIs(observed["rppg_result"], pulse)


if __name__ == "__main__":
    unittest.main()
