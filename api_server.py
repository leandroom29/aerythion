"""Compatibility entry point for the FastAPI application."""

import uvicorn

from api.main import app
from config.settings import PROJECT_CONFIG


def run_api(host: str | None = None, port: int | None = None, debug: bool | None = None):
    config = PROJECT_CONFIG["api"]
    uvicorn.run(
        "api.main:app",
        host=host or config.get("host", "127.0.0.1"),
        port=int(port or config.get("port", 8000)),
        reload=bool(debug) if debug is not None else False,
    )
