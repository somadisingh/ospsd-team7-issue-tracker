"""Unit tests for ServiceBoard."""

from unittest.mock import MagicMock

import pytest
from issue_tracker_adapter.board import ServiceBoard
from issue_tracker_client_api.board import Board


@pytest.mark.unit
class TestServiceBoard:
    """Test the ServiceBoard adapter implementation."""

    def test_service_board_initialization(self) -> None:
        board = ServiceBoard(id="board_1", board_name="My Board")
        assert board.id == "board_1"
        assert board.board_name == "My Board"

    def test_service_board_is_instance_of_board(self) -> None:
        board = ServiceBoard(id="b1", board_name="Test")
        assert isinstance(board, Board)

    def test_service_board_properties(self) -> None:
        board = ServiceBoard(id="test_id", board_name="Test Board")
        assert hasattr(board, "id")
        assert hasattr(board, "board_name")
        assert board.id == "test_id"
        assert board.board_name == "Test Board"

    def test_service_board_from_response(self, mock_board_response: MagicMock) -> None:
        board = ServiceBoard.from_response(mock_board_response)
        assert board.id == mock_board_response.id
        assert board.board_name == mock_board_response.board_name
        assert isinstance(board, ServiceBoard)
        assert isinstance(board, Board)
