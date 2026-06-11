import unittest


class FusionDecisionTests(unittest.TestCase):
    def test_rejects_unknown_when_recognition_does_not_match(self):
        from src.fusion import DECISION_REJECT_UNKNOWN, fuse_decision

        result = fuse_decision(
            recognition_score=0.40,
            recognition_matched=False,
            liveness_score=1.0,
            pad_score=1.0,
        )

        self.assertEqual(result.decision, DECISION_REJECT_UNKNOWN)
        self.assertIn("recognition_no_match", result.reasons)

    def test_rejects_spoof_when_liveness_fails_after_match(self):
        from src.fusion import DECISION_REJECT_SPOOF, fuse_decision

        result = fuse_decision(
            recognition_score=0.90,
            recognition_matched=True,
            liveness_score=0.20,
            pad_score=0.90,
        )

        self.assertEqual(result.decision, DECISION_REJECT_SPOOF)
        self.assertIn("liveness_low_score", result.reasons)

    def test_requires_challenge_when_passive_pad_is_suspicious(self):
        from src.fusion import DECISION_CHALLENGE_REQUIRED, fuse_decision

        result = fuse_decision(
            recognition_score=0.92,
            recognition_matched=True,
            liveness_score=0.82,
            pad_score=0.55,
            rppg_confidence=0.40,
        )

        self.assertEqual(result.decision, DECISION_CHALLENGE_REQUIRED)
        self.assertIn("pad_suspicious", result.reasons)

    def test_accepts_clear_live_match(self):
        from src.fusion import DECISION_ACCEPT, fuse_decision

        result = fuse_decision(
            recognition_score=0.96,
            recognition_matched=True,
            liveness_score=0.93,
            pad_score=0.91,
            rppg_confidence=0.45,
            quality_score=0.88,
        )

        self.assertEqual(result.decision, DECISION_ACCEPT)
        self.assertIn("live_clear", result.reasons)

    def test_failed_challenge_rejects_spoof(self):
        from src.fusion import DECISION_REJECT_SPOOF, fuse_decision

        result = fuse_decision(
            recognition_score=0.95,
            recognition_matched=True,
            liveness_score=0.90,
            pad_score=0.52,
            challenge_result="failed",
        )

        self.assertEqual(result.decision, DECISION_REJECT_SPOOF)
        self.assertIn("challenge_failed", result.reasons)


if __name__ == "__main__":
    unittest.main()
