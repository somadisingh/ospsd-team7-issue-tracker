"""List contract - Core list representation."""

from abc import ABC, abstractmethod


class List(ABC):
    """Abstract base class representing a list on a board."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the list."""
        raise NotImplementedError("Subclasses must implement id")

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the list."""
        raise NotImplementedError("Subclasses must implement name")

    @property
    @abstractmethod
    def board_id(self) -> str:
        """Return the ID of the board this list belongs to."""
        raise NotImplementedError("Subclasses must implement board_id")


def get_list(list_id: str) -> List:
    """Return a list by its ID."""
    raise NotImplementedError("Subclasses must implement get_list")
