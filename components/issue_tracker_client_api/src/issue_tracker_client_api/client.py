"""Core issue tracker client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from issue_tracker_client_api.board import Board
from issue_tracker_client_api.issue import Issue
from issue_tracker_client_api.list import List
from issue_tracker_client_api.member import Member

__all__ = ["Client", "get_client"]


class Client(ABC):
    """Abstract base class representing an issue tracker client for managing issues."""

    @abstractmethod
    def get_issue(self, issue_id: str) -> Issue:
        """Return a single issue by its ID."""
        raise NotImplementedError("Subclasses must implement get_issue")

    @abstractmethod
    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue by its ID."""
        raise NotImplementedError("Subclasses must implement delete_issue")

    @abstractmethod
    def update_status(self, issue_id: str, status: str) -> bool:
        """Update an issue's status (e.g. 'todo', 'in_progress', 'complete')."""
        raise NotImplementedError("Subclasses must implement update_status")

    @abstractmethod
    def get_board(self, board_id: str) -> Board:
        """Return a single board by its ID."""
        raise NotImplementedError("Subclasses must implement get_board")

    @abstractmethod
    def get_boards(self) -> Iterator[Board]:
        """Return an iterator of boards for the authenticated user."""
        raise NotImplementedError("Subclasses must implement get_boards")

    @abstractmethod
    def create_board(self, name: str) -> Board:
        """Create a new board and return it."""
        raise NotImplementedError("Subclasses must implement create_board")

    @abstractmethod
    def add_member_to_board(self, board_id: str, member_id: str) -> bool:
        """Add an existing member to the board. Returns True on success."""
        raise NotImplementedError("Subclasses must implement add_member_to_board")

    @abstractmethod
    def get_list(self, list_id: str) -> List:
        """Return a single list by its ID."""
        raise NotImplementedError("Subclasses must implement get_list")

    @abstractmethod
    def get_lists(self, board_id: str) -> Iterator[List]:
        """Return an iterator of lists on the board."""
        raise NotImplementedError("Subclasses must implement get_lists")

    @abstractmethod
    def get_issues_in_list(
        self, list_id: str, max_issues: int = 100
    ) -> Iterator[Issue]:
        """Return an iterator of issues in the given list."""
        raise NotImplementedError("Subclasses must implement get_issues_in_list")

    @abstractmethod
    def create_list(self, board_id: str, name: str) -> List:
        """Create a new list on the board (e.g. a status column)."""
        raise NotImplementedError("Subclasses must implement create_list")

    @abstractmethod
    def update_list(self, list_id: str, name: str) -> List:
        """Update a list's name (e.g. rename a status column)."""
        raise NotImplementedError("Subclasses must implement update_list")

    @abstractmethod
    def delete_list(self, list_id: str) -> bool:
        """Delete (archive) a list. Updates available statuses on the board."""
        raise NotImplementedError("Subclasses must implement delete_list")

    @abstractmethod
    def get_members_on_issue(self, issue_id: str) -> list[Member]:
        """Return members assigned to the issue."""
        raise NotImplementedError("Subclasses must implement get_members_on_issue")

    @abstractmethod
    def assign_issue(self, issue_id: str, member_id: str) -> bool:
        """Assign a member to an issue."""
        raise NotImplementedError("Subclasses must implement assign_issue")

    @abstractmethod
    def create_issue(
        self,
        title: str,
        list_id: str,
        *,
        description: str | None = None,
    ) -> Issue:
        """Create a new issue in the given list."""
        raise NotImplementedError("Subclasses must implement create_issue")


def get_client(*, interactive: bool = False) -> Client:
    """Return an instance of the concrete implementation of an issue tracker client."""
    raise NotImplementedError("Subclasses must implement get_client")
