"""Unit tests for the Board abstract class."""

from abc import ABC
from typing import Any

import pytest
from issue_tracker_client_api.board import Board, get_board


@pytest.mark.unit
class TestBoardAbstractClass:
    """Test that Board is an abstract base class with required properties."""

    def test_board_is_abstract(self) -> None:
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = Board()  # type: ignore[abstract]

    def test_board_is_abc(self) -> None:
        assert issubclass(Board, ABC)

    def test_board_has_id_property(self) -> None:
        assert hasattr(Board, "id")
        assert isinstance(Board.id, property)

    def test_board_has_board_name_property(self) -> None:
        assert hasattr(Board, "board_name")
        assert isinstance(Board.board_name, property)

    def test_concrete_board_implementation(
        self, sample_board_data: dict[str, Any]
    ) -> None:
        class ConcreteBoard(Board):  # type: ignore[misc]
            def __init__(self, id: str, board_name: str) -> None:
                self._id = id
                self._board_name = board_name

            @property
            def id(self) -> str:
                return self._id

            @property
            def board_name(self) -> str:
                return self._board_name

        board = ConcreteBoard(
            id=sample_board_data["id"], board_name=sample_board_data["board_name"]
        )
        assert board.id == sample_board_data["id"]
        assert board.board_name == sample_board_data["board_name"]


@pytest.mark.unit
class TestGetBoardFactory:
    """Test the get_board factory function."""

    def test_get_board_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            get_board("test_board_id")
