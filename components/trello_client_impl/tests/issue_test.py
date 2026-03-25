"""Unit tests for the TrelloCard implementation."""

from typing import Any

import pytest
from trello_client_impl import TrelloCard


@pytest.mark.unit
class TestTrelloCard:
    """Test the TrelloCard implementation."""

    def test_trello_issue_initialization(self) -> None:
        """Test TrelloCard can be initialized with required fields."""
        card = TrelloCard(
            id="card_123",
            title="Test Card",
            is_complete=False,
            board_id="board_123",
            list_id="list_123",
        )
        assert card.id == "card_123"
        assert card.title == "Test Card"
        assert card.is_complete is False
        assert card.board_id == "board_123"
        assert card.list_id == "list_123"

    def test_trello_card_from_api(self, mock_card_response: Any) -> None:
        """Test TrelloCard.from_api static method."""
        card = TrelloCard.from_api(mock_card_response)
        assert card.id == mock_card_response["id"]

    def test_trello_card_properties(self) -> None:
        """Test TrelloCard properties are accessible (Issue contract: id, title, is_complete, list_id, board_id)."""
        card = TrelloCard(
            id="test_id",
            title="Test",
            is_complete=True,
            board_id="board_1",
            list_id="list_1",
        )
        assert hasattr(card, "id")
        assert hasattr(card, "title")
        assert hasattr(card, "is_complete")
        assert hasattr(card, "list_id")
        assert hasattr(card, "board_id")
        assert card.list_id == "list_1"
        assert card.board_id == "board_1"
