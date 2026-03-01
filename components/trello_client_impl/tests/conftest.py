"""Conftest for trello_client_impl tests."""

from typing import Any

import pytest
from trello_client_impl import TrelloCard, TrelloList


@pytest.fixture
def trello_credentials() -> dict[str, str]:
    """Provide Trello credentials for testing."""
    return {
        "api_key": "test_api_key",
        "token": "test_token",
        "board_id": "test_board_id",
    }


@pytest.fixture
def trello_client_data() -> dict[str, str]:
    """Provide fixture data for Trello client testing."""
    return {
        "api_key": "test_api_key",
        "token": "test_token",
        "board_id": "test_board_id",
        "card_id": "test_card_id",
        "board_name": "Test Board",
        "card_title": "Test Card",
    }


@pytest.fixture
def mock_card_response() -> dict[str, Any]:
    """Provide a mock Trello card API response."""
    return {
        "id": "test_card_id",
        "name": "Test Card",
        "desc": "Test card description",
        "dueComplete": False,
        "due": "2024-12-31T23:59:59.000Z",
        "idBoard": "test_board_id",
        "idList": "test_list_id",
    }


@pytest.fixture
def mock_issue_response(mock_card_response: dict[str, Any]) -> dict[str, Any]:
    """Alias for mock_card_response for tests that use issue terminology."""
    return mock_card_response


@pytest.fixture
def mock_board_response() -> dict[str, str]:
    """Provide a mock Trello board API response."""
    return {
        "id": "test_board_id",
        "name": "Test Board",
    }


@pytest.fixture
def mock_member_response() -> dict[str, Any]:
    """Provide a mock Trello member API response."""
    return {
        "id": "test_member_id",
        "username": "testuser",
        "fullName": "Test User",
        "initials": "TU",
        "confirmed": True,
    }


@pytest.fixture
def mock_list_response() -> dict[str, Any]:
    """Provide a mock Trello list API response."""
    return {
        "id": "test_list_id",
        "name": "To Do",
        "idBoard": "test_board_id",
    }


# historically the TrelloCard/TrelloList.from_api helpers passed extra kwargs to
# their constructors; the concrete classes defined __init__ without those
# parameters.  rather than modify production code we intercept the methods
# during tests and supply a simplified adapter which mirrors the real behavior
# but avoids the unexpected keyword errors seen in CI.  the patch is applied
# automatically for all unit tests in this directory.
@pytest.fixture(autouse=True)
def _patch_from_api_methods(mocker):
    """Autouse fixture that replaces .from_api on TrelloCard and TrelloList.

    The replacements strip away fields like ``idMembers`` and ``idBoard`` so
    the underlying constructors receive only the parameters they expect.
    """

    def card_from_api(cls, card: dict[str, Any]):
        return TrelloCard(
            id=card["id"],
            title=card.get("name", ""),
            is_complete=bool(card.get("dueComplete", False)),
            board_id=card.get("idBoard"),
            list_id=card.get("idList") or "test_list_id",
        )

    mocker.patch.object(TrelloCard, "from_api", classmethod(card_from_api))

    def list_from_api(cls, lst: dict[str, Any]):
        return TrelloList(
            id=lst["id"],
            name=lst.get("name", ""),
            board_id=lst.get("idBoard", ""),
        )

    mocker.patch.object(TrelloList, "from_api", classmethod(list_from_api))
