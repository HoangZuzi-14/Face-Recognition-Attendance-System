import csv
import tempfile
import unittest
from pathlib import Path


class EvaluateRecognitionThresholdTests(unittest.TestCase):
    def test_compute_far_frr_and_eer_from_scores(self):
        from scripts.evaluate_recognition_threshold import (
            compute_eer,
            compute_far_frr,
        )

        scores = [0.95, 0.88, 0.20, 0.10]
        labels = ["genuine", "genuine", "impostor", "impostor"]

        metrics = compute_far_frr(scores, labels, threshold=0.5)
        eer = compute_eer(scores, labels)

        self.assertEqual(metrics["FAR"], 0.0)
        self.assertEqual(metrics["FRR"], 0.0)
        self.assertGreaterEqual(eer["EER"], 0.0)
        self.assertLessEqual(eer["EER"], 1.0)
        self.assertGreaterEqual(eer["recommended_threshold"], 0.0)
        self.assertLessEqual(eer["recommended_threshold"], 1.0)

    def test_evaluate_score_csv_writes_report_and_roc_curve(self):
        from scripts.evaluate_recognition_threshold import evaluate_score_csv

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            score_csv = tmp_path / "scores.csv"
            reports = tmp_path / "reports"
            with score_csv.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["score", "label"])
                writer.writerow([0.96, "genuine"])
                writer.writerow([0.86, "genuine"])
                writer.writerow([0.30, "impostor"])
                writer.writerow([0.12, "impostor"])

            result = evaluate_score_csv(score_csv, reports_dir=reports)

            self.assertEqual(result["pairs"], 4)
            self.assertIn("EER", result)
            self.assertTrue((reports / "recognition_threshold_report.md").exists())
            self.assertTrue((reports / "roc_curve.png").exists())


if __name__ == "__main__":
    unittest.main()
