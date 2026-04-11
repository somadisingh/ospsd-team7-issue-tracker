"""Adapter implementation of the Issue contract."""

from api.issue import Status
from issue_tracker_client_api.issue import Issue
from issue_tracker_service_client.models.issue_response import IssueResponse
from issue_tracker_service_client.types import Unset


class ServiceIssue(Issue):  # type: ignore[misc]
    """Issue backed by a service IssueResponse."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        desc: str,
        members: list[str] | None,
        due_date: str | None,
        status: Status,
        board_id: str,
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
    def from_response(cls, resp: IssueResponse) -> "ServiceIssue":
        """Build from the auto-generated IssueResponse."""
        members = resp.members if not isinstance(resp.members, Unset) else None
        due_date = resp.due_date if not isinstance(resp.due_date, Unset) else None
        return cls(
            id=resp.id,
            title=resp.title,
            desc=resp.desc,
            members=members,
            due_date=due_date,
            status=Status(resp.status),
            board_id=resp.board_id,
        )
