"""
regression.py
-------------
Modelo de regresión para la predicción de niveles de contaminación.

"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from ml.evaluation import evaluate_regression


def main():
    # Cargar dataset preprocesado
    csv_path = "data/processed/air_quality_clean.csv"
    df = pd.read_csv(csv_path, sep=";")

    # Definir variable objetivo
    target_column = "CO_GT"

    feature_columns = [
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
    y = df[target_column]

    # Escalado de variables
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # División train / test
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled,
        y,
        test_size=0.2,
        shuffle=False
    )

    # Entrenamiento del modelo
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # Predicción
    y_pred = model.predict(X_test)

    # Evaluación desde archivo de evaluacion
    metrics = evaluate_regression(y_test, y_pred)

    print("Evaluación del modelo de regresión")
    for name, value in metrics.items():
        print(f"{name}: {value:.4f}")

    # Evaluación del modelo
    rmse = root_mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("Resultados del modelo de regresión")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"R²:   {r2:.4f}")

    # Guardar resultados
    results = pd.DataFrame({
        "timestamp": df.loc[y_test.index, "timestamp"],
        "real_CO": y_test.values,
        "predicted_CO": y_pred
    })

    results.to_csv(
        "data/output/regression_predictions.csv",
        index=False
    )

    print("Predicciones guardadas en data/output/regression_predictions.csv")


if __name__ == "__main__":
    main()