import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


class EvaluatePadTests(unittest.TestCase):
    def _write_sample(self, root, folder, sample_id, value):
        path = root / folder / sample_id
        path.parent.mkdir(parents=True, exist_ok=True)
        image = np.ones((16, 16, 3), dtype=np.uint8) * value
        Image.fromarray(image).save(path)

    def test_compute_pad_metrics_apcer_bpcer_acer(self):
        from scripts.evaluate_pad import compute_pad_metrics

        records = [
            {"label": "genuine", "prediction": "genuine"},
            {"label": "genuine", "prediction": "spoof"},
            {"label": "spoof", "prediction": "spoof"},
            {"label": "spoof", "prediction": "genuine"},
        ]

        metrics = compute_pad_metrics(records)

        self.assertEqual(metrics["confusion_matrix"]["genuine"]["genuine"], 1)
        self.assertEqual(metrics["confusion_matrix"]["genuine"]["spoof"], 1)
        self.assertEqual(metrics["confusion_matrix"]["spoof"]["spoof"], 1)
        self.assertEqual(metrics["confusion_matrix"]["spoof"]["genuine"], 1)
        self.assertEqual(metrics["APCER"], 0.5)
        self.assertEqual(metrics["BPCER"], 0.5)
        self.assertEqual(metrics["ACER"], 0.5)

    def test_evaluate_dataset_writes_reports_with_mock_assessor(self):
        from scripts.evaluate_pad import evaluate_dataset
        from src.liveness import LivenessResult

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset = tmp_path / "pad"
            reports = tmp_path / "reports"
            self._write_sample(dataset, "genuine", "genuine_1.png", 220)
            self._write_sample(dataset, "print_attack", "spoof_1.png", 40)
            with (dataset / "metadata.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "sample_id",
                    "label",
                    "attack_type",
                    "subject_id",
                    "device",
                    "lighting",
                    "note",
                ])
                writer.writerow(["genuine_1.png", "genuine", "", "S1", "webcam", "bright", ""])
                writer.writerow(["spoof_1.png", "spoof", "print_attack", "S1", "webcam", "bright", ""])

            def assessor(frame, face_bbox=None, **kwargs):
                score = float(frame.mean() / 255.0)
                label = "LIVE" if score > 0.5 else "SPOOF"
                return LivenessResult(score=score, label=label, reasons=[], details={})

            metrics = evaluate_dataset(dataset, reports_dir=reports, assessor=assessor)

            self.assertEqual(metrics["samples"], 2)
            self.assertEqual(metrics["ACER"], 0.0)
            self.assertTrue((reports / "pad_metrics.json").exists())
            self.assertTrue((reports / "pad_metrics.md").exists())
            self.assertTrue((reports / "confusion_matrix.png").exists())
            loaded = json.loads((reports / "pad_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded["ACER"], 0.0)


if __name__ == "__main__":
    unittest.main()
