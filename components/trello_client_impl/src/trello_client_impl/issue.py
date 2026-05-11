"""Implementation of the Issue contract for Trello cards."""

import logging
from typing import TypedDict, TypeGuard

from api.issue import Status
from issue_tracker_client_api import Issue

logger = logging.getLogger(__name__)


class _TrelloCardResponse(TypedDict, total=False):
    id: str
    name: str
    desc: str
    idMembers: list[str]
    due: str | None
    dueComplete: bool
    idBoard: str
    idList: str


def _is_trello_card_response(obj: object) -> TypeGuard[_TrelloCardResponse]:
    """Type guard: narrow dict from API to Trello card response shape (requires id)."""
    return isinstance(obj, dict) and "id" in obj


# Well-known list name patterns mapped to Status values
_STATUS_PATTERNS: dict[str, Status] = {
    "to do": Status.TO_DO,
    "todo": Status.TO_DO,
    "backlog": Status.TO_DO,
    "in progress": Status.IN_PROGRESS,
    "doing": Status.IN_PROGRESS,
    "done": Status.COMPLETED,
    "complete": Status.COMPLETED,
    "completed": Status.COMPLETED,
}
_warned_unknown_status_lists: set[str] = set()


def _infer_status(list_name: str) -> Status:
    """Best-effort mapping from a Trello list name to a Status value."""
    normalised = list_name.strip().lower()
    for pattern, status in _STATUS_PATTERNS.items():
        if pattern in normalised:
            return status
    if normalised and normalised not in _warned_unknown_status_lists:
        logger.warning(
            "Unknown Trello list name '%s'; defaulting status to %s",
            list_name,
            Status.TO_DO.value,
        )
        _warned_unknown_status_lists.add(normalised)
    return Status.TO_DO


class TrelloCard(Issue):  # type: ignore[misc]
    """Concrete Issue built from a Trello card API response."""

    def __init__(
        self,
        *,
        id: str,
        title: str = "",
        desc: str = "",
        members: list[str] | None = None,
        due_date: str | None = None,
        status: Status = Status.TO_DO,
        board_id: str = "",
    ) -> None:
        self._id = id
        self._title = title
        self._desc = desc
        self._members = members
        self._due_date = due_date
        self._status = status
        self._board_id = board_id

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def desc(self) -> str:
        return self._desc

    @property
    def members(self) -> list[str] | None:
        return self._members

    @property
    def due_date(self) -> str | None:
        return self._due_date

    @property
    def status(self) -> Status:
        return self._status

    @property
    def board_id(self) -> str:
        return self._board_id

    @classmethod
    def from_api(
        cls,
        card: _TrelloCardResponse,
        *,
        list_name: str = "",
    ) -> "TrelloCard":
        """Build from Trello API card response.

        Args:
            card: Raw Trello card JSON.
            list_name: Name of the list the card belongs to, used for status inference.

        """
        return cls(
            id=card["id"],
            title=card.get("name", ""),
            desc=card.get("desc", ""),
            members=card.get("idMembers") or None,
            due_date=card.get("due"),
            status=_infer_status(list_name) if list_name else Status.TO_DO,
            board_id=card.get("idBoard", ""),
        )
