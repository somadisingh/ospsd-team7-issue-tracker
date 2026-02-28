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
    def get_issues(self, max_issues: int = 10) -> Iterator[Issue]:
        """Return an iterator of issues, up to max_issues."""
        raise NotImplementedError("Subclasses must implement get_issues")

    @abstractmethod
    def get_board(self, board_id: str) -> Board:
        """Return a single board by its ID."""
        raise NotImplementedError("Subclasses must implement get_board")

    @abstractmethod
    def get_boards(self) -> Iterator[Board]:
        """Return an iterator of boards for the authenticated user."""
        raise NotImplementedError("Subclasses must implement get_boards")

    @abstractmethod
    def get_lists(self, board_id: str) -> Iterator[List]:
        """Return an iterator of lists on the board."""
        raise NotImplementedError("Subclasses must implement get_lists")

    @abstractmethod
    def get_members_on_card(self, issue_id: str) -> list[Member]:
        """Return members assigned to the issue."""
        raise NotImplementedError("Subclasses must implement get_members_on_card")

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
