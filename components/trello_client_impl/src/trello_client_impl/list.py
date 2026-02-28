"""Implementation of the List contract."""

from typing import TypedDict

from issue_tracker_client_api import List as ListContract


class _TrelloListResponse(TypedDict, total=False):
    id: str
    name: str
    idBoard: str
    url : str


class TrelloList(ListContract):
    """Concrete List built from Trello lists API response."""

    def __init__(self, *, id: str, name: str, board_id: str = "") -> None:
        self._id = id
        self._name = name
        self._board_id = board_id or ""

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def board_id(self) -> str:
        return self._board_id

    @classmethod
    def from_api(cls, list_obj: _TrelloListResponse) -> "TrelloList":
        """Build List from API list object."""
        return cls(
            id=list_obj["id"],
            name=list_obj.get("name", ""),
            board_id=list_obj.get("idBoard", ""),
        )
