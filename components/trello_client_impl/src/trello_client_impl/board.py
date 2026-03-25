"""Implementation of the Board contract."""

from typing import TypedDict, TypeGuard

from issue_tracker_client_api import Board


class _TrelloBoardResponse(TypedDict, total=False):
    id: str
    name: str
    url: str


def _is_trello_board_response(obj: object) -> TypeGuard[_TrelloBoardResponse]:
    """Type guard: narrow dict from API to Trello board response shape (id, name)."""
    return isinstance(obj, dict) and "id" in obj and "name" in obj


class TrelloBoard(Board):
    """Concrete Board built for Board API response."""

    def __init__(
        self,
        *,
        id: str,
        name: str,
    ) -> None:
        self._id = id
        self._name = name

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def from_api(cls, board: _TrelloBoardResponse) -> "TrelloBoard":
        """Build Board from API board object."""
        return cls(
            id=board["id"],
            name=board.get("name", ""),
        )
