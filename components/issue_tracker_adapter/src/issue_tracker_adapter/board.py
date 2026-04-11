"""Adapter implementation of the Board contract."""

from issue_tracker_client_api.board import Board
from issue_tracker_service_client.models.board_response import BoardResponse


class ServiceBoard(Board):  # type: ignore[misc]
    """Board backed by a service BoardResponse."""

    def __init__(self, *, id: str, board_name: str) -> None:
        self._id = id
        self._board_name = board_name

    @property
    def id(self) -> str:
        return self._id

    @property
    def board_name(self) -> str:
        return self._board_name

    @classmethod
    def from_response(cls, resp: BoardResponse) -> "ServiceBoard":
        """Build from the auto-generated BoardResponse."""
        return cls(id=resp.id, board_name=resp.board_name)
