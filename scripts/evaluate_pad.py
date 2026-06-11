"""Evaluate PAD/liveness dataset with APCER, BPCER, and ACER metrics."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image

from src.liveness import LIVENESS_LIVE, assess_liveness


METADATA_COLUMNS = [
    "sample_id",
    "label",
    "attack_type",
    "subject_id",
    "device",
    "lighting",
    "note",
]


def load_metadata(dataset_root):
    metadata_path = Path(dataset_root) / "metadata.csv"
    if not metadata_path.exists():
        raise FileNotFoundError(f"PAD metadata not found: {metadata_path}")
    with metadata_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [column for column in METADATA_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"metadata.csv missing columns: {', '.join(missing)}")
        return [dict(row) for row in reader if row.get("sample_id")]


def resolve_sample_path(dataset_root, row):
    dataset_root = Path(dataset_root)
    sample_id = row["sample_id"]
    direct = dataset_root / sample_id
    if direct.exists():
        return direct

    folder = "genuine" if row.get("label") == "genuine" else row.get("attack_type")
    if not folder:
        raise FileNotFoundError(f"Cannot resolve folder for sample: {sample_id}")
    candidate = dataset_root / folder / sample_id
    if candidate.exists():
        return candidate
    stem_matches = list((dataset_root / folder).glob(f"{Path(sample_id).stem}.*"))
    if stem_matches:
        return stem_matches[0]
    raise FileNotFoundError(f"PAD sample not found: {sample_id}")


def load_image_rgb(path):
    with Image.open(path) as image:
        return np.array(image.convert("RGB"))


def predict_label(result, threshold):
    if str(result.label).upper() == LIVENESS_LIVE and float(result.score) >= threshold:
        return "genuine"
    return "spoof"


def compute_pad_metrics(records):
    confusion = {
        "genuine": {"genuine": 0, "spoof": 0},
        "spoof": {"genuine": 0, "spoof": 0},
    }
    for record in records:
        label = "genuine" if record["label"] == "genuine" else "spoof"
        prediction = "genuine" if record["prediction"] == "genuine" else "spoof"
        confusion[label][prediction] += 1

    attacks = confusion["spoof"]["genuine"] + confusion["spoof"]["spoof"]
    bona_fide = confusion["genuine"]["genuine"] + confusion["genuine"]["spoof"]
    apcer = confusion["spoof"]["genuine"] / attacks if attacks else 0.0
    bpcer = confusion["genuine"]["spoof"] / bona_fide if bona_fide else 0.0
    acer = (apcer + bpcer) / 2.0
    return {
        "samples": len(records),
        "APCER": round(apcer, 6),
        "BPCER": round(bpcer, 6),
        "ACER": round(acer, 6),
        "confusion_matrix": confusion,
    }


def _write_json(path, metrics, records):
    payload = dict(metrics)
    payload["records"] = records
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_markdown(path, metrics):
    cm = metrics["confusion_matrix"]
    path.write_text(
        "\n".join(
            [
                "# PAD Evaluation Metrics",
                "",
                f"- Samples: {metrics['samples']}",
                f"- APCER: {metrics['APCER']:.6f}",
                f"- BPCER: {metrics['BPCER']:.6f}",
                f"- ACER: {metrics['ACER']:.6f}",
                "",
                "## Confusion Matrix",
                "",
                "| Actual | Predicted Genuine | Predicted Spoof |",
                "| --- | ---: | ---: |",
                f"| genuine | {cm['genuine']['genuine']} | {cm['genuine']['spoof']} |",
                f"| spoof | {cm['spoof']['genuine']} | {cm['spoof']['spoof']} |",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_confusion_png(path, confusion):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matrix = np.array(
        [
            [confusion["genuine"]["genuine"], confusion["genuine"]["spoof"]],
            [confusion["spoof"]["genuine"], confusion["spoof"]["spoof"]],
        ]
    )
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], ["genuine", "spoof"])
    ax.set_yticks([0, 1], ["genuine", "spoof"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(matrix[i, j]), ha="center", va="center")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def evaluate_dataset(
    dataset_root="datasets/pad",
    reports_dir="reports",
    threshold=0.70,
    assessor=assess_liveness,
):
    dataset_root = Path(dataset_root)
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for row in load_metadata(dataset_root):
        image_path = resolve_sample_path(dataset_root, row)
        frame = load_image_rgb(image_path)
        h, w = frame.shape[:2]
        result = assessor(frame, face_bbox=(0, 0, w, h), pad_threshold=threshold)
        records.append(
            {
                "sample_id": row["sample_id"],
                "label": "genuine" if row["label"] == "genuine" else "spoof",
                "attack_type": row.get("attack_type") or "",
                "prediction": predict_label(result, threshold),
                "score": float(result.score),
                "liveness_label": str(result.label),
                "reasons": list(result.reasons),
            }
        )

    metrics = compute_pad_metrics(records)
    _write_json(reports_dir / "pad_metrics.json", metrics, records)
    _write_markdown(reports_dir / "pad_metrics.md", metrics)
    _write_confusion_png(reports_dir / "confusion_matrix.png", metrics["confusion_matrix"])
    return metrics


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate PAD dataset metrics.")
    parser.add_argument("--dataset", default="datasets/pad")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--threshold", type=float, default=0.70)
    args = parser.parse_args(argv)

    metrics = evaluate_dataset(args.dataset, args.reports_dir, args.threshold)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
