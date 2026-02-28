"""Unit tests for the Client abstract class."""

from abc import ABC
from collections.abc import Iterator

import pytest
from issue_tracker_client_api import Board, Issue, List, Member
from issue_tracker_client_api.client import Client, get_client


class _ConcreteIssue(Issue):
    """Minimal Issue implementation for testing Client."""

    def __init__(
        self,
        id: str,
        title: str,
        is_complete: bool,
        *,
        list_id: str = "",
    ) -> None:
        self._id = id
        self._title = title
        self._is_complete = is_complete
        self._list_id = list_id

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def list_id(self) -> str:
        return self._list_id


class _ConcreteList(List):
    """Minimal List implementation for testing."""

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


class _ConcreteBoard(Board):
    """Minimal Board implementation for testing."""

    def __init__(self, id: str, name: str) -> None:
        self._id = id
        self._name = name

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name


class _ConcreteMember(Member):
    """Minimal Member implementation for testing."""

    def __init__(
        self,
        id: str,
        username: str | None = None,
        is_board_member: bool | None = None,
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


class _ConcreteClient(Client):
    """Minimal Client implementation for testing."""

    def get_issue(self, issue_id: str) -> Issue:  # type: ignore[empty-body]
        ...

    def delete_issue(self, issue_id: str) -> bool:
        return True

    def update_status(self, issue_id: str, status: str) -> bool:
        return True

    def get_board(self, board_id: str) -> Board:  # type: ignore[empty-body]
        ...

    def get_boards(self) -> Iterator[Board]:
        return iter([])

    def create_board(self, name: str) -> Board:
        return _ConcreteBoard(id="new_board", name=name)

    def add_member_to_board(self, board_id: str, member_id: str) -> Member:
        return _ConcreteMember(id=member_id, username=None, is_board_member=True)

    def get_list(self, list_id: str) -> List:
        return _ConcreteList(id=list_id, name="", board_id="")

    def get_lists(self, board_id: str) -> Iterator[List]:
        return iter([])

    def get_issues_in_list(
        self, list_id: str, max_issues: int = 100
    ) -> Iterator[Issue]:
        return iter([])

    def create_list(self, board_id: str, name: str) -> List:
        return _ConcreteList(id="new_list", name=name, board_id=board_id)

    def update_list(self, list_id: str, name: str) -> List:
        return _ConcreteList(id=list_id, name=name, board_id="")

    def delete_list(self, list_id: str) -> bool:
        return True

    def get_members_on_issue(self, issue_id: str) -> list[Member]:
        return []

    def assign_issue(self, issue_id: str, member_id: str) -> bool:
        return True

    def create_issue(
        self,
        title: str,
        list_id: str,
        *,
        description: str | None = None,
    ) -> Issue:
        return _ConcreteIssue(
            id="new_issue", title=title, is_complete=False, list_id=list_id
        )


@pytest.mark.unit
class TestClientAbstractClass:
    """Test that Client is an abstract base class with required methods."""

    def test_client_is_abstract(self) -> None:
        """Test that Client cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = Client()  # type: ignore[abstract]

    def test_client_is_abc(self) -> None:
        """Test that Client is an ABC."""
        assert issubclass(Client, ABC)

    def test_client_has_required_methods(self) -> None:
        """Test that Client has all required abstract methods."""
        required_methods = [
            "get_issue",
            "delete_issue",
            "update_status",
            "get_board",
            "get_boards",
            "create_board",
            "add_member_to_board",
            "get_list",
            "get_lists",
            "get_issues_in_list",
            "create_list",
            "update_list",
            "delete_list",
            "get_members_on_issue",
            "assign_issue",
            "create_issue",
        ]
        for method_name in required_methods:
            assert hasattr(Client, method_name)

    def test_concrete_client_implementation(self) -> None:
        """Test a concrete Client implementation."""
        client = _ConcreteClient()
        assert client is not None
        assert isinstance(client, Client)


@pytest.mark.unit
class TestGetClientFactory:
    """Test the get_client factory function."""

    def test_get_client_not_implemented(self) -> None:
        """Test that get_client raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            get_client()

    def test_get_client_with_interactive_flag(self) -> None:
        """Test that get_client rejects interactive flag when not implemented."""
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            get_client(interactive=True)
