"""Issue contract - Core issue representation."""

from abc import ABC, abstractmethod


class Issue(ABC):
    """Abstract base class representing an issue in the issue tracker."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the issue."""
        raise NotImplementedError("Subclasses must implement id")

    @property
    @abstractmethod
    def title(self) -> str:
        """Return the title of the issue."""
        raise NotImplementedError("Subclasses must implement title")

    @property
    @abstractmethod
    def is_complete(self) -> bool:
        """Return whether the issue is complete."""
        raise NotImplementedError("Subclasses must implement is_complete")

    @property
    @abstractmethod
    def list_id(self) -> str:
        """Return the ID of the list this issue belongs to."""
        raise NotImplementedError("Subclasses must implement list_id")

    @property
    @abstractmethod
    def board_id(self) -> str | None:
        """Return the ID of the board this issue belongs to, or None if unknown."""
        raise NotImplementedError("Subclasses must implement board_id")


def get_issue(issue_id: str) -> Issue:
    """Return an issue by its ID.

    Args:
        issue_id: The ID of the issue to return.

    Returns:
        An instance of the Issue class with the given ID.

    """
    raise NotImplementedError("Subclasses must implement get_issue")
