"""
clustering.py
-------------
Clustering de patrones ambientales urbanos mediante K-Means.

"""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from ml.evaluation import summarize_clusters


def main():
    # Cargar dataset preprocesado
    csv_path = "data/processed/air_quality_clustering.csv"
    df = pd.read_csv(csv_path, sep=";")

    # Selección de variables numéricas
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

    # Escalado de variables
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Clustering con K-Means
    kmeans = KMeans(
        n_clusters=3,
        random_state=42,
        n_init=10
    )

    df["cluster"] = kmeans.fit_predict(X_scaled)

    # Evaluación desde archivo de evaluación
    cluster_summary = summarize_clusters(df)

    print("Distribución de clusters")
    for cluster, count in cluster_summary.items():
        print(f"Cluster {cluster}: {count} muestras")
    # Guardar resultados
    output_df = df[["timestamp", "cluster"] + feature_columns]

    output_df.to_csv(
        "data/output/clustering_results.csv",
        index=False
    )

    print("Clustering completado con K-Means")
    print("Resultados guardados en data/output/clustering_results.csv")


if __name__ == "__main__":
    main()
