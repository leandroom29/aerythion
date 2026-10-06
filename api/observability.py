from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from prometheus_client import Counter, Histogram


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "sensor_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> logging.Logger:
    root = logging.getLogger()
    if not any(getattr(handler, "_air_quality_json", False) for handler in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._air_quality_json = True
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    return logging.getLogger("aerythion")


HTTP_REQUESTS = Counter(
    "air_quality_http_requests_total",
    "Total HTTP requests served by the API",
    ("method", "path", "status"),
)
HTTP_REQUEST_DURATION = Histogram(
    "air_quality_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "path"),
)
SENSOR_READINGS = Counter(
    "air_quality_sensor_readings_total",
    "Number of sensor readings accepted by the ingestion API",
)
