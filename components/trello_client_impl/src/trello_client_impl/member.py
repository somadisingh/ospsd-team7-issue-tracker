"""Implementation of the Member contract."""

from typing import TypedDict, TypeGuard

from issue_tracker_client_api import Member


class _TrelloMemberResponse(TypedDict, total=False):
    id: str
    username: str | None
    confirmed: bool | None
    url: str | None


def _is_trello_member_response(obj: object) -> TypeGuard[_TrelloMemberResponse]:
    """Type guard: narrow dict from API to Trello member response (id, username, confirmed)."""
    return (
        isinstance(obj, dict)
        and "id" in obj
        and "username" in obj
        and "confirmed" in obj
    )


class TrelloMember(Member):
    """Concrete Member built from API response.

    'confirmed' (email verified) maps to is_board_member.
    """

    def __init__(
        self,
        *,
        id: str,
        username: str | None = None,
        is_board_member: bool | None = None,
    ) -> None:
        self._id = id
        self._username = username
        self._is_board_member = is_board_member

    @property
    def id(self) -> str:
        return self._id

    @property
    def username(self) -> str | None:
        return self._username

    @property
    def is_board_member(self) -> bool | None:
        return self._is_board_member

    @classmethod
    def from_api(cls, member: _TrelloMemberResponse) -> "TrelloMember":
        """Build from API member object."""
        confirmed = member.get("confirmed") if "confirmed" in member else None
        return cls(
            id=member["id"],
            username=member.get("username"),
            is_board_member=confirmed,
        )
