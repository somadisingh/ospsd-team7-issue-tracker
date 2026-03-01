"""Unit tests for the TrelloList (List) implementation."""

from typing import Any

import pytest
from trello_client_impl import TrelloList


@pytest.mark.unit
class TestTrelloList:
    """Test the TrelloList implementation."""

    def test_trello_list_initialization(self) -> None:
        """Test TrelloList can be initialized."""
        list_obj = TrelloList(id="list_123", name="To Do", board_id="board_1")
        assert list_obj.id == "list_123"
        assert list_obj.name == "To Do"
        assert list_obj.board_id == "board_1"

    def test_trello_list_from_api(self, mock_list_response: Any) -> None:
        """Test TrelloList.from_api static method."""
        list_obj = TrelloList.from_api(mock_list_response)
        assert list_obj.id == mock_list_response["id"]
        assert list_obj.name == mock_list_response["name"]
        assert list_obj.board_id == mock_list_response.get("idBoard", "")

    def test_trello_list_properties(self) -> None:
        """Test TrelloList properties are accessible."""
        list_obj = TrelloList(id="test_id", name="In Progress", board_id="b1")
        assert hasattr(list_obj, "id")
        assert hasattr(list_obj, "name")
        assert hasattr(list_obj, "board_id")
        assert list_obj.id == "test_id"
        assert list_obj.name == "In Progress"
        assert list_obj.board_id == "b1"
