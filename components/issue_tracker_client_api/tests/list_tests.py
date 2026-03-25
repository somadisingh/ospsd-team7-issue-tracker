"""Unit tests for the List abstract class."""

from abc import ABC
from typing import Any

import pytest
from issue_tracker_client_api.list import List, get_list


@pytest.mark.unit
class TestListAbstractClass:
    """Test that List is an abstract base class with required properties."""

    def test_list_is_abstract(self) -> None:
        """Test that List cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = List()  # type: ignore[abstract]

    def test_list_is_abc(self) -> None:
        """Test that List is an ABC."""
        assert issubclass(List, ABC)

    def test_list_has_id_property(self) -> None:
        """Test that List has an id property."""
        assert hasattr(List, "id")
        assert isinstance(List.id, property)

    def test_list_has_name_property(self) -> None:
        """Test that List has a name property."""
        assert hasattr(List, "name")
        assert isinstance(List.name, property)

    def test_list_has_board_id_property(self) -> None:
        """Test that List has a board_id property."""
        assert hasattr(List, "board_id")
        assert isinstance(List.board_id, property)

    def test_concrete_list_implementation(
        self, sample_list_data: dict[str, Any]
    ) -> None:
        """Test a concrete List implementation."""

        class ConcreteList(List):
            """Concrete implementation of List for testing."""

            def __init__(self, id: str, name: str, *, board_id: str = "") -> None:
                self._id = id
                self._name = name
                self._board_id = board_id

            @property
            def id(self) -> str:
                return self._id

            @property
            def name(self) -> str:
                return self._name

            @property
            def board_id(self) -> str:
                return self._board_id

        list_obj = ConcreteList(
            id=sample_list_data["id"],
            name=sample_list_data["name"],
            board_id=sample_list_data["board_id"],
        )
        assert list_obj.id == sample_list_data["id"]
        assert list_obj.name == sample_list_data["name"]
        assert list_obj.board_id == sample_list_data["board_id"]


@pytest.mark.unit
class TestGetListFactory:
    """Test the get_list factory function."""

    def test_get_list_not_implemented(self) -> None:
        """Test that get_list raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            get_list("test_list_id")
