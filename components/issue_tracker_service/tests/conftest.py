"""Conftest for issue_tracker_service tests."""

# Unit tests use an isolated SQLite DB so CI does not need Postgres. Override before importing the app.
import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["OTEL_SDK_DISABLED"] = "true"

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from api.issue import Status
from fastapi.testclient import TestClient
from issue_tracker_service.main import app, get_authenticated_client


@pytest.fixture
def mock_trello_client() -> MagicMock:
    """Provide a mock TrelloClient with all methods stubbed."""
    return MagicMock()


@pytest.fixture
def test_client(mock_trello_client: MagicMock) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with auth dependency overridden."""
    app.dependency_overrides[get_authenticated_client] = lambda: mock_trello_client
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def raw_client() -> Generator[TestClient, None, None]:
    """TestClient without auth override — for testing auth validation."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_board() -> MagicMock:
    """Provide a mock Board domain object."""
    board = MagicMock()
    board.id = "board_123"
    board.board_name = "Test Board"
    return board


@pytest.fixture
def mock_list_obj() -> MagicMock:
    """Provide a mock List domain object."""
    lst = MagicMock()
    lst.id = "list_456"
    lst.name = "To Do"
    lst.board_id = "board_123"
    return lst


@pytest.fixture
def mock_issue() -> MagicMock:
    """Provide a mock Issue domain object."""
    issue = MagicMock()
    issue.id = "issue_789"
    issue.title = "Fix bug"
    issue.desc = "A bug description"
    issue.members = None
    issue.due_date = None
    issue.status = Status.TO_DO
    issue.board_id = "board_123"
    return issue


@pytest.fixture
def mock_member() -> MagicMock:
    """Provide a mock Member domain object."""
    member = MagicMock()
    member.id = "member_abc"
    member.username = "testuser"
    return member
