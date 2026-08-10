"""
Package step of the YOLO MLOps pipeline.

Exports the trained weights to ONNX and assembles everything the
"deploy" and GitHub Release steps need into one output directory.
Also tags the MLflow run with the release id and logs the final
bundle, so the MLflow record links straight to what got shipped.
"""
import argparse
import json
import os
import shutil
from pathlib import Path

import mlflow
from ultralytics import YOLO

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "file:./mlruns")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=str, required=True)
    parser.add_argument("--metrics", type=str, required=True)
    parser.add_argument("--run-id", type=str, required=True,
                         help="GitHub Actions run id, used for the release tag / image tag")
    parser.add_argument("--mlflow-run-id-file", type=str, default="runs/train/mlflow_run_id.txt")
    parser.add_argument("--output-dir", type=str, default="dist")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy raw weights (kept as a Release asset for reproducibility / re-fine-tuning)
    shutil.copy(args.weights, out_dir / "model.pt")

    # Export to ONNX for portable inference (used by the Docker image too)
    model = YOLO(args.weights)
    onnx_path = model.export(format="onnx")
    shutil.copy(onnx_path, out_dir / "model.onnx")

    # Carry metrics through
    metrics = json.loads(Path(args.metrics).read_text())
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    # Release notes for the GitHub Release body
    notes = f"""# YOLO model {args.run_id}

    | Metric | Value |
    |---|---|
    | mAP50 | {metrics['map50']:.4f} |
    | mAP50-95 | {metrics['map50_95']:.4f} |
    | Precision | {metrics['precision']:.4f} |
    | Recall | {metrics['recall']:.4f} |

    Docker image: `ghcr.io/OWNER/smart-forest-yolo:{args.run_id}`
    """
    (out_dir / "RELEASE_NOTES.md").write_text(notes.replace("    ", ""))

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow_run_id = Path(args.mlflow_run_id_file).read_text().strip()
    with mlflow.start_run(run_id=mlflow_run_id):
        mlflow.set_tag("release_tag", f"yolo-{args.run_id}")
        mlflow.set_tag("ghcr_image", f"ghcr.io/OWNER/smart-forest-yolo:{args.run_id}")
        mlflow.log_artifact(str(out_dir / "model.onnx"), artifact_path="packaged")

    print(f"Packaged bundle in {out_dir}/: model.pt, model.onnx, metrics.json, RELEASE_NOTES.md")


if __name__ == "__main__":
    main()
