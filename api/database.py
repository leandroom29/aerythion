from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_session_factory(database_url: str | URL) -> tuple[Engine, sessionmaker[Session]]:
    options: dict = {"pool_pre_ping": True}
    parsed_url = make_url(database_url)
    if parsed_url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
        if parsed_url.database in (None, "", ":memory:"):
            options["poolclass"] = StaticPool

    engine = create_engine(database_url, **options)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def configured_database_url() -> str | URL:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    if os.getenv("POSTGRES_HOST"):
        return URL.create(
            "postgresql+psycopg",
            username=os.getenv("POSTGRES_USER", "air_quality"),
            password=os.getenv("POSTGRES_PASSWORD", "air_quality_dev"),
            host=os.environ["POSTGRES_HOST"],
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "air_quality"),
        )

    return "postgresql+psycopg://air_quality:air_quality_dev@localhost:5432/air_quality"


def get_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session
