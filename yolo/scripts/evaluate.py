"""
Eval step of the YOLO MLOps pipeline.

Runs validation on the trained weights and enforces a minimum mAP50
"quality gate": if the model doesn't meet the bar, this script exits
non-zero and the whole workflow stops (no package/deploy of a worse model).

Resumes the MLflow run started in train.py (via the run_id file that
travels alongside the mlruns/ folder as a workflow artifact) so eval
metrics land on the same run as training params/metrics.
"""
import argparse
import json
import sys
from pathlib import Path

import mlflow
from ultralytics import YOLO

MLFLOW_TRACKING_URI = "file:./mlruns"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=str, required=True)
    parser.add_argument("--min-map50", type=float, default=0.5)
    parser.add_argument("--metrics-out", type=str, default="runs/eval/metrics.json")
    parser.add_argument("--run-id-file", type=str, default="runs/train/mlflow_run_id.txt")
    args = parser.parse_args()

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    run_id = Path(args.run_id_file).read_text().strip()

    model = YOLO(args.weights)
    results = model.val()

    metrics = {
        "map50": float(results.box.map50),
        "map50_95": float(results.box.map),
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
    }

    out_path = Path(args.metrics_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, indent=2))

    with mlflow.start_run(run_id=run_id):
        mlflow.log_metrics({f"eval_{k}": v for k, v in metrics.items()})
        mlflow.log_artifact(str(out_path), artifact_path="eval")

    print(f"Metrics: {metrics}")

    if metrics["map50"] < args.min_map50:
        print(
            f"FAILED quality gate: mAP50 {metrics['map50']:.4f} "
            f"< required {args.min_map50:.4f}"
        )
        sys.exit(1)

    print(f"Passed quality gate: mAP50 {metrics['map50']:.4f} >= {args.min_map50:.4f}")


if __name__ == "__main__":
    main()
