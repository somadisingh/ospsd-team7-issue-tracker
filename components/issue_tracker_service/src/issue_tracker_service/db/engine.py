"""Database engine and session factory."""

from __future__ import annotations

import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .base import Base

load_dotenv()

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_database_url() -> str:
    """Return DSN for SQLAlchemy. Set ``DATABASE_URL`` in the environment (or .env)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        msg = "DATABASE_URL is not set. Add it to your environment or .env (see .env.example)."
        raise RuntimeError(msg)
    return url


def _is_sqlite(url: str) -> bool:
    return url.strip().lower().startswith("sqlite")


def get_engine() -> Engine:
    """Singleton SQLAlchemy engine (sync)."""
    global _engine, SessionLocal
    if _engine is not None:
        return _engine

    url = get_database_url()
    if _is_sqlite(url):
        # Single shared in-memory database across connections (tests + app)
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Enforce foreign keys in SQLite
        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        _engine = create_engine(
            url,
            pool_pre_ping=True,
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a database session and close it after the request."""
    if SessionLocal is None:
        get_engine()
    assert SessionLocal is not None
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create tables (SQLite unit tests / local dev) or no-op (Postgres: use Alembic)."""
    engine = get_engine()
    url = get_database_url()
    if _is_sqlite(url):
        Base.metadata.create_all(bind=engine)
