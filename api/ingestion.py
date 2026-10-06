from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from api.models import AnalysisRecord, ImportCheckpoint, SensorReading
from config.settings import OUTPUT_DIR, PROCESSED_DIR

logger = logging.getLogger("aerythion.ingestion")

CSV_SOURCES = {
    "dataset": (PROCESSED_DIR / "air_quality_clean.csv", ";"),
    "regression": (OUTPUT_DIR / "regression_predictions.csv", ","),
    "anomalies": (OUTPUT_DIR / "anomaly_detection_results.csv", ","),
    "clustering": (OUTPUT_DIR / "clustering_results.csv", ","),
    "gradient_boosting": (OUTPUT_DIR / "gradient_boosting_predictions.csv", ","),
    "dbscan": (OUTPUT_DIR / "dbscan_results.csv", ","),
}


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _observed_at(payload: dict) -> datetime | None:
    value = payload.get("timestamp")
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed.to_pydatetime()


def _fingerprint(model: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(f"{model}:{canonical}".encode("utf-8")).hexdigest()


def seed_analysis_records(session_factory: sessionmaker[Session]) -> int:
    inserted = 0
    with session_factory() as session:
        for model, (path, separator) in CSV_SOURCES.items():
            if not path.is_file():
                logger.info("seed_source_unavailable", extra={"path": str(path), "model": model})
                continue

            source_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            checkpoint = session.get(ImportCheckpoint, model)
            if checkpoint is not None and checkpoint.source_digest == source_digest:
                continue
            if checkpoint is not None:
                session.execute(
                    delete(AnalysisRecord).where(AnalysisRecord.model == model)
                )
                session.flush()

            frame = pd.read_csv(path, sep=separator)
            for start in range(0, len(frame), 500):
                records = []
                for row in frame.iloc[start : start + 500].to_dict(orient="records"):
                    payload = {key: _json_value(value) for key, value in row.items()}
                    records.append(
                        AnalysisRecord(
                            model=model,
                            fingerprint=_fingerprint(model, payload),
                            observed_at=_observed_at(payload),
                            payload=payload,
                        )
                    )

                fingerprints = [record.fingerprint for record in records]
                existing = set(
                    session.scalars(
                        select(AnalysisRecord.fingerprint).where(
                            AnalysisRecord.fingerprint.in_(fingerprints)
                        )
                    )
                )
                pending = []
                for record in records:
                    if record.fingerprint not in existing:
                        pending.append(record)
                        existing.add(record.fingerprint)
                session.add_all(pending)
                inserted += len(pending)
                session.flush()
            if checkpoint is None:
                checkpoint = ImportCheckpoint(model=model, source_digest=source_digest)
                session.add(checkpoint)
            else:
                checkpoint.source_digest = source_digest
        session.commit()

    logger.info("analysis_records_seeded", extra={"inserted": inserted})
    return inserted


def dashboard_snapshot(session_factory: sessionmaker[Session]) -> dict:
    with session_factory() as session:
        models = ("dataset", "regression", "anomalies", "clustering", "gradient_boosting", "dbscan")
        counts = {model: 0 for model in models}
        for model, count in session.execute(
            select(AnalysisRecord.model, func.count())
            .where(AnalysisRecord.model.in_(models))
            .group_by(AnalysisRecord.model)
        ):
            counts[model] = int(count)
        recent_readings = session.scalars(
            select(AnalysisRecord)
            .where(AnalysisRecord.model == "dataset")
            .order_by(AnalysisRecord.observed_at.desc(), AnalysisRecord.id.desc())
            .limit(120)
        ).all()
        live_readings = session.scalars(
            select(AnalysisRecord)
            .where(AnalysisRecord.model == "regression")
            .order_by(AnalysisRecord.observed_at.desc(), AnalysisRecord.id.desc())
            .limit(120)
        ).all()
        sensor_readings = session.scalars(
            select(SensorReading)
            .order_by(SensorReading.observed_at.desc(), SensorReading.id.desc())
            .limit(120)
        ).all()

        anomaly_count = int(
            session.scalar(
                select(func.count())
                .select_from(AnalysisRecord)
                .where(
                    AnalysisRecord.model == "anomalies",
                    AnalysisRecord.payload["anomaly"].as_integer() == -1,
                )
            )
            or 0
        )

        chart_readings = [
            {"timestamp": item.observed_at.isoformat() if item.observed_at else None, **item.payload}
            for item in reversed(recent_readings)
        ]
        chart_predictions = [
            {"timestamp": item.observed_at.isoformat() if item.observed_at else None, **item.payload}
            for item in reversed(live_readings)
        ]
        live = [
            {
                "sensor_id": item.sensor_id,
                "timestamp": item.observed_at.isoformat(),
                "source_type": item.source_type,
                "source_timestamp": (
                    item.source_timestamp.isoformat() if item.source_timestamp else None
                ),
                "values": item.values,
            }
            for item in reversed(sensor_readings)
        ]
        return {
            "counts": counts,
            "anomalies_detected": anomaly_count,
            "readings": chart_readings,
            "predictions": chart_predictions,
            "live_readings": live,
            "updated_at": datetime.now().astimezone().isoformat(),
        }
