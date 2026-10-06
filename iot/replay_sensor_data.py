"""Replay processed historical UCI readings through the sensor ingestion API."""

from __future__ import annotations

import json
import logging
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pandas as pd

SENSOR_COLUMNS = (
    "CO_GT",
    "NO2_GT",
    "NOx_GT",
    "PT08_S1_CO",
    "PT08_S2_NMHC",
    "PT08_S3_NOx",
    "T",
    "RH",
    "AH",
)
DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "data" / "processed" / "air_quality_clean.csv"
LOGGER = logging.getLogger("air_quality.replay")


def replay_payload(row: dict, sensor_id: str) -> dict:
    values = {}
    for column in SENSOR_COLUMNS:
        value = pd.to_numeric(row.get(column), errors="coerce")
        if pd.notna(value) and math.isfinite(float(value)):
            values[column] = float(value)
    if not values:
        raise ValueError("The row does not contain any valid numeric readings")

    source_timestamp = pd.to_datetime(row.get("timestamp"), errors="coerce", utc=True)
    if pd.isna(source_timestamp):
        original_timestamp = None
    else:
        original_timestamp = source_timestamp.isoformat()

    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_type": "historical_replay",
        "source_timestamp": original_timestamp,
        "values": values,
    }


def load_readings(dataset_path: Path) -> Iterator[dict]:
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Processed dataset not found: {dataset_path}")
    frame = pd.read_csv(dataset_path, sep=";")
    required = {"timestamp", *SENSOR_COLUMNS}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"Processed dataset is missing required columns: {', '.join(sorted(missing))}"
        )
    for row in frame.to_dict(orient="records"):
        yield row


def publish_reading(api_url: str, payload: dict) -> None:
    body = json.dumps(payload, allow_nan=False).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 201:
                raise RuntimeError(f"API returned HTTP {response.status}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API rejected a reading (HTTP {error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not connect to the ingestion API: {error.reason}") from error


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"level":"%(levelname)s","message":"%(message)s"}',
    )
    api_url = os.getenv("SENSOR_API_URL", "http://127.0.0.1:8000/api/v1/readings")
    sensor_id = os.getenv("SENSOR_ID", "uci-historical-replay")
    interval = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "2"))
    if not math.isfinite(interval) or interval < 0.25:
        raise ValueError("SIMULATOR_INTERVAL_SECONDS must be at least 0.25")
    dataset_path = Path(os.getenv("SENSOR_DATASET_PATH", str(DEFAULT_DATASET)))

    rows = list(load_readings(dataset_path))
    if not rows:
        raise ValueError(f"Dataset contains no readings: {dataset_path}")
    LOGGER.info(
        "Historical replay active: %s rows, interval %.2f s, sensor %s",
        len(rows),
        interval,
        sensor_id,
    )

    index = 0
    while True:
        payload = replay_payload(rows[index], sensor_id)
        publish_reading(api_url, payload)
        LOGGER.info(
            "Reading %s/%s published; original timestamp %s",
            index + 1,
            len(rows),
            payload["source_timestamp"],
        )
        index = (index + 1) % len(rows)
        time.sleep(interval)


if __name__ == "__main__":
    main()
