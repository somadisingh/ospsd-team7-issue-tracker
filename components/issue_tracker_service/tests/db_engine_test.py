"""Unit tests for ``issue_tracker_service.db.engine``.

These exercise the pure URL-normalization helpers, the ``DATABASE_URL``
guard, the postgres branch of ``get_engine`` (which only constructs the
SQLAlchemy engine — no connection is opened), and the lazy initialization
in ``get_db`` / ``init_db``.
"""

from __future__ import annotations

import pytest
from sqlalchemy.engine import Engine

import issue_tracker_service.db.engine as engine_module


@pytest.mark.unit
class TestNormalizePostgresUrl:
    """Direct unit tests for the URL canonicalization helper."""

    def test_empty_and_sqlite_pass_through(self) -> None:
        assert engine_module._normalize_postgres_url("") == ""
        assert engine_module._normalize_postgres_url("sqlite:///:memory:") == "sqlite:///:memory:"
        assert engine_module._normalize_postgres_url("SQLite+pysqlite:///foo.db") == "SQLite+pysqlite:///foo.db"

    def test_bare_postgresql_rewritten_to_psycopg(self) -> None:
        out = engine_module._normalize_postgres_url("postgresql://u:p@h/db")
        assert out.startswith("postgresql+psycopg://")

    def test_postgres_alias_rewritten_to_psycopg(self) -> None:
        out = engine_module._normalize_postgres_url("postgres://u:p@h/db")
        assert out.startswith("postgresql+psycopg://")

    def test_psycopg2_explicitly_remapped(self) -> None:
        out = engine_module._normalize_postgres_url("postgresql+psycopg2://u:p@h/db")
        assert out.startswith("postgresql+psycopg://")

    def test_quoted_url_is_stripped_before_normalizing(self) -> None:
        out = engine_module._normalize_postgres_url('  "postgresql://u:p@h/db"  ')
        assert out.startswith("postgresql+psycopg://")
        out = engine_module._normalize_postgres_url("'postgres://u:p@h/db'")
        assert out.startswith("postgresql+psycopg://")

    def test_unknown_driver_passes_through(self) -> None:
        url = "mysql+pymysql://u:p@h/db"
        assert engine_module._normalize_postgres_url(url) == url

    def test_unparseable_url_falls_back_to_input(self) -> None:
        """The defensive ``except Exception`` branch returns the original input
        when SQLAlchemy's URL parser raises."""
        # `make_url` raises on a non-empty string without a recognizable
        # scheme separator.
        url = "not-a-real-url"
        out = engine_module._normalize_postgres_url(url)
        assert out == url


@pytest.mark.unit
class TestGetDatabaseUrl:
    def test_raises_when_database_url_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
            engine_module.get_database_url()

    def test_returns_normalized_postgres_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
        out = engine_module.get_database_url()
        assert out.startswith("postgresql+psycopg://")

    def test_returns_sqlite_url_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
        assert engine_module.get_database_url() == "sqlite+pysqlite:///:memory:"


@pytest.mark.unit
class TestGetEngineBranches:
    """Exercise the singleton + postgres / sqlite branching."""

    def test_postgres_branch_creates_engine_without_connecting(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``create_engine`` is lazy: passing a postgres URL must not try to
        open a TCP connection at construction time. We just verify the URL
        was normalized onto the psycopg3 dialect."""
        monkeypatch.setattr(engine_module, "_engine", None, raising=False)
        monkeypatch.setattr(engine_module, "SessionLocal", None, raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
        eng = engine_module.get_engine()
        assert isinstance(eng, Engine)
        assert "psycopg" in str(eng.url)
        # SessionLocal is wired in either branch.
        assert engine_module.SessionLocal is not None

    def test_get_engine_is_idempotent(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(engine_module, "_engine", None, raising=False)
        monkeypatch.setattr(engine_module, "SessionLocal", None, raising=False)
        monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
        first = engine_module.get_engine()
        second = engine_module.get_engine()
        assert first is second


@pytest.mark.unit
class TestGetDb:
    def test_get_db_lazily_initializes_when_session_local_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``get_db`` calls ``get_engine`` when ``SessionLocal`` has not yet
        been built (covers the lazy branch on line 95)."""
        monkeypatch.setattr(engine_module, "_engine", None, raising=False)
        monkeypatch.setattr(engine_module, "SessionLocal", None, raising=False)
        monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
        gen = engine_module.get_db()
        session = next(gen)
        try:
            assert session is not None
        finally:
            gen.close()
        assert engine_module.SessionLocal is not None


@pytest.mark.unit
class TestInitDb:
    def test_init_db_creates_tables_on_sqlite(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(engine_module, "_engine", None, raising=False)
        monkeypatch.setattr(engine_module, "SessionLocal", None, raising=False)
        monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
        # Should not raise; metadata.create_all is idempotent.
        engine_module.init_db()

    def test_init_db_is_noop_on_postgres(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """For non-sqlite URLs, ``init_db`` deliberately skips ``create_all``
        (Alembic owns the schema in production). Covers the false branch
        of the ``if _is_sqlite(url):`` guard."""
        monkeypatch.setattr(engine_module, "_engine", None, raising=False)
        monkeypatch.setattr(engine_module, "SessionLocal", None, raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
        # Must not attempt to talk to a real Postgres host.
        engine_module.init_db()
