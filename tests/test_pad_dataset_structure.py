import csv
import unittest
from pathlib import Path


class PadDatasetStructureTests(unittest.TestCase):
    def test_pad_dataset_skeleton_exists_with_metadata_header(self):
        dataset_root = Path("datasets/pad")

        self.assertTrue((dataset_root / "genuine").is_dir())
        self.assertTrue((dataset_root / "print_attack").is_dir())
        self.assertTrue((dataset_root / "screen_attack").is_dir())
        self.assertTrue((dataset_root / "cutout_attack").is_dir())

        metadata_path = dataset_root / "metadata.csv"
        self.assertTrue(metadata_path.exists())
        with metadata_path.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))

        self.assertEqual(
            header,
            [
                "sample_id",
                "label",
                "attack_type",
                "subject_id",
                "device",
                "lighting",
                "note",
            ],
        )


if __name__ == "__main__":
    unittest.main()
