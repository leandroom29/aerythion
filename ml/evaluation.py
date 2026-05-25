"""
evaluation.py
-------------
Módulo de evaluación de modelos de Machine Learning
para el proyecto.
"""

import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
    root_mean_squared_error
)

# Evaluación de REGRESIÓN

def evaluate_regression(y_true, y_pred) -> dict:
    """
    Calcula métricas estándar para modelos de regresión.

    """
    rmse = root_mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    return {
        "RMSE": rmse,
        "MAE": mae,
        "R2": r2
    }


# Evaluación de DETECCIÓN DE ANOMALÍAS

def summarize_anomalies(df: pd.DataFrame, column: str = "anomaly") -> dict:
    """
    Resume los resultados de la detección de anomalías.

    """
    total = len(df)
    anomalies = (df[column] == -1).sum()
    normal = (df[column] == 1).sum()

    return {
        "total_samples": total,
        "normal_points": int(normal),
        "anomalies_detected": int(anomalies),
        "anomaly_ratio": anomalies / total if total > 0 else 0
    }


# Evaluación de CLUSTERING

def summarize_clusters(df: pd.DataFrame, column: str = "cluster") -> dict:
    """
    Resume la distribución de clusters generados por K-Means.

    """
    return df[column].value_counts().sort_index().to_dict()