"""Adapter implementation of the Board contract."""

from issue_tracker_client_api.board import Board
from issue_tracker_service_client.models.board_response import BoardResponse


class ServiceBoard(Board):
    """Board backed by a service BoardResponse."""

    def __init__(self, *, id: str, name: str) -> None:
        self._id = id
        self._name = name

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def from_response(cls, resp: BoardResponse) -> "ServiceBoard":
        """Build from the auto-generated BoardResponse."""
        return cls(id=resp.id, name=resp.name)
