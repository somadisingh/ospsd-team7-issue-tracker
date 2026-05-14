"""Conftest for issue_tracker_adapter tests."""

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_board_response() -> MagicMock:
    """Provide a mock BoardResponse from the auto-generated client."""
    resp = MagicMock()
    resp.id = "board_123"
    resp.name = "Test Board"
    return resp


@pytest.fixture
def mock_issue_response() -> MagicMock:
    """Provide a mock IssueResponse from the auto-generated client."""
    resp = MagicMock()
    resp.id = "issue_456"
    resp.title = "Test Issue"
    resp.is_complete = False
    resp.list_id = "list_789"
    resp.board_id = "board_123"
    return resp


@pytest.fixture
def mock_list_response() -> MagicMock:
    """Provide a mock ListResponse from the auto-generated client."""
    resp = MagicMock()
    resp.id = "list_789"
    resp.name = "To Do"
    resp.board_id = "board_123"
    return resp


@pytest.fixture
def mock_member_response() -> MagicMock:
    """Provide a mock MemberResponse from the auto-generated client."""
    resp = MagicMock()
    resp.id = "member_abc"
    resp.username = "testuser"
    return resp


@pytest.fixture
def adapter_kwargs() -> dict[str, Any]:
    """Provide kwargs for creating a ServiceClientAdapter."""
    return {
        "base_url": "https://test-service.example.com",
        "session_token": "test_session_token_123",
    }
