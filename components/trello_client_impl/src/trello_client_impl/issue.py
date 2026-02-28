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
    idMembers: list[str]
    url: str


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
        board_id: str | None = None,
        list_id: str,
    ) -> None:
        self._id = id
        self._title = title
        self._is_complete = is_complete
        self._desc = desc
        self._due = due
        self._board_id = board_id
        self._list_id = list_id

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def desc(self) -> str | None:
        return self._desc

    @property
    def due(self) -> str | None:
        return self._due

    @property
    def board_id(self) -> str | None:
        return self._board_id

    @property
    def list_id(self) -> str:
        return self._list_id

    @classmethod
    def from_api(cls, card: _TrelloCardResponse) -> "TrelloCard":
        """Build Card from API card object. Requires idList (every issue belongs to a list)."""
        id_list = card.get("idList")
        if not id_list:
            raise ValueError("Card response must include idList")
        return cls(
            id=card["id"],
            title=card.get("name", ""),
            desc=card.get("desc") or None,
            due=card.get("due"),
            board_id=card.get("idBoard"),
            list_id=id_list,
        )
