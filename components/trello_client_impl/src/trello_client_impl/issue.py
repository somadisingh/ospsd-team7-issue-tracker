"""Implementation of the Issue contract."""

from typing import TypedDict, TypeGuard

from issue_tracker_client_api import Issue


class _TrelloCardResponse(TypedDict, total=False):
    id: str
    name: str
    dueComplete: bool
    idBoard: str
    idList: str


def _is_trello_card_response(obj: object) -> TypeGuard[_TrelloCardResponse]:
    """Type guard: narrow dict from API to Trello card response shape (requires id)."""
    return isinstance(obj, dict) and "id" in obj


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
        board_id: str | None = None,
        list_id: str,
    ) -> None:
        self._id = id
        self._title = title
        self._is_complete = is_complete
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
    def board_id(self) -> str | None:
        return self._board_id

    @property
    def list_id(self) -> str:
        return self._list_id

    @classmethod
    def from_api(cls, card: _TrelloCardResponse) -> "TrelloCard":
        """Build Card from API card object. Requires idList (every issue belongs to a list).

        Maps Trello dueComplete to is_complete (Issue has only is_complete; dueComplete is API-only).
        """
        id_list = card.get("idList")
        if not id_list:
            raise ValueError("Card response must include idList")
        return cls(
            id=card["id"],
            title=card.get("name", ""),
            is_complete=bool(card.get("dueComplete", False)),
            board_id=card.get("idBoard"),
            list_id=id_list,
        )
