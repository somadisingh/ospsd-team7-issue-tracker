"""Unit tests for the Client abstract class and domain exceptions."""

from abc import ABC
from collections.abc import Iterator

import pytest
from api.issue import Status
from issue_tracker_client_api import Board, Issue
from issue_tracker_client_api.client import Client, get_client
from issue_tracker_client_api.exceptions import (
    AuthenticationError,
    IssueTrackerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from issue_tracker_client_api.list import List
from issue_tracker_client_api.member import Member


class _ConcreteIssue(Issue):  # type: ignore[misc]
    """Minimal Issue implementation for testing Client."""

    def __init__(
        self, id: str, title: str, desc: str, status: Status, board_id: str
    ) -> None:
        self._id = id
        self._title = title
        self._desc = desc
        self._status = status
        self._board_id = board_id

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def desc(self) -> str:
        return self._desc

    @property
    def members(self) -> list[str] | None:
        return None

    @property
    def due_date(self) -> str | None:
        return None

    @property
    def status(self) -> Status:
        return self._status

    @property
    def board_id(self) -> str:
        return self._board_id


class _ConcreteBoard(Board):  # type: ignore[misc]
    """Minimal Board implementation for testing."""

    def __init__(self, id: str, board_name: str) -> None:
        self._id = id
        self._board_name = board_name

    @property
    def id(self) -> str:
        return self._id

    @property
    def board_name(self) -> str:
        return self._board_name


class _ConcreteList(List):
    """Minimal List implementation for testing."""

    def __init__(self, id: str, name: str, board_id: str) -> None:
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

    # -- SharedClient CRUD methods --

    def get_issue(self, issue_id: str) -> Issue:
        return _ConcreteIssue(
            id=issue_id, title="T", desc="", status=Status.TO_DO, board_id="b1"
        )

    def get_board(self, board_id: str) -> Board:
        return _ConcreteBoard(id=board_id, board_name="B")

    def get_issues(self, board_id: str) -> Iterator[Issue]:
        return iter([])

    def get_boards(self) -> Iterator[Board]:
        return iter([])

    def update_issue(
        self,
        issue_id: str,
        title: str | None = None,
        desc: str | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        status: Status | None = None,
        board_id: str | None = None,
    ) -> Issue:
        return _ConcreteIssue(
            id=issue_id,
            title=title or "T",
            desc=desc or "",
            status=status or Status.TO_DO,
            board_id=board_id or "b1",
        )

    def update_board(self, board_id: str, name: str | None = None) -> Board:
        return _ConcreteBoard(id=board_id, board_name=name or "B")

    def delete_issue(self, issue_id: str) -> bool:
        return True

    def delete_board(self, board_id: str) -> bool:
        return True

    def create_issue(
        self,
        title: str,
        board_id: str,
        desc: str | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        status: Status = Status.TO_DO,
    ) -> Issue:
        return _ConcreteIssue(
            id="new", title=title, desc=desc or "", status=status, board_id=board_id
        )

    def create_board(self, name: str) -> Board:
        return _ConcreteBoard(id="new_board", board_name=name)

    # -- OAuth methods --

    def get_authorization_url(self, callback_url: str | None = None) -> str:
        return "https://example.com/auth"

    def exchange_request_token(self, oauth_token: str, oauth_verifier: str) -> None:
        pass

    # -- Internal List operations --

    def get_list(self, list_id: str) -> List:
        return _ConcreteList(id=list_id, name="To Do", board_id="b1")

    def get_lists(self, board_id: str) -> Iterator[List]:
        return iter([])

    def get_issues_in_list(
        self, list_id: str, max_issues: int = 100
    ) -> Iterator[Issue]:
        return iter([])

    def create_list(self, board_id: str, name: str) -> List:
        return _ConcreteList(id="new_list", name=name, board_id=board_id)

    def update_list(self, list_id: str, name: str) -> List:
        return _ConcreteList(id=list_id, name=name, board_id="b1")

    def delete_list(self, list_id: str) -> bool:
        return True

    # -- Internal Member operations --

    def get_members_on_issue(self, issue_id: str) -> list[Member]:
        return []

    def assign_issue(self, issue_id: str, member_id: str) -> bool:
        return True

    def add_member_to_board(self, board_id: str, member_id: str) -> bool:
        return True


@pytest.mark.unit
class TestClientAbstractClass:
    """Test that Client is an abstract base class with required methods."""

    def test_client_is_abstract(self) -> None:
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = Client()  # type: ignore[abstract]

    def test_client_is_abc(self) -> None:
        assert issubclass(Client, ABC)

    def test_client_has_shared_crud_methods(self) -> None:
        shared_methods = [
            "get_issue",
            "get_board",
            "get_issues",
            "get_boards",
            "update_issue",
            "update_board",
            "delete_issue",
            "delete_board",
            "create_issue",
            "create_board",
        ]
        for method_name in shared_methods:
            assert hasattr(Client, method_name)

    def test_client_has_auth_methods(self) -> None:
        auth_methods = ["get_authorization_url", "exchange_request_token"]
        for method_name in auth_methods:
            assert hasattr(Client, method_name)

    def test_client_has_list_methods(self) -> None:
        list_methods = [
            "get_list",
            "get_lists",
            "get_issues_in_list",
            "create_list",
            "update_list",
            "delete_list",
        ]
        for method_name in list_methods:
            assert hasattr(Client, method_name)

    def test_client_has_member_methods(self) -> None:
        member_methods = [
            "get_members_on_issue",
            "assign_issue",
            "add_member_to_board",
        ]
        for method_name in member_methods:
            assert hasattr(Client, method_name)

    def test_concrete_client_implementation(self) -> None:
        client = _ConcreteClient()
        assert client is not None
        assert isinstance(client, Client)


@pytest.mark.unit
class TestGetClientFactory:
    """Test the get_client factory function."""

    def test_get_client_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            get_client()

    def test_get_client_with_interactive_flag(self) -> None:
        with pytest.raises(NotImplementedError):
            get_client(interactive=True)


@pytest.mark.unit
class TestDomainExceptions:
    """Test domain-specific exception hierarchy."""

    def test_base_exception_is_catchable(self) -> None:
        with pytest.raises(IssueTrackerError):
            raise IssueTrackerError

    def test_resource_not_found_inherits_base(self) -> None:
        exc = ResourceNotFoundError("board", "abc123")
        assert isinstance(exc, IssueTrackerError)
        assert exc.resource_type == "board"
        assert exc.resource_id == "abc123"
        assert "board" in str(exc)
        assert "abc123" in str(exc)

    def test_authentication_error_inherits_base(self) -> None:
        assert isinstance(AuthenticationError(), IssueTrackerError)

    def test_service_unavailable_inherits_base(self) -> None:
        assert isinstance(ServiceUnavailableError(), IssueTrackerError)

    def test_validation_error_inherits_base(self) -> None:
        assert isinstance(ValidationError(), IssueTrackerError)

    def test_resource_not_found_catchable_as_base(self) -> None:
        with pytest.raises(IssueTrackerError):
            raise ResourceNotFoundError("board", "id")

    def test_auth_error_catchable_as_base(self) -> None:
        with pytest.raises(IssueTrackerError):
            raise AuthenticationError

    def test_service_unavailable_catchable_as_base(self) -> None:
        with pytest.raises(IssueTrackerError):
            raise ServiceUnavailableError

    def test_validation_error_catchable_as_base(self) -> None:
        with pytest.raises(IssueTrackerError):
            raise ValidationError
