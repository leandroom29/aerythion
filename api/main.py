from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError

from api.database import configured_database_url, create_session_factory
from api.ingestion import dashboard_snapshot, seed_analysis_records
from api.models import AnalysisRecord, Base, SensorReading
from api.observability import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS,
    SENSOR_READINGS,
    configure_logging,
)
from api.schemas import SensorReadingInput
from config.settings import RAW_DATA_PATH

logger = configure_logging()
DASHBOARD_FILE = Path(__file__).resolve().parent / "dashboard.html"


def create_app(
    database_url: str | None = None,
    *,
    seed_files: bool = True,
    initialize_schema: bool = True,
    replay_retention_limit: int = 1000,
) -> FastAPI:
    if replay_retention_limit < 1:
        raise ValueError("replay_retention_limit must be greater than zero")
    engine, session_factory = create_session_factory(database_url or configured_database_url())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            if initialize_schema:
                Base.metadata.create_all(engine)
                sensor_columns = {
                    column["name"] for column in inspect(engine).get_columns("sensor_readings")
                }
                migrations = {
                    "source_type": (
                        "ALTER TABLE sensor_readings "
                        "ADD COLUMN source_type VARCHAR(32) NOT NULL DEFAULT 'sensor'"
                    ),
                    "source_timestamp": (
                        "ALTER TABLE sensor_readings "
                        "ADD COLUMN source_timestamp TIMESTAMP WITH TIME ZONE"
                    ),
                }
                with engine.begin() as connection:
                    for column_name, statement in migrations.items():
                        if column_name not in sensor_columns:
                            connection.execute(text(statement))
                if seed_files:
                    await asyncio.to_thread(seed_analysis_records, session_factory)
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="Aerythion API",
        description="Urban analytics API with batch results and IoT sensor ingestion.",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory

    @app.middleware("http")
    async def request_observability(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)
            duration = time.perf_counter() - started
            HTTP_REQUESTS.labels(request.method, route_path, str(status)).inc()
            HTTP_REQUEST_DURATION.labels(request.method, route_path).observe(duration)
            logger.info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": route_path,
                    "status_code": status,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

    @app.get("/", include_in_schema=False)
    def home():
        return {
            "name": "Aerythion",
            "status": "ok",
            "dashboard": "/dashboard",
            "docs": "/docs",
            "endpoints": [
                "/health",
                "/api/v1/dashboard",
                "/api/v1/data",
                "/api/v1/regression",
                "/api/v1/gradient-boosting",
                "/api/v1/clustering",
                "/api/v1/dbscan",
                "/api/v1/anomalies",
                "/api/v1/readings",
                "/api/v1/events",
                "/metrics",
            ],
        }

    @app.get("/health")
    def health():
        try:
            with session_factory() as session:
                session.execute(text("SELECT 1"))
                dataset_count = session.scalar(
                    select(func.count())
                    .select_from(AnalysisRecord)
                    .where(AnalysisRecord.model == "dataset")
                )
            return {
                "status": "ok",
                "database": "connected",
                "dataset_exists": RAW_DATA_PATH.is_file(),
                "processed_dataset_exists": bool(dataset_count),
            }
        except SQLAlchemyError as exc:
            logger.exception("database_health_check_failed")
            raise HTTPException(status_code=503, detail="Database unavailable") from exc

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception):
        logger.exception(
            "unhandled_api_error",
            extra={"path": request.url.path, "method": request.method},
            exc_info=error,
        )
        return Response(
            content='{"detail":"Internal server error"}',
            status_code=500,
            media_type="application/json",
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, error: RequestValidationError
    ):
        errors = [
            {
                "location": list(item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": errors},
        )

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/dashboard", include_in_schema=False)
    def dashboard():
        return FileResponse(DASHBOARD_FILE)

    @app.get("/api/v1/dashboard")
    def dashboard_data():
        return dashboard_snapshot(session_factory)

    def get_analysis_results(
        model: str,
        limit: int = Query(default=100, ge=1, le=10000),
        offset: int = Query(default=0, ge=0),
    ):
        model_aliases = {
            "data": "dataset",
            "regression": "regression",
            "clustering": "clustering",
            "anomalies": "anomalies",
            "gradient-boosting": "gradient_boosting",
            "dbscan": "dbscan",
        }
        model_name = model_aliases.get(model)
        if model_name is None:
            raise HTTPException(status_code=404, detail="Unknown analysis result")
        with session_factory() as session:
            records = session.scalars(
                select(AnalysisRecord)
                .where(AnalysisRecord.model == model_name)
                .order_by(AnalysisRecord.observed_at, AnalysisRecord.id)
                .offset(offset)
                .limit(limit)
            ).all()
            total = session.scalar(
                select(func.count()).select_from(AnalysisRecord).where(
                    AnalysisRecord.model == model_name
                )
            )
        return {
            "items": [
                {
                    "timestamp": record.observed_at.isoformat() if record.observed_at else None,
                    **record.payload,
                }
                for record in records
            ],
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/data", include_in_schema=False)
    def legacy_data(limit: int = Query(default=10000, ge=1, le=10000)):
        return get_analysis_results("data", limit, 0)["items"]

    @app.get("/regression", include_in_schema=False)
    def legacy_regression(limit: int = Query(default=10000, ge=1, le=10000)):
        return get_analysis_results("regression", limit, 0)["items"]

    @app.get("/clustering", include_in_schema=False)
    def legacy_clustering(limit: int = Query(default=10000, ge=1, le=10000)):
        return get_analysis_results("clustering", limit, 0)["items"]

    @app.get("/anomalies", include_in_schema=False)
    def legacy_anomalies(limit: int = Query(default=10000, ge=1, le=10000)):
        return get_analysis_results("anomalies", limit, 0)["items"]

    @app.get("/summary", include_in_schema=False)
    def legacy_summary():
        with session_factory() as session:
            dataset_count = session.scalar(
                select(func.count())
                .select_from(AnalysisRecord)
                .where(AnalysisRecord.model == "dataset")
            )
            output_counts = {
                "regression_predictions": int(
                    session.scalar(
                        select(func.count()).select_from(AnalysisRecord).where(
                            AnalysisRecord.model == "regression"
                        )
                    )
                    or 0
                ),
                "anomaly_detection_results": int(
                    session.scalar(
                        select(func.count()).select_from(AnalysisRecord).where(
                            AnalysisRecord.model == "anomalies"
                        )
                    )
                    or 0
                ),
                "clustering_results": int(
                    session.scalar(
                        select(func.count()).select_from(AnalysisRecord).where(
                            AnalysisRecord.model == "clustering"
                        )
                    )
                    or 0
                ),
            }
        return {
            "raw_dataset_exists": RAW_DATA_PATH.is_file(),
            "processed_dataset_exists": bool(dataset_count),
            "output_files": {name: count > 0 for name, count in output_counts.items()},
        }

    @app.post("/api/v1/readings", status_code=201)
    def ingest_reading(reading: SensorReadingInput):
        record = SensorReading(
            sensor_id=reading.sensor_id,
            observed_at=reading.observed_at(),
            source_type=reading.source_type,
            source_timestamp=reading.source_observed_at(),
            values=reading.values,
        )
        with session_factory() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            result = {
                "id": record.id,
                "sensor_id": record.sensor_id,
                "timestamp": record.observed_at.isoformat(),
                "source_type": record.source_type,
                "source_timestamp": (
                    record.source_timestamp.isoformat() if record.source_timestamp else None
                ),
                "values": record.values,
            }
            if record.source_type == "historical_replay":
                overflow_ids = (
                    select(SensorReading.id)
                    .where(
                        SensorReading.sensor_id == record.sensor_id,
                        SensorReading.source_type == "historical_replay",
                    )
                    .order_by(SensorReading.observed_at.desc(), SensorReading.id.desc())
                    .offset(replay_retention_limit)
                )
                session.execute(delete(SensorReading).where(SensorReading.id.in_(overflow_ids)))
                session.commit()
        SENSOR_READINGS.inc()
        logger.info("sensor_reading_ingested", extra={"sensor_id": reading.sensor_id})
        return result

    @app.get("/api/v1/readings")
    def get_readings(limit: int = Query(default=100, ge=1, le=10000)):
        with session_factory() as session:
            records = session.scalars(
                select(SensorReading)
                .order_by(SensorReading.observed_at.desc(), SensorReading.id.desc())
                .limit(limit)
            ).all()
        return [
            {
                "id": record.id,
                "sensor_id": record.sensor_id,
                "timestamp": record.observed_at.isoformat(),
                "source_type": record.source_type,
                "source_timestamp": (
                    record.source_timestamp.isoformat() if record.source_timestamp else None
                ),
                "values": record.values,
            }
            for record in records
        ]

    @app.get("/api/v1/events")
    async def dashboard_events(request: Request):
        async def event_stream():
            while not await request.is_disconnected():
                snapshot = await asyncio.to_thread(dashboard_snapshot, session_factory)
                yield f"event: dashboard\ndata: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
                await asyncio.sleep(5)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    app.get("/api/v1/{model}")(get_analysis_results)

    return app


app = create_app()
