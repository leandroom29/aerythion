"""
anomaly_detection.py
--------------------
Detección de anomalías en sensores ambientales urbanos
mediante el algoritmo Isolation Forest.

"""

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from ml.evaluation import summarize_anomalies


def main():
    # Cargar dataset preprocesado
    csv_path = "data/processed/air_quality_clean.csv"
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

    # Entrenamiento del modelo
    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )

    df["anomaly"] = model.fit_predict(X_scaled)
    #  1  -> normal
    # -1  -> anomalía

    # Evaluación desde archivo de evaluación
    summary = summarize_anomalies(df)

    print("Resumen de anomalías")
    for k, v in summary.items():
        print(f"{k}: {v}")

    # Guardar resultados
    output_df = df[["timestamp", "anomaly"] + feature_columns]

    output_df.to_csv(
        "data/output/anomaly_detection_results.csv",
        index=False
    )

    print("Detección de anomalías completada")
    print("Resultados guardados en data/output/anomaly_detection_results.csv")


if __name__ == "__main__":
    main()