import pytest
import pandas as pd
from fastapi.testclient import TestClient

import api.ingestion as ingestion
from api.database import configured_database_url
from api.main import create_app
from api.database import create_session_factory
from api.models import Base
from iot.replay_sensor_data import replay_payload
from ml.extra_models import main as run_extra_models


@pytest.fixture
def client():
    app = create_app(database_url="sqlite:///:memory:", seed_files=False)
    with TestClient(app) as test_client:
        yield test_client


def test_health_checks_database(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"


def test_sensor_readings_are_validated_and_persisted(client):
    response = client.post(
        "/api/v1/readings",
        json={
            "sensor_id": "sensor-01",
            "timestamp": "2026-10-05T12:00:00Z",
            "values": {"CO_GT": 1.25, "T": 18.5},
        },
    )

    assert response.status_code == 201
    assert response.json()["sensor_id"] == "sensor-01"
    assert response.json()["values"]["CO_GT"] == 1.25
    readings = client.get("/api/v1/readings").json()
    assert len(readings) == 1
    assert readings[0]["sensor_id"] == "sensor-01"


def test_historical_readings_are_marked_as_a_replay(client):
    response = client.post(
        "/api/v1/readings",
        json={
            "sensor_id": "uci-historical-replay",
            "source_type": "historical_replay",
            "source_timestamp": "2004-03-10T18:00:00Z",
            "values": {"CO_GT": 0.3},
        },
    )

    assert response.status_code == 201
    assert response.json()["source_type"] == "historical_replay"
    assert response.json()["source_timestamp"].startswith("2004-03-10")
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["live_readings"][0]["source_type"] == "historical_replay"


def test_historical_replay_keeps_only_the_latest_configured_rows():
    app = create_app(
        database_url="sqlite:///:memory:",
        seed_files=False,
        replay_retention_limit=2,
    )
    with TestClient(app) as client:
        for value in (1.0, 2.0, 3.0):
            response = client.post(
                "/api/v1/readings",
                json={
                    "sensor_id": "uci-historical-replay",
                    "source_type": "historical_replay",
                    "values": {"CO_GT": value},
                },
            )
            assert response.status_code == 201

        readings = client.get("/api/v1/readings?limit=10").json()
        assert [item["values"]["CO_GT"] for item in readings] == [3.0, 2.0]


def test_replay_payload_preserves_the_original_timestamp_and_measurements():
    payload = replay_payload(
        {
            "timestamp": "2004-03-10 18:00:00",
            "CO_GT": 0.35,
            "T": -0.47,
            "AH": 0.58,
        },
        "uci-historical-replay",
    )

    assert payload["source_type"] == "historical_replay"
    assert payload["source_timestamp"].startswith("2004-03-10T18:00:00")
    assert payload["values"] == {"CO_GT": 0.35, "T": -0.47, "AH": 0.58}
    assert payload["timestamp"] != payload["source_timestamp"]


def test_sensor_reading_rejects_infinite_values(client):
    response = client.post(
        "/api/v1/readings",
        content=b'{"sensor_id":"sensor-01","values":{"CO_GT":1e999}}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422


def test_dashboard_and_metrics_are_available(client):
    assert "Aerythion" in client.get("/dashboard").text

    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["counts"]["dataset"] == 0

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "air_quality_http_requests_total" in metrics.text


def test_legacy_routes_keep_the_list_response_shape(client):
    response = client.get("/regression")

    assert response.status_code == 200
    assert response.json() == []


def test_unknown_analysis_name_returns_not_found(client):
    response = client.get("/api/v1/not-a-model")

    assert response.status_code == 404


def test_database_url_escapes_credentials(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_USER", "air quality")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss/word")

    url = configured_database_url()

    assert url.username == "air quality"
    assert url.password == "p@ss/word"


def test_csv_seeding_is_idempotent_and_handles_duplicate_rows(tmp_path, monkeypatch):
    source = tmp_path / "records.csv"
    anomalies_source = tmp_path / "anomalies.csv"
    pd.DataFrame(
        [
            {"timestamp": "2026-10-05T12:00:00Z", "CO_GT": 1.0},
            {"timestamp": "2026-10-05T12:00:00Z", "CO_GT": 1.0},
        ]
    ).to_csv(source, sep=";", index=False)
    pd.DataFrame([{"timestamp": "2026-10-05T12:00:00Z", "anomaly": -1}]).to_csv(
        anomalies_source, index=False
    )
    monkeypatch.setattr(
        ingestion,
        "CSV_SOURCES",
        {"dataset": (source, ";"), "anomalies": (anomalies_source, ",")},
    )
    engine, session_factory = create_session_factory("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    assert ingestion.seed_analysis_records(session_factory) == 2
    assert ingestion.seed_analysis_records(session_factory) == 0
    assert ingestion.dashboard_snapshot(session_factory)["counts"]["dataset"] == 1
    assert ingestion.dashboard_snapshot(session_factory)["anomalies_detected"] == 1

    pd.DataFrame([{"timestamp": "2026-10-05T12:00:00Z", "CO_GT": 2.0}]).to_csv(
        source, sep=";", index=False
    )
    assert ingestion.seed_analysis_records(session_factory) == 1
    snapshot = ingestion.dashboard_snapshot(session_factory)
    assert snapshot["counts"]["dataset"] == 1
    assert snapshot["anomalies_detected"] == 1

    engine.dispose()


def test_api_imports_real_project_outputs_into_sqlite():
    app = create_app(database_url="sqlite:///:memory:")
    with TestClient(app) as client:
        assert client.get("/health").json()["processed_dataset_exists"] is True
        assert client.get("/summary").json()["output_files"]["regression_predictions"] is True
        assert client.get("/data?limit=1").status_code == 200
        assert len(client.get("/data?limit=1").json()) == 1
        assert len(client.get("/regression?limit=1").json()) == 1
        dashboard = client.get("/api/v1/dashboard").json()
        assert dashboard["counts"]["dataset"] > 0
        assert dashboard["counts"]["regression"] > 0


def test_additional_models_write_predictions_and_dbscan_labels(tmp_path, monkeypatch):
    processed = tmp_path / "processed"
    output = tmp_path / "output"
    processed.mkdir()
    output.mkdir()
    monkeypatch.setattr("ml.extra_models.PROCESSED_DIR", processed)
    monkeypatch.setattr("ml.extra_models.OUTPUT_DIR", output)

    rows = []
    for index in range(80):
        row = {
            "timestamp": f"2026-01-{index % 28 + 1:02d}T00:00:00",
            "CO_GT": float(index / 20),
            "NO2_GT": float(index % 10),
            "NOx_GT": float(index % 14),
            "PT08_S1_CO": float(800 + index),
            "PT08_S2_NMHC": float(700 + index * 2),
            "PT08_S3_NOx": float(500 + index * 3),
            "T": float(10 + index / 10),
            "RH": float(35 + index % 20),
            "AH": float(0.5 + index / 1000),
        }
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame.to_csv(processed / "air_quality_clean.csv", sep=";", index=False)
    frame.to_csv(processed / "air_quality_clustering.csv", sep=";", index=False)

    run_extra_models()

    predictions = pd.read_csv(output / "gradient_boosting_predictions.csv")
    clusters = pd.read_csv(output / "dbscan_results.csv")
    assert len(predictions) == 16
    assert {"cluster", "is_noise"}.issubset(clusters.columns)
