"""Evaluate recognition thresholds with FAR, FRR, EER, and ROC output."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def cosine_score(vec1, vec2):
    a = np.asarray(vec1, dtype=np.float32)
    b = np.asarray(vec2, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return 0.0
    return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))


def compute_far_frr(scores, labels, threshold):
    scores = [float(score) for score in scores]
    labels = [str(label).strip().lower() for label in labels]
    genuine = [(s, l) for s, l in zip(scores, labels) if l == "genuine"]
    impostor = [(s, l) for s, l in zip(scores, labels) if l == "impostor"]
    false_rejects = sum(1 for score, _ in genuine if score < threshold)
    false_accepts = sum(1 for score, _ in impostor if score >= threshold)
    frr = false_rejects / len(genuine) if genuine else 0.0
    far = false_accepts / len(impostor) if impostor else 0.0
    return {
        "threshold": float(threshold),
        "FAR": round(far, 6),
        "FRR": round(frr, 6),
        "genuine_pairs": len(genuine),
        "impostor_pairs": len(impostor),
    }


def threshold_sweep(scores, labels):
    candidates = sorted({0.0, 1.0, *[float(score) for score in scores]})
    return [compute_far_frr(scores, labels, threshold) for threshold in candidates]


def compute_eer(scores, labels):
    sweep = threshold_sweep(scores, labels)
    best = min(sweep, key=lambda row: abs(row["FAR"] - row["FRR"]))
    eer = (best["FAR"] + best["FRR"]) / 2.0
    return {
        "EER": round(eer, 6),
        "recommended_threshold": best["threshold"],
        "FAR_at_EER": best["FAR"],
        "FRR_at_EER": best["FRR"],
        "sweep": sweep,
    }


def load_score_csv(path):
    scores = []
    labels = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = str(row.get("label", "")).strip().lower()
            if not label:
                continue
            if row.get("score") not in (None, ""):
                score = float(row["score"])
            elif row.get("left_embedding") and row.get("right_embedding"):
                left = np.load(row["left_embedding"])
                right = np.load(row["right_embedding"])
                score = cosine_score(left, right)
            else:
                raise ValueError("CSV row needs score or left_embedding/right_embedding")
            scores.append(score)
            labels.append(label)
    return scores, labels


def _write_report(path, result):
    path.write_text(
        "\n".join(
            [
                "# Recognition Threshold Report",
                "",
                f"- Pairs: {result['pairs']}",
                f"- EER: {result['EER']:.6f}",
                f"- Recommended threshold: {result['recommended_threshold']:.6f}",
                f"- FAR at EER: {result['FAR_at_EER']:.6f}",
                f"- FRR at EER: {result['FRR_at_EER']:.6f}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_curves(reports_dir, sweep):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    thresholds = [row["threshold"] for row in sweep]
    fars = [row["FAR"] for row in sweep]
    frrs = [row["FRR"] for row in sweep]
    tprs = [1.0 - value for value in frrs]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fars, tprs, marker="o")
    ax.set_xlabel("FAR")
    ax.set_ylabel("TAR")
    ax.set_title("ROC Curve")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(Path(reports_dir) / "roc_curve.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fars, frrs, marker="o")
    ax.set_xlabel("FAR")
    ax.set_ylabel("FRR")
    ax.set_title("DET Curve")
    ax.grid(True, alpha=0.3)
    for threshold, far, frr in zip(thresholds, fars, frrs):
        ax.annotate(f"{threshold:.2f}", (far, frr), fontsize=7)
    fig.tight_layout()
    fig.savefig(Path(reports_dir) / "det_curve.png")
    plt.close(fig)


def evaluate_score_csv(score_csv, reports_dir="reports"):
    scores, labels = load_score_csv(score_csv)
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    eer = compute_eer(scores, labels)
    result = {
        "pairs": len(scores),
        **{key: value for key, value in eer.items() if key != "sweep"},
    }
    _write_report(reports_dir / "recognition_threshold_report.md", result)
    (reports_dir / "recognition_threshold_metrics.json").write_text(
        json.dumps({**result, "sweep": eer["sweep"]}, indent=2),
        encoding="utf-8",
    )
    _write_curves(reports_dir, eer["sweep"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate recognition thresholds.")
    parser.add_argument("--scores", required=True, help="CSV with score,label columns.")
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args(argv)

    result = evaluate_score_csv(args.scores, args.reports_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
