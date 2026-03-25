"""Unit tests for the Board abstract class."""

from abc import ABC
from typing import Any

import pytest
from issue_tracker_client_api.board import Board, get_board


@pytest.mark.unit
class TestBoardAbstractClass:
    """Test that Board is an abstract base class with required properties."""

    def test_board_is_abstract(self) -> None:
        """Test that Board cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = Board()  # type: ignore[abstract]

    def test_board_is_abc(self) -> None:
        """Test that Board is an ABC."""
        assert issubclass(Board, ABC)

    def test_board_has_id_property(self) -> None:
        """Test that Board has an id property."""
        assert hasattr(Board, "id")
        assert isinstance(Board.id, property)

    def test_board_has_name_property(self) -> None:
        """Test that Board has a name property."""
        assert hasattr(Board, "name")
        assert isinstance(Board.name, property)

    def test_concrete_board_implementation(
        self, sample_board_data: dict[str, Any]
    ) -> None:
        """Test a concrete Board implementation."""

        class ConcreteBoard(Board):
            """Concrete implementation of Board for testing."""

            def __init__(self, id: str, name: str) -> None:
                self._id = id
                self._name = name

            @property
            def id(self) -> str:
                return self._id

            @property
            def name(self) -> str:
                return self._name

        board = ConcreteBoard(
            id=sample_board_data["id"], name=sample_board_data["name"]
        )
        assert board.id == sample_board_data["id"]
        assert board.name == sample_board_data["name"]


@pytest.mark.unit
class TestGetBoardFactory:
    """Test the get_board factory function."""

    def test_get_board_not_implemented(self) -> None:
        """Test that get_board raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            get_board("test_board_id")
