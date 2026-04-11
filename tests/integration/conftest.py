"""Conftest for integration tests."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from api.issue import Status
from pytest_mock import MockerFixture
from trello_client_impl import TrelloCard, TrelloList


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
    }


@pytest.fixture
def integration_env_setup(
    mocker: MockerFixture, integration_credentials: dict[str, str]
) -> None:
    """Setup environment for integration tests (no longer used but kept for compatibility)."""


@pytest.fixture
def mock_client_implementation() -> MagicMock:
    """Provide a mock client implementation for integration tests."""
    mock_client = MagicMock()
    mock_client.get_issue = MagicMock()
    mock_client.delete_issue = MagicMock(return_value=True)
    mock_client.get_board = MagicMock()
    mock_client.get_boards = MagicMock()
    mock_client.create_board = MagicMock()
    mock_client.update_board = MagicMock()
    mock_client.delete_board = MagicMock(return_value=True)
    mock_client.get_issues = MagicMock()
    mock_client.update_issue = MagicMock()
    mock_client.create_issue = MagicMock()
    mock_client.add_member_to_board = MagicMock()
    mock_client.get_list = MagicMock()
    mock_client.get_lists = MagicMock()
    mock_client.get_issues_in_list = MagicMock()
    mock_client.create_list = MagicMock()
    mock_client.update_list = MagicMock()
    mock_client.delete_list = MagicMock(return_value=True)
    mock_client.get_members_on_issue = MagicMock()
    mock_client.assign_issue = MagicMock(return_value=True)
    return mock_client


@pytest.fixture
def mock_issue_response() -> dict[str, Any]:
    """Provide a mock Trello card API response for integration tests."""
    return {
        "id": "test_issue_id",
        "name": "Test Issue",
        "desc": "Test issue description",
        "idMembers": ["member1"],
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
        "idBoard": "test_board_id",
    }


@pytest.fixture(autouse=True)
def _patch_from_api_methods(mocker):
    def card_from_api(cls, card: dict[str, Any], *, list_name: str = ""):
        return TrelloCard(
            id=card["id"],
            title=card.get("name", ""),
            desc=card.get("desc", ""),
            members=card.get("idMembers") or None,
            due_date=card.get("due"),
            status=Status.TO_DO,
            board_id=card.get("idBoard", ""),
        )

    mocker.patch.object(TrelloCard, "from_api", classmethod(card_from_api))

    def list_from_api(cls, lst: dict[str, Any]):
        return TrelloList(
            id=lst["id"],
            name=lst.get("name", ""),
            board_id=lst.get("idBoard", ""),
        )

    mocker.patch.object(TrelloList, "from_api", classmethod(list_from_api))
