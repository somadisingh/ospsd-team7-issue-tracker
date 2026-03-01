"""Unit tests for the Member abstract class."""

from abc import ABC
from typing import Any

import pytest
from issue_tracker_client_api.member import Member, get_member


@pytest.mark.unit
class TestMemberAbstractClass:
    """Test that Member is an abstract base class with required properties."""

    def test_member_is_abstract(self) -> None:
        """Test that Member cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = Member()  # type: ignore[abstract]

    def test_member_is_abc(self) -> None:
        """Test that Member is an ABC."""
        assert issubclass(Member, ABC)

    def test_member_has_id_property(self) -> None:
        """Test that Member has an id property."""
        assert hasattr(Member, "id")
        assert isinstance(Member.id, property)

    def test_member_has_username_property(self) -> None:
        """Test that Member has a username property."""
        assert hasattr(Member, "username")
        assert isinstance(Member.username, property)

    def test_member_has_is_board_member_property(self) -> None:
        """Test that Member has an is_board_member property."""
        assert hasattr(Member, "is_board_member")
        assert isinstance(Member.is_board_member, property)

    def test_concrete_member_implementation(
        self, sample_member_data: dict[str, Any]
    ) -> None:
        """Test a concrete Member implementation."""

        class ConcreteMember(Member):
            """Concrete implementation of Member for testing."""

            def __init__(
                self, id: str, username: str | None, is_board_member: bool | None
            ) -> None:
                self._id = id
                self._username = username
                self._is_board_member = is_board_member

            @property
            def id(self) -> str:
                return self._id

            @property
            def username(self) -> str | None:
                return self._username

            @property
            def is_board_member(self) -> bool | None:
                return self._is_board_member

        member = ConcreteMember(
            id=sample_member_data["id"],
            username=sample_member_data["username"],
            is_board_member=sample_member_data["is_board_member"],
        )
        assert member.id == sample_member_data["id"]
        assert member.username == sample_member_data["username"]
        assert member.is_board_member == sample_member_data["is_board_member"]

    def test_member_with_none_properties(self) -> None:
        """Test that Member properties can be None."""

        class ConcreteMember(Member):
            """Concrete implementation of Member for testing."""

            def __init__(self, id: str) -> None:
                self._id = id

            @property
            def id(self) -> str:
                return self._id

            @property
            def username(self) -> str | None:
                return None

            @property
            def is_board_member(self) -> bool | None:
                return None

        member = ConcreteMember(id="test_id")
        assert member.id == "test_id"
        assert member.username is None
        assert member.is_board_member is None


@pytest.mark.unit
class TestGetMemberFactory:
    """Test the get_member factory function."""

    def test_get_member_not_implemented(self) -> None:
        """Test that get_member raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            get_member("test_member_id")
