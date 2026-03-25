"""Member contract - Core member representation."""

from abc import ABC, abstractmethod


class Member(ABC):
    """Abstract base class representing a member in the issue tracker."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the member."""
        raise NotImplementedError("Subclasses must implement id")

    @property
    @abstractmethod
    def username(self) -> str | None:
        """Return the username."""
        raise NotImplementedError("Subclasses must implement username")

    @property
    @abstractmethod
    def is_board_member(self) -> bool | None:
        """Whether the member can be assigned to issues on the board."""
        raise NotImplementedError("Subclasses must implement is_board_member")


def get_member(member_id: str) -> Member:
    """Return a member by their ID."""
    raise NotImplementedError("Subclasses must implement get_member")
