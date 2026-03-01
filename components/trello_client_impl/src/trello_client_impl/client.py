"""Client implementation.

Concrete implementation of the issue tracker API using the Trello REST API.
See: https://developer.atlassian.com/cloud/trello/rest/api-group-cards/
"""

from collections.abc import Iterator
from typing import Any

import issue_tracker_client_api
import requests
from issue_tracker_client_api import Board, Client, Issue, List, Member

from .board import TrelloBoard, _is_trello_board_response
from .issue import TrelloCard, _is_trello_card_response
from .list import TrelloList, _is_trello_list_response
from .member import TrelloMember, _is_trello_member_response

BASE_URL = "https://api.trello.com/1"


class TrelloClient(Client):
    """Implementation of the issue tracker Client.

    Credentials are injected via constructor to remain provider-agnostic.
    The consumer application is responsible for loading credentials from
    any source (environment, file, vault, etc.).
    """

    def __init__(
        self,
        *,
        api_key: str,
        token: str,
        board_id: str | None = None,
        status_list_ids: dict[str, str] | None = None,
        interactive: bool = False,
    ) -> None:
        """Initialize TrelloClient with injected credentials.

        Args:
            api_key: Trello API key
            token: Trello token
            board_id: Optional default board ID
            status_list_ids: Optional mapping of status name to list ID for
                update_status (e.g. {"todo": "id1", "in_progress": "id2", "complete": "id3"}).
                When set, update_status moves the issue to the list for that status.
            interactive: Whether to enable interactive mode

        """
        if not api_key or not token:
            raise ValueError("api_key and token are required")
        self.api_key = api_key
        self._token = token
        self._default_board_id = board_id
        self._status_list_ids = status_list_ids or {}
        self.interactive = interactive

    @property
    def token(self) -> str:
        return self._token

    def _query(self, **kwargs: str) -> dict[str, str]:
        return {"key": self.api_key, "token": self.token, **kwargs}

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
        req_params = {**self._query(), **(params or {})}
        resp = requests.request(
            method,
            url,
            headers={"Accept": "application/json"},
            params=req_params,
            json=json_payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def get_issue(self, issue_id: str) -> Issue:
        data = self._request("GET", f"/cards/{issue_id}")
        if not _is_trello_card_response(data):
            raise TypeError("Expected card response with id from cards API")
        return TrelloCard.from_api(data)

    def delete_issue(self, issue_id: str) -> bool:
        self._request("PUT", f"/cards/{issue_id}", json_payload={"closed": True})
        self._request("DELETE", f"/cards/{issue_id}")
        return True

    def update_status(self, issue_id: str, status: str) -> bool:
        list_id = self._status_list_ids.get(status)
        if list_id is not None:
            payload: dict[str, Any] = {"idList": list_id}
            # Future: when status == "complete" (done list), set dueComplete=True so is_complete is true
            self._request("PUT", f"/cards/{issue_id}", json_payload=payload)
        return True

    def get_board(self, board_id: str) -> Board:
        data = self._request("GET", f"/boards/{board_id}")
        if not _is_trello_board_response(data):
            raise TypeError("Expected board response with id from boards API")
        return TrelloBoard.from_api(data)

    def get_boards(self) -> Iterator[Board]:
        data = self._request("GET", "/members/me/boards")
        if not isinstance(data, list):
            return
        for board in data:
            if _is_trello_board_response(board):
                yield TrelloBoard.from_api(board)

    def create_board(self, name: str) -> Board:
        """Create a board (POST /boards)."""
        data = self._request("POST", "/boards", params={"name": name})
        if not _is_trello_board_response(data):
            raise TypeError("Expected board response with id from boards API")
        return TrelloBoard.from_api(data)

    def add_member_to_board(self, board_id: str, member_id: str) -> bool:
        """Add a member to the board (PUT /boards/{id}/members/{idMember})."""
        self._request(
            "PUT",
            f"/boards/{board_id}/members/{member_id}",
            params={"type": "normal"},
        )
        return True

    def get_issues_in_list(
        self, list_id: str, max_issues: int = 100
    ) -> Iterator[Issue]:
        """Return issues in the list (GET /lists/{id}/cards)."""
        data = self._request("GET", f"/lists/{list_id}/cards")
        if not isinstance(data, list):
            return
        for count, issue in enumerate(data):
            if count >= max_issues:
                break
            if _is_trello_card_response(issue):
                yield TrelloCard.from_api(issue)

    def get_list(self, list_id: str) -> List:
        data = self._request("GET", f"/lists/{list_id}")
        if not _is_trello_list_response(data):
            raise TypeError("Expected list response with id from lists API")
        return TrelloList.from_api(data)

    def get_lists(self, board_id: str) -> Iterator[List]:
        data = self._request("GET", f"/boards/{board_id}/lists")
        if not isinstance(data, list):
            return
        for list_obj in data:
            if _is_trello_list_response(list_obj):
                yield TrelloList.from_api(list_obj)

    def create_list(self, board_id: str, name: str) -> List:
        data = self._request(
            "POST",
            "/lists",
            params={"idBoard": board_id, "name": name},
        )
        if not _is_trello_list_response(data):
            raise TypeError("Expected list response with id from lists API")
        return TrelloList.from_api(data)

    def update_list(self, list_id: str, name: str) -> List:
        data = self._request(
            "PUT",
            f"/lists/{list_id}",
            json_payload={"name": name},
        )
        if not _is_trello_list_response(data):
            raise TypeError("Expected list response with id from lists API")
        return TrelloList.from_api(data)

    def delete_list(self, list_id: str) -> bool:
        """Archive the list (Trello does not permanently delete lists)."""
        self._request("PUT", f"/lists/{list_id}", json_payload={"closed": True})
        return True

    def get_members_on_issue(self, issue_id: str) -> list[Member]:
        data = self._request("GET", f"/cards/{issue_id}/members")
        if not isinstance(data, list):
            return []
        return [TrelloMember.from_api(m) for m in data if _is_trello_member_response(m)]

    def assign_issue(self, issue_id: str, member_id: str) -> bool:
        self._request(
            "POST",
            f"/cards/{issue_id}/idMembers",
            params={"idMember": member_id},
        )
        return True

    def create_issue(
        self,
        title: str,
        list_id: str,
        *,
        description: str | None = None,
    ) -> Issue:
        params: dict[str, str] = {"name": title, "idList": list_id}
        if description is not None:
            params["desc"] = description
        data = self._request("POST", "/cards", params=params)
        if not _is_trello_card_response(data):
            raise TypeError("Expected card response with id from cards API")
        return TrelloCard.from_api(data)


def get_client_impl(**kwargs: Any) -> Client:  # noqa: ANN401
    """Return an instance of the Trello client.

    Extracts Trello-specific credentials from generic kwargs provided by consumer.

    Args:
        **kwargs: Configuration dictionary. Must contain:
            - api_key: Trello API key
            - token: Trello token
            - board_id (optional): Default board ID
            - status_list_ids (optional): Map status name -> list ID for update_status
            - interactive (optional): Whether to enable interactive mode

    Returns:
        TrelloClient instance

    Raises:
        ValueError: If required credentials (api_key, token) are missing

    """
    api_key = kwargs.get("api_key")
    token = kwargs.get("token")
    if not api_key or not token:
        raise ValueError(
            "Trello requires 'api_key' and 'token' in configuration. "
            f"Got: {set(kwargs.keys())}"
        )
    return TrelloClient(
        api_key=api_key,
        token=token,
        board_id=kwargs.get("board_id"),
        status_list_ids=kwargs.get("status_list_ids"),
        interactive=kwargs.get("interactive", False),
    )


def register() -> None:
    """Register the Trello client factory with the issue tracker client API.

    This allows consumers to use:
        from issue_tracker_client_api import get_client
        client = get_client(api_key="...", token="...", board_id="...", ...)
    """
    issue_tracker_client_api.get_client = get_client_impl
