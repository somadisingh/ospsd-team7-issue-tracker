"""Unit tests for the enhanced health check endpoint.

Validates Requirements 9.2 and 9.3:
- 9.2: WHEN the Database connection is available, THE Health_Check SHALL return 200 OK
- 9.3: WHEN the Database connection is unavailable, THE Health_Check SHALL return 503 Service Unavailable
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestHealthCheckWithDatabase:
    """Test health endpoint when DATABASE_URL is configured."""

    def test_healthy_database_returns_200_connected(self, raw_client: TestClient) -> None:
        """When DB check succeeds, return 200 with database: connected."""
        with patch(
            "issue_tracker_service.routes.health._check_database",
            return_value=True,
        ):
            response = raw_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"

    def test_unhealthy_database_returns_503_unavailable(self, raw_client: TestClient) -> None:
        """When DB check fails, return 503 with database: unavailable."""
        with patch(
            "issue_tracker_service.routes.health._check_database",
            return_value=False,
        ):
            response = raw_client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "unavailable"

    def test_database_check_exception_returns_503(self, raw_client: TestClient) -> None:
        """When _check_database raises an exception, return 503."""
        with patch(
            "issue_tracker_service.routes.health._check_database",
            side_effect=Exception("connection refused"),
        ):
            response = raw_client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "unavailable"


@pytest.mark.unit
class TestHealthCheckWithoutDatabase:
    """Test health endpoint when DATABASE_URL is not configured (local dev fallback)."""

    def test_no_database_url_returns_200_simple_ok(self, raw_client: TestClient) -> None:
        """When DATABASE_URL is not set, return simple 200 with status: ok."""
        # Temporarily remove DATABASE_URL so the health endpoint takes the no-DB path.
        # The conftest sets it globally for the test session; we restore it after.
        saved = os.environ.pop("DATABASE_URL", None)
        try:
            response = raw_client.get("/health")
        finally:
            if saved is not None:
                os.environ["DATABASE_URL"] = saved

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "database" not in data
