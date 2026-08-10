"""
Train step of the YOLO MLOps pipeline.

Uses Ultralytics YOLO26 + the D-Fire dataset (fire/smoke detection,
https://github.com/gaia-solutions-on-demand/DFireDataset). D-Fire ships
YOLO-format labels already, so fetch_dataset() just needs to get the
repo's train/test folders onto disk -- no reformatting required.

`dataset_version` maps to a git ref (tag/branch/commit) of that repo,
so re-running with a pinned ref gives reproducible training data.
"""
import argparse
import os
import subprocess
from pathlib import Path

import mlflow
from ultralytics import YOLO

DFIRE_REPO = "https://github.com/gaia-solutions-on-demand/DFireDataset.git"

# Defaults to a local file-based store (e.g. in GitHub Actions, where the
# mlruns/ folder travels between jobs as an artifact). Set MLFLOW_TRACKING_URI
# to point at a real server instead -- e.g. the one in docker-compose.mlops.yml --
# for live cross-run history you can browse in the MLflow UI.
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "file:./mlruns")
MLFLOW_EXPERIMENT = "yolo26-dfire"


def fetch_dataset(dataset_version: str) -> str:
    """
    Clone (or reuse a cached checkout of) D-Fire at the given git ref and
    return the path to the Ultralytics data.yaml that points at it.
    """
    data_dir = Path("yolo/data/D-Fire")
    if not data_dir.exists():
        ref = "" if dataset_version in ("latest", "", None) else f"--branch {dataset_version}"
        subprocess.run(
            f"git clone --depth 1 {ref} {DFIRE_REPO} {data_dir}",
            shell=True, check=True,
        )
    else:
        print(f"Reusing existing dataset checkout at {data_dir}")

    data_yaml = Path("yolo/data/data.yaml")
    if not data_yaml.exists():
        raise FileNotFoundError(
            f"Expected dataset config at {data_yaml}. "
            "See yolo/data/data.yaml for the expected D-Fire layout."
        )
    return str(data_yaml)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--dataset-version", type=str, default="latest")
    parser.add_argument("--base-model", type=str, default="yolo26n.pt",
                         help="Starting weights: yolo26n/s/m/l/x.pt, or a path to previous best.pt for fine-tuning")
    parser.add_argument("--output-dir", type=str, default="runs/train")
    args = parser.parse_args()

    data_yaml = fetch_dataset(args.dataset_version)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    with mlflow.start_run() as run:
        mlflow.log_params({
            "base_model": args.base_model,
            "epochs": args.epochs,
            "dataset_version": args.dataset_version,
            "dataset": "D-Fire",
        })

        model = YOLO(args.base_model)
        results = model.train(
            data=data_yaml,
            epochs=args.epochs,
            project=args.output_dir,
            name="exp",
            exist_ok=True,
        )

        # Ultralytics' own results_dict has the final-epoch training/val metrics
        if hasattr(results, "results_dict"):
            numeric_metrics = {
                k: v for k, v in results.results_dict.items()
                if isinstance(v, (int, float))
            }
            mlflow.log_metrics(numeric_metrics)

        # Ultralytics writes weights to {output_dir}/exp/weights/{best,last}.pt.
        # The workflow expects runs/train/weights/best.pt, so normalize the path.
        exp_weights = Path(args.output_dir) / "exp" / "weights" / "best.pt"
        flat_weights_dir = Path(args.output_dir) / "weights"
        flat_weights_dir.mkdir(parents=True, exist_ok=True)
        (flat_weights_dir / "best.pt").write_bytes(exp_weights.read_bytes())

        mlflow.log_artifact(str(flat_weights_dir / "best.pt"), artifact_path="weights")

        # Later jobs (eval, package) run on fresh checkouts/runners, so they
        # can't inherit this run_id in-process -- write it to disk instead,
        # to travel alongside the mlruns/ folder as a workflow artifact.
        run_id_file = Path(args.output_dir) / "mlflow_run_id.txt"
        run_id_file.write_text(run.info.run_id)

    print(f"Training complete. Weights at {flat_weights_dir / 'best.pt'}")
    print(f"MLflow run: {run.info.run_id}")


if __name__ == "__main__":
    main()
