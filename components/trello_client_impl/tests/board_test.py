"""Unit tests for the TrelloBoard (Board) implementation."""

from typing import Any

import pytest
from trello_client_impl import TrelloBoard


@pytest.mark.unit
class TestTrelloBoard:
    """Test the TrelloBoard implementation."""

    def test_trello_board_initialization(self) -> None:
        """Test TrelloBoard can be initialized."""
        board = TrelloBoard(id="board_123", name="Test Board")
        assert board.id == "board_123"
        assert board.name == "Test Board"

    def test_trello_board_from_api(self, mock_board_response: Any) -> None:
        """Test TrelloBoard.from_api static method."""
        board = TrelloBoard.from_api(mock_board_response)
        assert board.id == mock_board_response["id"]
        assert board.name == mock_board_response["name"]

    def test_trello_board_properties(self) -> None:
        """Test TrelloBoard properties are accessible."""
        board = TrelloBoard(id="test_id", name="Test Board")
        assert hasattr(board, "id")
        assert hasattr(board, "name")
        assert board.id == "test_id"
        assert board.name == "Test Board"
