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

    def test_fake_pad_live_is_allowed_to_proceed_through_gate(self):
        import numpy as np
        from src.liveness import assess_liveness
        from src.pad import PADResult
        from src.recognize import evaluate_liveness_gate

        class LivePadModel:
            def predict(self, frame, face_bbox):
                return PADResult(
                    live_score=0.9,
                    print_score=0.05,
                    replay_score=0.05,
                    spoof_score=0.1,
                    label="LIVE",
                )

        def assessor(frame, landmarks=None, face_bbox=None, rppg_result=None):
            return assess_liveness(frame, face_bbox=face_bbox, pad_model=LivePadModel())

        gate = evaluate_liveness_gate(
            frame=np.ones((100, 100, 3), dtype=np.uint8),
            face_bbox=(10, 10, 90, 90),
            enabled=True,
            assessor=assessor,
        )

        self.assertTrue(gate.allowed)
        self.assertEqual(gate.decision, "ACCEPT")
        self.assertEqual(gate.result.label, "LIVE")

    def test_fake_pad_spoof_rejects_through_gate(self):
        import numpy as np
        from src.liveness import assess_liveness
        from src.pad import PADResult
        from src.recognize import evaluate_liveness_gate

        class SpoofPadModel:
            def predict(self, frame, face_bbox):
                return PADResult(
                    live_score=0.1,
                    print_score=0.7,
                    replay_score=0.2,
                    spoof_score=0.9,
                    label="SPOOF",
                )

        def assessor(frame, landmarks=None, face_bbox=None, rppg_result=None):
            return assess_liveness(frame, face_bbox=face_bbox, pad_model=SpoofPadModel())

        gate = evaluate_liveness_gate(
            frame=np.ones((100, 100, 3), dtype=np.uint8),
            face_bbox=(10, 10, 90, 90),
            enabled=True,
            assessor=assessor,
        )

        self.assertFalse(gate.allowed)
        self.assertEqual(gate.decision, "REJECT_SPOOF")
        self.assertEqual(gate.result.label, "SPOOF")

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

    def test_process_frame_does_not_log_attendance_during_review(self):
        from unittest.mock import patch, MagicMock
        import numpy as np
        from src.recognize import process_frame, reset_trackers, MatchDecision
        
        # Reset tracker state first
        reset_trackers()

        fake_face = {"bbox": (10, 10, 90, 90), "embedding": np.ones(512), "landmarks": np.zeros((5, 2))}
        
        # Mock get_face_model to return our fake face
        mock_face_model = MagicMock()
        mock_face_model.get_faces.return_value = [fake_face]

        # We will mock classify_match to return NEED_REVIEW
        with patch('src.recognize.get_face_model', return_value=mock_face_model), \
             patch('src.recognize.classify_match', return_value=MatchDecision("NEED_REVIEW", 0.60, "low_confidence")), \
             patch('src.recognize.log_attendance', return_value=(True, "PRESENT")) as mock_log_att, \
             patch('src.recognize.get_attended_today_for_class', return_value=set()):
            
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            db = {"Alice": np.ones(512)}
            
            # Process two frames to exceed VOTE_WINDOW (2) and trigger temporal voting log
            process_frame(frame, db, class_id=1, respect_skip=False)
            process_frame(frame, db, class_id=1, respect_skip=False)
            
            # Assert log_attendance was NEVER called because status is NEED_REVIEW
            mock_log_att.assert_not_called()

    def test_process_frame_does_not_log_attendance_when_liveness_not_allowed(self):
        from unittest.mock import patch, MagicMock
        import numpy as np
        from src.recognize import (
            get_tracker_hud_snapshot,
            process_frame,
            reset_trackers,
            MatchDecision,
            LivenessGateDecision,
        )
        
        reset_trackers()

        fake_face = {"bbox": (10, 10, 90, 90), "embedding": np.ones(512), "landmarks": np.zeros((5, 2))}
        mock_face_model = MagicMock()
        mock_face_model.get_faces.return_value = [fake_face]

        # Mock evaluate_liveness_gate to return allowed=False
        from src.liveness import LivenessResult
        mock_gate = LivenessGateDecision(
            allowed=False,
            decision="REJECT_SPOOF",
            result=LivenessResult(0.1, "SPOOF", ["test_spoof"], {}),
            short_reason="test_spoof"
        )

        with patch('src.recognize.get_face_model', return_value=mock_face_model), \
             patch('src.recognize.evaluate_liveness_gate', return_value=mock_gate), \
             patch('src.recognize.classify_match', return_value=MatchDecision("ACCEPT", 0.95, "strong")), \
             patch('src.recognize.log_attendance', return_value=(True, "PRESENT")) as mock_log_att, \
             patch('src.recognize.get_attended_today_for_class', return_value=set()):
            
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            db = {"Alice": np.ones(512)}
            
            process_frame(frame, db, class_id=1, respect_skip=False)
            process_frame(frame, db, class_id=1, respect_skip=False)
            
            mock_log_att.assert_not_called()

            snapshot = get_tracker_hud_snapshot()
            self.assertEqual(snapshot["identity"], "Alice")
            self.assertIn("Alice", snapshot["display_text"])
            self.assertNotEqual(snapshot["display_text"], "SPOOF DETECTED")

    def test_process_frame_does_not_run_pad_for_review_candidate(self):
        from unittest.mock import patch, MagicMock
        import numpy as np
        from src.liveness import LivenessResult
        from src.recognize import (
            get_tracker_hud_snapshot,
            process_frame,
            reset_trackers,
            MatchDecision,
            LivenessGateDecision,
        )

        reset_trackers()

        fake_face = {"bbox": (10, 10, 90, 90), "embedding": np.ones(512), "landmarks": np.zeros((5, 2))}
        mock_face_model = MagicMock()
        mock_face_model.get_faces.return_value = [fake_face]
        mock_gate = LivenessGateDecision(
            allowed=False,
            decision="REJECT_SPOOF",
            result=LivenessResult(0.1, "SPOOF", ["test_spoof"], {}),
            short_reason="test_spoof",
        )

        with patch('src.recognize.get_face_model', return_value=mock_face_model), \
             patch('src.recognize.evaluate_liveness_gate', return_value=mock_gate) as mock_gate_fn, \
             patch('src.recognize.classify_match', return_value=MatchDecision("NEED_REVIEW", 0.60, "low_confidence")), \
             patch('src.recognize.log_attendance', return_value=(True, "PRESENT")) as mock_log_att, \
             patch('src.recognize.get_attended_today_for_class', return_value=set()):

            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            db = {"Alice": np.ones(512)}

            process_frame(frame, db, class_id=1, respect_skip=False)

            mock_gate_fn.assert_not_called()
            mock_log_att.assert_not_called()
            snapshot = get_tracker_hud_snapshot()
            self.assertEqual(snapshot["identity"], "Alice")
            self.assertIn("REVIEW Alice", snapshot["display_text"])


if __name__ == "__main__":
    unittest.main()
