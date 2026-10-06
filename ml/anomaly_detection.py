"""
anomaly_detection.py
--------------------
Anomaly detection for urban environmental sensors
using the Isolation Forest algorithm.

"""

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from config.settings import OUTPUT_DIR, PROCESSED_DIR
from ml.evaluation import summarize_anomalies


def main():
    # Load the preprocessed dataset
    csv_path = PROCESSED_DIR / "air_quality_clean.csv"
    df = pd.read_csv(csv_path, sep=";")

    # Select numeric features
    feature_columns = [
        "CO_GT",
        "NO2_GT",
        "NOx_GT",
        "PT08_S1_CO",
        "PT08_S2_NMHC",
        "PT08_S3_NOx",
        "T",
        "RH",
        "AH"
    ]

    X = df[feature_columns]

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train the model
    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )

    df["anomaly"] = model.fit_predict(X_scaled)
    #  1  -> normal
    # -1  -> anomaly

    # Evaluate the anomaly detection results
    summary = summarize_anomalies(df)

    print("Anomaly summary")
    for k, v in summary.items():
        print(f"{k}: {v}")

    # Save results
    output_df = df[["timestamp", "anomaly"] + feature_columns]

    output_df.to_csv(
        OUTPUT_DIR / "anomaly_detection_results.csv",
        index=False
    )

    print("Anomaly detection complete")
    print(f"Results saved to {OUTPUT_DIR / 'anomaly_detection_results.csv'}")


if __name__ == "__main__":
    main()