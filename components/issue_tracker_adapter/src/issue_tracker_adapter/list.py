"""Adapter implementation of the List contract."""

from issue_tracker_client_api.list import List as ListContract
from issue_tracker_service_client.models.list_response import ListResponse


class ServiceList(ListContract):
    """List backed by a service ListResponse."""

    def __init__(self, *, id: str, name: str, board_id: str) -> None:
        self._id = id
        self._name = name
        self._board_id = board_id

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def board_id(self) -> str:
        return self._board_id

    @classmethod
    def from_response(cls, resp: ListResponse) -> "ServiceList":
        """Build from the auto-generated ListResponse."""
        return cls(id=resp.id, name=resp.name, board_id=resp.board_id)
