"""Conftest for integration tests."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_requests_integration(mocker: MockerFixture) -> Any:
    """Provide a mock requests module for integration tests."""
    return mocker.patch("requests.request")


@pytest.fixture
def integration_credentials() -> dict[str, str]:
    """Provide test credentials for integration tests."""
    return {
        "api_key": "integration_test_api_key",
        "token": "integration_test_token",
        "board_id": "integration_test_board_id",
    }


@pytest.fixture
def integration_env_setup(
    mocker: MockerFixture, integration_credentials: dict[str, str]
) -> None:
    """Setup environment for integration tests (no longer used but kept for compatibility)."""
    # Deprecated: credentials are now injected via integration_credentials fixture


@pytest.fixture
def mock_client_implementation() -> MagicMock:
    """Provide a mock client implementation for integration tests."""
    mock_client = MagicMock()
    mock_client.get_issue = MagicMock()
    mock_client.delete_issue = MagicMock(return_value=True)
    mock_client.update_status = MagicMock(return_value=True)
    mock_client.get_issues = MagicMock()
    mock_client.get_board = MagicMock()
    mock_client.get_boards = MagicMock()
    mock_client.get_lists = MagicMock()
    mock_client.get_members_on_card = MagicMock()
    mock_client.assign_issue = MagicMock(return_value=True)
    mock_client.create_issue = MagicMock()
    return mock_client


@pytest.fixture
def mock_card_response() -> dict[str, Any]:
    """Provide a mock Trello card API response for integration tests."""
    return {
        "id": "test_card_id",
        "name": "Test Card",
        "desc": "Test card description",
        "dueComplete": False,
        "due": "2026-02-15T23:59:59.000Z",
        "idBoard": "test_board_id",
        "idList": "test_list_id",
    }


@pytest.fixture
def mock_board_response() -> dict[str, Any]:
    """Provide a mock Trello board API response for integration tests."""
    return {
        "id": "test_board_id",
        "name": "Test Board",
    }


@pytest.fixture
def mock_member_response() -> dict[str, Any]:
    """Provide a mock Trello member API response for integration tests."""
    return {
        "id": "test_member_id",
        "username": "testuser",
        "fullName": "Test User",
        "initials": "TU",
        "confirmed": True,
    }


@pytest.fixture
def mock_list_response() -> dict[str, Any]:
    """Provide a mock Trello list API response for integration tests."""
    return {
        "id": "test_list_id",
        "name": "To Do",
    }
