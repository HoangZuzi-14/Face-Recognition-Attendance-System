import unittest


class RecognitionPolicyTests(unittest.TestCase):
    def test_classifies_match_accept_need_review_and_unknown(self):
        from src.recognize import classify_match

        self.assertEqual(classify_match(0.30, 0.12).status, "ACCEPT")
        self.assertEqual(classify_match(0.38, 0.12).status, "NEED_REVIEW")
        self.assertEqual(classify_match(0.30, 0.01).status, "NEED_REVIEW")
        self.assertEqual(classify_match(0.50, 0.12).status, "UNKNOWN")

    def test_confidence_score_is_bounded(self):
        from src.recognize import confidence_from_distance

        self.assertEqual(confidence_from_distance(-1), 1.0)
        self.assertEqual(confidence_from_distance(2), 0.0)
        self.assertEqual(confidence_from_distance(0.25), 0.75)


if __name__ == "__main__":
    unittest.main()
