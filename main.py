import argparse

import uvicorn

from config.settings import ensure_project_directories, OUTPUT_DIR, PROJECT_CONFIG
from ml.anomaly_detection import main as run_anomaly_detection
from ml.clustering import main as run_clustering
from ml.extra_models import main as run_extra_models
from ml.regression import main as run_regression
from spark.spark_analysis import main as run_spark_analysis
from spark.spark_clustering_prep import main as run_clustering_prep


REQUIRED_OUTPUTS = [
    OUTPUT_DIR / "regression_predictions.csv",
    OUTPUT_DIR / "anomaly_detection_results.csv",
    OUTPUT_DIR / "clustering_results.csv",
    OUTPUT_DIR / "gradient_boosting_predictions.csv",
    OUTPUT_DIR / "dbscan_results.csv",
]


def check_outputs(allow_missing: bool = False) -> None:
    """Check that pipeline outputs exist before serving the API."""
    missing = [str(path) for path in REQUIRED_OUTPUTS if not path.exists()]
    if missing:
        if allow_missing:
            print("Skipping output validation because ML execution was requested to be skipped.")
            return
        raise FileNotFoundError(
            "Missing pipeline outputs: " + ", ".join(missing)
        )
    print("All output files are present.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Air quality analysis pipeline")
    parser.add_argument("--skip-spark", action="store_true", help="Skip exploratory analysis with Spark")
    parser.add_argument("--skip-clustering-prep", action="store_true", help="Skip clustering dataset preparation")
    parser.add_argument("--skip-ml", action="store_true", help="Skip the machine-learning models")
    parser.add_argument("--skip-api", action="store_true", help="Do not start the API when the pipeline finishes")
    parser.add_argument("--host", default=PROJECT_CONFIG["api"]["host"], help="FastAPI server host")
    parser.add_argument("--port", type=int, default=PROJECT_CONFIG["api"]["port"], help="FastAPI server port")
    return parser


def run_pipeline(args: argparse.Namespace) -> None:
    ensure_project_directories()
    print("=== AERYTHION PIPELINE ===")
    print("Initial setup complete.")

    if not args.skip_spark:
        print("Loading dataset and running exploratory analysis with Spark...")
        run_spark_analysis()
        print("Spark exploratory analysis complete.")

    if not args.skip_clustering_prep:
        print("Preparing the clustering dataset...")
        run_clustering_prep()
        print("Clustering dataset prepared.")

    if not args.skip_ml:
        print("Running the machine-learning pipeline...")
        print("============================================")
        print("Running regression model...")
        print("============================================")
        run_regression()
        print("Regression complete.")

        print("============================================")
        print("Running anomaly detection model...")
        print("============================================")
        run_anomaly_detection()
        print("Anomaly detection complete.")

        print("============================================")
        print("Running clustering model on the preprocessed dataset...")
        print("============================================")
        run_clustering()
        print("Clustering complete.")

        print("Running additional models (Gradient Boosting and DBSCAN)...")
        run_extra_models()
        print("Additional models complete.")

    check_outputs(allow_missing=args.skip_ml)
    print("Pipeline completed successfully.")

    if not args.skip_api:
        print("Starting the FastAPI service and dashboard...")
        print(f"Dashboard: http://{args.host}:{args.port}/dashboard")
        print(f"API docs:  http://{args.host}:{args.port}/docs")
        uvicorn.run("api.main:app", host=args.host, port=args.port, reload=False)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        run_pipeline(args)
    except Exception as exc:  # pragma: no cover - keep the pipeline output readable
        print("\nPIPELINE ERROR:")
        print(exc)
        raise


if __name__ == "__main__":
    main()