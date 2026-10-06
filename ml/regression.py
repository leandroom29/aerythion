"""
regression.py
-------------
Regression model for predicting pollution levels.

"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from ml.evaluation import evaluate_regression
from config.settings import OUTPUT_DIR, PROCESSED_DIR


def main():
    # Load the preprocessed dataset
    csv_path = PROCESSED_DIR / "air_quality_clean.csv"
    df = pd.read_csv(csv_path, sep=";")

    # Define the target variable
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

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled,
        y,
        test_size=0.2,
        shuffle=False
    )

    # Train the model
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # Generate predictions
    y_pred = model.predict(X_test)

    # Evaluate the predictions
    metrics = evaluate_regression(y_test, y_pred)

    print("Regression model evaluation")
    for name, value in metrics.items():
        print(f"{name}: {value:.4f}")

    # Calculate model metrics
    rmse = root_mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("Regression model results")
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"R²:   {r2:.4f}")

    # Save results
    results = pd.DataFrame({
        "timestamp": df.loc[y_test.index, "timestamp"],
        "real_CO": y_test.values,
        "predicted_CO": y_pred
    })

    results.to_csv(
        OUTPUT_DIR / "regression_predictions.csv",
        index=False
    )

    print(f"Predictions saved to {OUTPUT_DIR / 'regression_predictions.csv'}")


if __name__ == "__main__":
    main()