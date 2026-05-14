"""Unit tests for ServiceBoard."""

from unittest.mock import MagicMock

import pytest
from issue_tracker_adapter.board import ServiceBoard
from issue_tracker_client_api.board import Board


@pytest.mark.unit
class TestServiceBoard:
    """Test the ServiceBoard adapter implementation."""

    def test_service_board_initialization(self) -> None:
        board = ServiceBoard(id="board_1", name="My Board")
        assert board.id == "board_1"
        assert board.name == "My Board"

    def test_service_board_is_instance_of_board(self) -> None:
        board = ServiceBoard(id="b1", name="Test")
        assert isinstance(board, Board)

    def test_service_board_properties(self) -> None:
        board = ServiceBoard(id="test_id", name="Test Board")
        assert hasattr(board, "id")
        assert hasattr(board, "name")
        assert board.id == "test_id"
        assert board.name == "Test Board"

    def test_service_board_from_response(self, mock_board_response: MagicMock) -> None:
        board = ServiceBoard.from_response(mock_board_response)
        assert board.id == mock_board_response.id
        assert board.name == mock_board_response.name
        assert isinstance(board, ServiceBoard)
        assert isinstance(board, Board)
