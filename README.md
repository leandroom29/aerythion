# Aerythion

An academic urban air-quality analytics platform. The project combines an Apache Spark batch pipeline, scikit-learn models, a FastAPI service, PostgreSQL persistence, IoT reading ingestion, and a web dashboard that updates through Server-Sent Events (SSE).

## Quick start

With Docker Desktop running, start the API and PostgreSQL from the repository root:

```powershell
docker compose up --build -d
```

To also replay historical readings through the ingestion API:

```powershell
docker compose --profile demo up --build -d simulator
```

Open the [dashboard](http://localhost:8000/dashboard), explore the API in [Swagger UI](http://localhost:8000/docs), or check the API/database status at [health](http://localhost:8000/health).

> **Important:** The optional simulator replays historical rows from the UCI dataset. It does not measure current air quality and does not connect to a physical sensor. The dashboard labels replayed readings accordingly and preserves their original timestamps. Processed CSV values are normalized and must not be interpreted as physical concentrations.

## Contents

- [Capabilities](#capabilities)
- [Architecture and data flow](#architecture-and-data-flow)
- [Repository layout](#repository-layout)
- [Data and preprocessing](#data-and-preprocessing)
- [Machine-learning models](#machine-learning-models)
- [Requirements](#requirements)
- [Local installation and execution](#local-installation-and-execution)
- [Docker Compose deployment](#docker-compose-deployment)
- [Historical IoT replay](#historical-iot-replay)
- [REST API](#rest-api)
- [Database and CSV imports](#database-and-csv-imports)
- [Dashboard and live updates](#dashboard-and-live-updates)
- [Logging and metrics](#logging-and-metrics)
- [Tests](#tests)
- [Configuration and security](#configuration-and-security)
- [Known limitations and future work](#known-limitations-and-future-work)
- [Troubleshooting](#troubleshooting)
- [License and data provenance](#license-and-data-provenance)

## Capabilities

- Exploratory analysis and clustering-data preparation with Apache Spark.
- Batch regression, clustering, and anomaly detection using scikit-learn.
- Versioned FastAPI endpoints with an OpenAPI schema and compatibility routes.
- IoT readings ingestion through `POST /api/v1/readings`.
- PostgreSQL storage for IoT readings and imported batch results.
- Responsive dashboard with recent activity, normalized CO plots, and SSE updates.
- Optional replay of the historical UCI dataset at configurable intervals.
- Structured JSON logs, request IDs, and Prometheus metrics.
- Separate Docker images for the API, Spark/ML batch pipeline, and simulator.

## Architecture and data flow

```text
                         BATCH LAYER
Air Quality UCI ──> Spark ──> processed datasets
                                  │
                                  v
                     scikit-learn / ML models
                                  │
                                  v
                           output CSV files
                                  │
                                  │ idempotent import at API startup
                                  v
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI + PostgreSQL                         │
│                                                                  │
│  REST queries ─────> persisted analytical results                │
│  REST ingestion ───> persisted IoT readings                      │
│  /api/v1/events ───> SSE snapshots ───> web dashboard            │
│  /metrics ─────────> Prometheus                                   │
└──────────────────────────────────────────────────────────────────┘
           ^                                      │
           │ POST /api/v1/readings                │ SSE, every 5 s
     sensor/gateway                         web browser
           ^
           │
   optional simulator
   (historical UCI replay)
```

The pipeline reads and analyzes the source file, prepares data, runs models, and writes CSV results under `data/output/`. On startup, the API creates its database schema and imports available CSV files. Clients query results through REST, sensors submit readings through HTTP, and the dashboard receives periodic snapshots through SSE.

The implemented IoT transport uses HTTP and PostgreSQL. **This repository does not deploy Kafka, MQTT, Flume, HDFS, Spark Streaming, or physical measurement hardware.**

## Repository layout

```text
.
├── api/
│   ├── dashboard.html        Web dashboard and SSE client
│   ├── database.py           SQLAlchemy connection/session factories
│   ├── ingestion.py          CSV import and dashboard snapshots
│   ├── main.py               FastAPI application, routes, and lifecycle
│   ├── models.py             SQLAlchemy tables
│   ├── observability.py      JSON logging and Prometheus metrics
│   └── schemas.py            IoT reading validation
├── config/
│   ├── config.yaml           API host, port, and data paths
│   └── settings.py           Centralized configuration and paths
├── data/
│   ├── raw/                  Source dataset
│   ├── processed/            Clean and clustering-ready datasets
│   └── output/               Batch-model CSV results
├── iot/
│   └── replay_sensor_data.py Historical reading replay client
├── ml/
│   ├── anomaly_detection.py  Isolation Forest
│   ├── clustering.py         K-Means
│   ├── evaluation.py         Metrics and summaries
│   ├── extra_models.py       HistGradientBoosting and DBSCAN
│   └── regression.py         Random Forest
├── spark/
│   ├── spark_analysis.py        Source dataset exploratory analysis
│   ├── spark_clustering_prep.py Clustering dataset preparation
│   └── spark_session.py         Local Spark session
├── tests/
│   └── test_api.py           API, database, replay, and integration tests
├── api_server.py             Uvicorn compatibility entry point
├── main.py                   CLI and pipeline orchestration
├── Dockerfile                FastAPI service image
├── Dockerfile.pipeline       Spark/Java batch image
├── Dockerfile.simulator      IoT replay image
├── compose.yaml              API, PostgreSQL, and optional profiles
├── requirements.txt          Full development dependencies
├── requirements-api.txt      API dependencies
└── requirements-pipeline.txt Spark/ML dependencies
```

## Data and preprocessing

The application expects the Air Quality UCI dataset and uses configured paths from `config/config.yaml`. The default paths are:

- Source: `data/raw/AirQualityUCI.csv`
- Processed data: `data/processed/air_quality_clean.csv`
- Clustering-ready data: `data/processed/air_quality_clustering.csv`
- Model outputs: `data/output/`

The preprocessing artifacts use semicolon-delimited CSV. Model output CSV files are comma-delimited. The project refers to columns such as `CO_GT`, `NO2_GT`, `NOx_GT`, `PT08_S1_CO`, `PT08_S2_NMHC`, `PT08_S3_NOx`, `T`, `RH`, and `AH`. These names are kept unchanged because they are part of the data and API contracts.

The processed values may be standardized or otherwise transformed. Do not label them as ppm, µg/m³, or other physical units unless the original transformations have been correctly reversed and the units verified.

## Machine-learning models

| Model | Purpose | Output |
|---|---|---|
| Random Forest Regressor | Predict `CO_GT` from the selected sensor and environmental features | `regression_predictions.csv` |
| Isolation Forest | Flag normal (`1`) and anomalous (`-1`) observations | `anomaly_detection_results.csv` |
| K-Means | Segment observations into three clusters | `clustering_results.csv` |
| HistGradientBoostingRegressor | Additional `CO_GT` regression model | `gradient_boosting_predictions.csv` |
| DBSCAN | Density-based grouping and noise detection | `dbscan_results.csv` |

The regression pipeline reports RMSE, MAE, and R². Clustering and anomaly detection produce summaries in the command output. `ml/evaluation.py` contains shared evaluation helpers.

## Requirements

### Local development

- Python 3.12 or newer (the Docker images use Python 3.12).
- Java 17 or newer for local PySpark execution.
- PostgreSQL 15 or newer for the API.
- Docker Desktop with Docker Compose v2 is an alternative to installing Java and PostgreSQL locally.

Python 3.14 may not be supported by every dependency used by the Spark stack. For a predictable local setup, use Python 3.12.

## Local installation and execution

### 1. Create and activate a virtual environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents environment activation, invoke `.\.venv\Scripts\python.exe` directly in the following commands.

### 2. Install dependencies

Install the complete stack, including Spark and test dependencies:

```powershell
python -m pip install -r requirements.txt
```

For API-only development:

```powershell
python -m pip install -r requirements-api.txt
```

### 3. Start PostgreSQL

The API requires PostgreSQL when running locally. One option is to start only the database with Compose:

```powershell
docker compose up -d db
docker compose ps
```

The default development Compose settings are host `localhost`, port `5432`, database `air_quality`, and user `air_quality`. The default development password is `air_quality_dev`; replace it outside a local environment.

To configure a local API connection with an explicit URL:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://air_quality:your_password@localhost:5432/air_quality"
```

Alternatively, configure `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

### 4. Run the full pipeline and API

```powershell
python main.py
```

The pipeline runs in this order:

1. Exploratory analysis of the source CSV with Spark.
2. Spark preparation of the clustering CSV.
3. Random Forest regression and metrics.
4. Isolation Forest anomaly detection.
5. K-Means clustering.
6. Additional Gradient Boosting prediction.
7. DBSCAN clustering.
8. Output validation and FastAPI/Uvicorn startup.

The API listens at `http://127.0.0.1:8000` by default. Check `/health` before using the dashboard.

### CLI options

```powershell
python main.py --help
```

| Option | Effect |
|---|---|
| `--skip-spark` | Skip analysis of the source CSV |
| `--skip-clustering-prep` | Do not rebuild the clustering CSV |
| `--skip-ml` | Skip all machine-learning models |
| `--skip-api` | Finish after the requested pipeline steps without starting Uvicorn |
| `--host HOST` | Set the Uvicorn host, for example `0.0.0.0` |
| `--port PORT` | Set the Uvicorn port, for example `8080` |

To rerun models using existing processed CSV files without starting the API:

```powershell
python main.py --skip-spark --skip-clustering-prep --skip-api
```

To run only the API locally after starting PostgreSQL:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

At startup, the API imports available result CSV files and logs which sources are imported or missing.

## Docker Compose deployment

Compose provides separate database and API services. The `batch` profile adds Spark/Java; the `demo` profile adds the optional replay simulator.

### Start the API and PostgreSQL

```powershell
Copy-Item .env.example .env
notepad .env
```

Set a local `POSTGRES_PASSWORD` in `.env`, then run:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

The API waits for PostgreSQL to pass its health check. HTTP is published on port `8000`; PostgreSQL is available only on the Compose network by default. The `postgres_data` volume preserves the database when containers are recreated.

Local URLs:

- Dashboard: <http://localhost:8000/dashboard>
- Swagger/OpenAPI UI: <http://localhost:8000/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>
- API and database health: <http://localhost:8000/health>
- Prometheus metrics: <http://localhost:8000/metrics>

### Run the batch pipeline in Docker

The batch image contains Python, Java, and PySpark. The project data directory is mounted so generated outputs remain in the repository:

```powershell
docker compose --profile batch run --build --rm batch
```

The default command runs `python main.py --skip-api`. Restart the API after generating new CSVs so they are imported:

```powershell
docker compose restart api
```

To run batch without Spark, clustering preparation, or API startup:

```powershell
docker compose --profile batch run --build --rm batch --skip-spark --skip-clustering-prep --skip-api
```

### Common Compose commands

```powershell
docker compose ps
docker compose logs --tail 100 api
docker compose logs --tail 100 db

# Stop services while preserving PostgreSQL data
docker compose down

# Start again using the existing database volume
docker compose up -d
```

> `docker compose down -v` deletes the persistent PostgreSQL volume and its data. It is not needed for a normal restart.

## Historical IoT replay

The optional simulator reads `data/processed/air_quality_clean.csv` in order. By default it sends one row to the HTTP ingestion endpoint every two seconds and starts again from the beginning after reaching the end.

Start the API and PostgreSQL, then enable the demo profile:

```powershell
docker compose --profile demo up --build -d simulator
docker compose ps
docker compose logs -f simulator
```

The dashboard displays a **Demo mode** notice when replay readings are present. Each reading uses `source_type = historical_replay`, the current receipt time in `timestamp`, and the dataset observation time in `source_timestamp`. The API retains at most 1,000 most recent replay readings per sensor.

### Configure the replay interval and sensor ID

```powershell
$env:SIMULATOR_INTERVAL_SECONDS = "1"
$env:SIMULATED_SENSOR_ID = "uci-replay-01"
docker compose --profile demo up -d --force-recreate simulator
```

The minimum interval is 0.25 seconds. Faster intervals create more frequent database writes. Stop the simulator while leaving the API available:

```powershell
docker compose stop simulator
```

To stop the demo profile and then leave the normal API and database running:

```powershell
docker compose --profile demo down
docker compose up -d
```

### Replay semantics and limitations

- The simulator does **not** create new measurements; it resends observations from the historical UCI dataset.
- The current timestamp represents receipt time. The original observation timestamp is retained separately.
- Cleaned CSV values are transformed/normalized and must not be reported as physical units without reversing and validating the transformations.
- The simulator does not add random noise. Changes come from advancing through dataset rows.
- Replay is useful for testing ingestion, persistence, charts, reconnection, and continuous display. It does not validate current air quality.

## REST API

FastAPI publishes an OpenAPI schema at `/openapi.json` and interactive documentation at `/docs`. Result endpoints support bounded `limit` and `offset` pagination.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Service name, primary endpoints, and useful links |
| `GET` | `/health` | API/database status and source/processed dataset availability |
| `GET` | `/summary` | Dataset and batch-result availability (compatibility route) |
| `GET` | `/dashboard` | Web dashboard |
| `GET` | `/api/v1/dashboard` | Snapshot of counts, series, and recent readings |
| `GET` | `/api/v1/events` | SSE dashboard snapshots every five seconds |
| `POST` | `/api/v1/readings` | Validate and persist an IoT reading |
| `GET` | `/api/v1/readings?limit=100` | Recent sensor readings, up to 10,000 |
| `GET` | `/api/v1/data?limit=100&offset=0` | Processed dataset records |
| `GET` | `/api/v1/regression?limit=100&offset=0` | Random Forest predictions |
| `GET` | `/api/v1/gradient-boosting?limit=100&offset=0` | Gradient Boosting predictions |
| `GET` | `/api/v1/anomalies?limit=100&offset=0` | Isolation Forest results |
| `GET` | `/api/v1/clustering?limit=100&offset=0` | K-Means results |
| `GET` | `/api/v1/dbscan?limit=100&offset=0` | DBSCAN results |
| `GET` | `/metrics` | Prometheus metrics |

### Submit a sensor reading

```powershell
$reading = @{
  sensor_id = "sensor-01"
  timestamp = (Get-Date).ToUniversalTime().ToString("o")
  values = @{ CO_GT = 1.25; T = 18.5 }
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/v1/readings `
  -ContentType "application/json" `
  -Body $reading
```

Example request:

```json
{
  "sensor_id": "sensor-01",
  "timestamp": "2026-10-06T06:30:00Z",
  "values": {
    "CO_GT": 1.25,
    "T": 18.5
  }
}
```

Validation rules:

- `sensor_id` must be non-empty text of at most 120 characters.
- `timestamp` is an optional ISO 8601 date/time. If omitted, the service uses the UTC receipt time.
- `values` must contain 1–50 name/value pairs with finite numeric values.
- Unknown top-level fields are rejected.
- Simulator readings also include `source_type: "historical_replay"` and `source_timestamp`.
- Schema errors return HTTP `422`; accepted readings return HTTP `201`.

### Compatibility routes

The following unversioned routes are retained during migration:

| Legacy route | Recommended versioned route |
|---|---|
| `GET /data` | `GET /api/v1/data` |
| `GET /regression` | `GET /api/v1/regression` |
| `GET /clustering` | `GET /api/v1/clustering` |
| `GET /anomalies` | `GET /api/v1/anomalies` |
| `GET /summary` | `/api/v1/dashboard` for dashboard KPIs; `/summary` remains available |

Legacy routes return a direct JSON list. Versioned model routes include pagination metadata.

## Database and CSV imports

SQLAlchemy manages PostgreSQL connections and tables.

| Table | Purpose |
|---|---|
| `analysis_records` | Dataset rows and model results stored as JSON payloads |
| `sensor_readings` | Sensor readings and source metadata |
| `import_checkpoints` | Imported CSV fingerprints used to skip unchanged files |

At startup, the API creates missing tables, applies a small compatibility migration for reading-source columns, calculates a SHA-256 digest for each configured CSV, and skips imports whose digest is unchanged. If a CSV changes, its rows for that model are replaced with the new version.

Newly generated CSV files are not watched while the API is running. Restart the service (`docker compose restart api`) to import them. In Docker, `postgres_data` persists the database across container recreation. `/health` returns HTTP `503` when PostgreSQL is unavailable.

The current startup migration is intentionally simple. For coordinated multi-environment or production schema management, replace it with a migration tool such as Alembic.

## Dashboard and live updates

The dashboard is `api/dashboard.html`, served at `/dashboard`. It displays historical record counts, Isolation Forest anomaly counts, recent readings, available result models, a normalized CO chart, sensor activity, source timestamps, connection state, and an explicit historical replay notice.

The browser maintains an `EventSource` connection to `/api/v1/events`. FastAPI obtains a database snapshot every five seconds and streams it to the page without a full reload. The browser's EventSource client automatically retries after a lost connection.

Each snapshot limits chart series to the 120 most recent observations. The events endpoint reads PostgreSQL for each update; larger deployments may benefit from a shared publication/cache layer.

## Logging and metrics

The API writes structured JSON logs to stdout/stderr. HTTP events include the request ID (returned as `X-Request-ID`), method, normalized route, status code, and duration in milliseconds. CSV imports, unhandled errors, and accepted IoT readings are also logged.

`GET /metrics` exposes Prometheus metrics including:

| Metric | Type | Labels/use |
|---|---|---|
| `air_quality_http_requests_total` | Counter | HTTP method, route, and status |
| `air_quality_http_request_duration_seconds` | Histogram | HTTP method and route |
| `air_quality_sensor_readings_total` | Counter | Readings accepted by this API process |

Application metrics are process-local and reset when the container restarts. Configure Prometheus externally for multi-worker aggregation or historical retention. `/metrics` has no built-in authentication; do not expose it publicly without access controls.

## Tests

Run the test suite from an environment with the dependencies in `requirements.txt`:

```powershell
python -m pytest -q
```

Tests use in-memory SQLite and temporary/fixture CSV files. They cover health, dashboard and metrics responses; ingestion, validation and persistence; replay source/timestamp semantics and retention; database URL configuration; idempotent CSV import and changed-file reload; real project data/model imports; Gradient Boosting and DBSCAN output generation; compatibility routes; and unknown-result handling.

SQLite tests validate API and ORM behavior but do not replace testing against PostgreSQL. After starting Compose, inspect PostgreSQL with:

```powershell
docker compose exec -T db psql -U air_quality -d air_quality `
  -c "SELECT model, count(*) FROM analysis_records GROUP BY model ORDER BY model;"

docker compose exec -T db psql -U air_quality -d air_quality `
  -c "SELECT source_type, count(*) FROM sensor_readings GROUP BY source_type;"
```

## Configuration and security

| Setting | Purpose | Default/notes |
|---|---|---|
| `config/config.yaml` | API host/port and data paths | API port `8000` |
| `DATABASE_URL` | Full SQLAlchemy URL; takes precedence | `postgresql+psycopg://...` |
| `POSTGRES_HOST` | Database host when using split variables | `db` in Compose; usually `localhost` on host |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `air_quality` |
| `POSTGRES_USER` | Database user | `air_quality` |
| `POSTGRES_PASSWORD` | Compose database password | Override outside local development |
| `API_PORT` | Host port published by Compose | `8000` |
| `SIMULATED_SENSOR_ID` | Replay sensor ID | `uci-historical-replay` |
| `SIMULATOR_INTERVAL_SECONDS` | Delay between replay readings | `2` seconds |
| `SENSOR_API_URL` | URL for directly run replay script | `http://127.0.0.1:8000/api/v1/readings` |
| `SENSOR_ID` | Sensor ID for standalone replay script | `uci-historical-replay` |
| `SENSOR_DATASET_PATH` | CSV for standalone replay script | Project cleaned CSV |

`.env.example` is a Compose template, not a place to store production secrets. `.env` and private environment files are excluded from Git.

Before a real deployment:

- Replace default credentials and use a secrets manager.
- Do not expose PostgreSQL directly to the Internet.
- Add authentication and authorization to ingestion and operational endpoints.
- Serve HTTP behind TLS and a reverse proxy.
- Apply appropriate sensor-ID limits, retention, rate limits, and payload-size limits.
- Do not send personal data in sensor values or identifiers.
- Define retention and access policies for time-series data.
- Restrict `/metrics` to a trusted monitoring network.
- Add access control to the dashboard if it contains sensitive data.

## Known limitations and future work

The academic proposal refers to Lambda architecture, Kafka/Flume/HDFS, time-series collections, HBase, LSTM/GAN models, Power BI, and GDPR considerations. **Those components should not be considered deployed by this repository.**

Current capabilities include local Spark batch analysis, scikit-learn models, HTTP ingestion into PostgreSQL, periodic SSE updates, and a historical dataset replay for continuous demonstrations.

For a real sensor deployment, further work should include selecting and calibrating suitable devices; introducing a trusted gateway and secure transport such as MQTT over TLS; defining UTC timestamps, units, zones, data quality, and calibration metadata; validating physical ranges; adding authentication, monitoring, alerting, and rate limits; and evaluating online predictions before issuing municipal alerts.

Historical replay is a demonstration aid. It is not a sensor, a current public data source, or proof of an operational prediction system.

## Troubleshooting

### `Connection refused` when starting the API

Check that PostgreSQL is running and healthy:

```powershell
docker compose ps
docker compose logs --tail 100 db
```

For a local API, verify `DATABASE_URL` or the `POSTGRES_*` settings and confirm PostgreSQL is listening on the expected port.

### Port 8000 is already in use

With Compose:

```powershell
$env:API_PORT = "8080"
docker compose up -d
```

Then open `http://localhost:8080`. For local execution, use `python main.py --port 8080`.

### The dashboard says “Waiting for readings”

Check that the replay simulator is running:

```powershell
docker compose --profile demo up -d simulator
docker compose logs --tail 30 simulator
docker compose exec -T db psql -U air_quality -d air_quality `
  -c "SELECT source_type, count(*) FROM sensor_readings GROUP BY source_type;"
```

If you do not want to simulate readings, submit a real sensor payload to `POST /api/v1/readings`.

### Gradient Boosting or DBSCAN results are missing

The importer only loads CSV files that exist. Run the pipeline on the processed data, then restart the API:

```powershell
python main.py --skip-spark --skip-clustering-prep --skip-api
docker compose restart api
```

Alternatively, run the Compose batch profile.

### The simulator does not start

Review `docker compose logs simulator` and check the API:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Inside Compose, the simulator connects to `http://api:8000/api/v1/readings`. Do not replace the hostname with `localhost` inside the container.

### Spark warns that `winutils.exe` is missing

This Hadoop warning can appear on Windows even when Spark completes its analysis. Check the process exit code and pipeline completion message. For reproducible cross-platform execution, use the Docker batch profile.

### CSV changes are not visible in the API

Restart the API. At startup it recalculates SHA-256 fingerprints and replaces records for any model whose CSV changed:

```powershell
docker compose restart api
```

## License and data provenance

This repository is presented as an academic and educational project. Check the original UCI dataset's terms of use and attribution requirements before redistributing it or incorporating it into another product.
