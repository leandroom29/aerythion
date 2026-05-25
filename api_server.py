from flask import Flask, jsonify
import pandas as pd

app = Flask(__name__)

# ENDPOINTS

@app.route("/")
def home():
    return "API en funcionamiento"


@app.route("/data")
def get_data():
    df = pd.read_csv("data/processed/air_quality_clean.csv", sep=";")
    return jsonify(df.to_dict(orient="records"))


@app.route("/regression")
def get_regression():
    df = pd.read_csv("data/output/regression_predictions.csv")
    return jsonify(df.to_dict(orient="records"))


@app.route("/clustering")
def get_clustering():
    df = pd.read_csv("data/output/clustering_results.csv")
    return jsonify(df.to_dict(orient="records"))


@app.route("/anomalies")
def get_anomalies():
    df = pd.read_csv("data/output/anomaly_detection_results.csv")
    return jsonify(df.to_dict(orient="records"))


# EJECUCIÓN
def run_api():
    app.run(debug=True, use_reloader=False)