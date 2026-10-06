"""Additional environmental prediction and clustering models."""

import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from config.settings import OUTPUT_DIR, PROCESSED_DIR, ensure_project_directories

FEATURE_COLUMNS = [
    "NO2_GT",
    "NOx_GT",
    "PT08_S1_CO",
    "PT08_S2_NMHC",
    "PT08_S3_NOx",
    "T",
    "RH",
    "AH",
]
CLUSTER_COLUMNS = ["CO_GT", *FEATURE_COLUMNS]


def run_gradient_boosting() -> None:
    source = PROCESSED_DIR / "air_quality_clean.csv"
    if not source.is_file():
        raise FileNotFoundError(f"Processed dataset does not exist: {source}")

    frame = pd.read_csv(source, sep=";").dropna(subset=["CO_GT", *FEATURE_COLUMNS])
    if len(frame) < 5:
        raise ValueError("At least 5 valid rows are required to train Gradient Boosting")

    X_train, X_test, y_train, y_test = train_test_split(
        frame[FEATURE_COLUMNS], frame["CO_GT"], test_size=0.2, shuffle=False
    )
    model = HistGradientBoostingRegressor(
        learning_rate=0.08, max_iter=150, max_leaf_nodes=20, random_state=42
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    metrics = {
        "RMSE": float(root_mean_squared_error(y_test, predictions)),
        "MAE": float(mean_absolute_error(y_test, predictions)),
    }
    print("Gradient Boosting evaluation")
    for name, value in metrics.items():
        print(f"{name}: {value:.4f}")

    results = pd.DataFrame(
        {
            "timestamp": frame.iloc[len(X_train) :]["timestamp"].to_numpy(),
            "real_CO": y_test.to_numpy(),
            "predicted_CO": predictions,
        }
    )
    results.to_csv(OUTPUT_DIR / "gradient_boosting_predictions.csv", index=False)


def run_dbscan() -> None:
    source = PROCESSED_DIR / "air_quality_clustering.csv"
    if not source.is_file():
        raise FileNotFoundError(f"Clustering dataset does not exist: {source}")

    frame = pd.read_csv(source, sep=";").dropna(subset=CLUSTER_COLUMNS)
    if len(frame) < 2:
        raise ValueError("At least 2 valid rows are required to run DBSCAN")

    scaled = StandardScaler().fit_transform(frame[CLUSTER_COLUMNS])
    labels = DBSCAN(eps=1.5, min_samples=10, n_jobs=-1).fit_predict(scaled)
    frame["cluster"] = labels
    frame["is_noise"] = labels == -1

    noise_count = int((labels == -1).sum())
    cluster_count = len(set(labels) - {-1})
    print(f"DBSCAN: {cluster_count} clusters, {noise_count} noise/anomalous readings.")
    frame[["timestamp", "cluster", "is_noise", *CLUSTER_COLUMNS]].to_csv(
        OUTPUT_DIR / "dbscan_results.csv", index=False
    )


def main() -> None:
    ensure_project_directories()
    run_gradient_boosting()
    run_dbscan()


if __name__ == "__main__":
    main()
