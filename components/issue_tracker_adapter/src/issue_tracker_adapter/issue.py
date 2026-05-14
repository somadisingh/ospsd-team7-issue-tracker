"""Adapter implementation of the Issue contract."""

from issue_tracker_client_api.issue import Issue
from issue_tracker_service_client.models.issue_response import IssueResponse


class ServiceIssue(Issue):
    """Issue backed by a service IssueResponse."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        is_complete: bool,
        list_id: str,
        board_id: str | None,
    ) -> None:
        self._id = id
        self._title = title
        self._is_complete = is_complete
        self._list_id = list_id
        self._board_id = board_id

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
    def list_id(self) -> str:
        return self._list_id

    @property
    def board_id(self) -> str | None:
        return self._board_id

    @classmethod
    def from_response(cls, resp: IssueResponse) -> "ServiceIssue":
        """Build from the auto-generated IssueResponse."""
        return cls(
            id=resp.id,
            title=resp.title,
            is_complete=resp.is_complete,
            list_id=resp.list_id,
            board_id=resp.board_id,
        )
