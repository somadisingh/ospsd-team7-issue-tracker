"""Conftest for issue_tracker_service tests."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from issue_tracker_service.main import app, get_authenticated_client


@pytest.fixture
def mock_trello_client() -> MagicMock:
    """Provide a mock TrelloClient with all methods stubbed."""
    return MagicMock()


@pytest.fixture
def test_client(mock_trello_client: MagicMock) -> TestClient:
    """Provide a FastAPI TestClient with auth dependency overridden."""
    app.dependency_overrides[get_authenticated_client] = lambda: mock_trello_client
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_board() -> MagicMock:
    """Provide a mock Board domain object."""
    board = MagicMock()
    board.id = "board_123"
    board.name = "Test Board"
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
    issue.list_id = "list_456"
    issue.board_id = "board_123"
    issue.is_complete = False
    return issue


@pytest.fixture
def mock_member() -> MagicMock:
    """Provide a mock Member domain object."""
    member = MagicMock()
    member.id = "member_abc"
    member.username = "testuser"
    return member
