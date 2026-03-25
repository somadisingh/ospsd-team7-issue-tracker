"""Unit tests for the TrelloMember (Member) implementation."""

from typing import Any

import pytest
from trello_client_impl import TrelloMember


@pytest.mark.unit
class TestTrelloMember:
    """Test the TrelloMember implementation."""

    def test_trello_member_initialization(self) -> None:
        """Test TrelloMember can be initialized."""
        member = TrelloMember(
            id="member_123", username="testuser", is_board_member=True
        )
        assert member.id == "member_123"
        assert member.username == "testuser"
        assert member.is_board_member is True

    def test_trello_member_from_api(self, mock_member_response: Any) -> None:
        """Test TrelloMember.from_api static method."""
        member = TrelloMember.from_api(mock_member_response)
        assert member.id == mock_member_response["id"]

    def test_trello_member_optional_fields(self) -> None:
        """Test TrelloMember with optional fields."""
        member = TrelloMember(id="member_123", username=None, is_board_member=None)
        assert member.id == "member_123"
        assert member.username is None
        assert member.is_board_member is None
