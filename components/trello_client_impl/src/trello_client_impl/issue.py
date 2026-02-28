"""Implementation of the Issue contract."""

from typing import TypedDict

from issue_tracker_client_api import Issue


class _TrelloCardResponse(TypedDict, total=False):
    id: str
    name: str
    dueComplete: bool
    desc: str | None
    due: str | None
    idBoard: str | None
    idList: str | None


class TrelloCard(Issue):
    """Concrete Issue built from Card API response.

    Mapping dueComplete to is_complete.
    """

    def __init__(
        self,
        *,
        id: str,
        title: str = "",
        is_complete: bool = False,
        desc: str | None = None,
        due: str | None = None,
        id_board: str | None = None,
        id_list: str | None = None,
    ) -> None:
        self._id = id
        self._title = title
        self._is_complete = is_complete
        self._desc = desc
        self._due = due
        self._id_board = id_board
        self._id_list = id_list

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
    def desc(self) -> str | None:
        return self._desc

    @property
    def due(self) -> str | None:
        return self._due

    @property
    def id_board(self) -> str | None:
        return self._id_board

    @property
    def id_list(self) -> str | None:
        return self._id_list

    @classmethod
    def from_api(cls, card: _TrelloCardResponse) -> "TrelloCard":
        """Build Card from API card object."""
        due_complete = bool(card.get("dueComplete", False))
        return cls(
            id=card["id"],
            title=card.get("name", ""),
            is_complete=due_complete,
            desc=card.get("desc") or None,
            due=card.get("due"),
            id_board=card.get("idBoard"),
            id_list=card.get("idList"),
        )
