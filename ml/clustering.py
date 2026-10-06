"""
clustering.py
-------------
Clustering de patrones ambientales urbanos mediante K-Means.

"""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from config.settings import OUTPUT_DIR, PROCESSED_DIR
from ml.evaluation import summarize_clusters


def main():
    # Load the preprocessed dataset
    csv_path = PROCESSED_DIR / "air_quality_clustering.csv"
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

    # Cluster with K-Means
    kmeans = KMeans(
        n_clusters=3,
        random_state=42,
        n_init=10
    )

    df["cluster"] = kmeans.fit_predict(X_scaled)

    # Evaluate the clustering results
    cluster_summary = summarize_clusters(df)

    print("Cluster distribution")
    for cluster, count in cluster_summary.items():
        print(f"Cluster {cluster}: {count} samples")
    # Save results
    output_df = df[["timestamp", "cluster"] + feature_columns]

    output_df.to_csv(
        OUTPUT_DIR / "clustering_results.csv",
        index=False
    )

    print("K-Means clustering complete")
    print(f"Results saved to {OUTPUT_DIR / 'clustering_results.csv'}")


if __name__ == "__main__":
    main()
