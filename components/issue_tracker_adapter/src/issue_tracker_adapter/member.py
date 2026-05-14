"""Adapter implementation of the Member contract."""

from issue_tracker_client_api.member import Member
from issue_tracker_service_client.models.member_response import MemberResponse


class ServiceMember(Member):
    """Member backed by a service MemberResponse."""

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
    def from_response(cls, resp: MemberResponse) -> "ServiceMember":
        """Build from the auto-generated MemberResponse."""
        return cls(id=resp.id, username=resp.username)
