"""Core issue tracker client contract.

Extends the shared vertical Client ABC with authentication methods
and internal List/Member operations specific to our team's
Trello-based implementation.  The shared interface defines the CRUD
operations that all issue-tracker verticals implement; this module
adds the auth layer and domain-specific helpers each team manages
independently.
"""

from abc import abstractmethod
from collections.abc import Iterator

from api.client import Client as SharedClient
from api.client import get_client

from issue_tracker_client_api.issue import Issue
from issue_tracker_client_api.list import List
from issue_tracker_client_api.member import Member

__all__ = ["Client", "get_client"]


class Client(SharedClient):  # type: ignore[misc]
    """Extended issue-tracker client with OAuth and internal List/Member support.

    Inherits all shared CRUD operations (Board and Issue) from the
    vertical's shared API and adds:
    * OAuth 1.0a authentication methods
    * Internal List operations (Trello lists ↔ status columns)
    * Internal Member operations (board members, issue assignment)
    """

    # ------------------------------------------------------------------ #
    # OAuth
    # ------------------------------------------------------------------ #

    @abstractmethod
    def get_authorization_url(self, callback_url: str | None = None) -> str:
        """Return the URL to authorize the application."""
        raise NotImplementedError("Subclasses must implement get_authorization_url")

    @abstractmethod
    def exchange_request_token(self, oauth_token: str, oauth_verifier: str) -> None:
        """Exchange the request token for an access token."""
        raise NotImplementedError("Subclasses must implement exchange_request_token")

    # ------------------------------------------------------------------ #
    # Internal List operations
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Internal Member operations
    # ------------------------------------------------------------------ #

    @abstractmethod
    def get_members_on_issue(self, issue_id: str) -> list[Member]:
        """Return members assigned to the issue."""
        raise NotImplementedError("Subclasses must implement get_members_on_issue")

    @abstractmethod
    def assign_issue(self, issue_id: str, member_id: str) -> bool:
        """Assign a member to an issue."""
        raise NotImplementedError("Subclasses must implement assign_issue")

    @abstractmethod
    def add_member_to_board(self, board_id: str, member_id: str) -> bool:
        """Add an existing member to the board. Returns True on success."""
        raise NotImplementedError("Subclasses must implement add_member_to_board")
