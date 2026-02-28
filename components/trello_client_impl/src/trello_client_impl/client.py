"""Client implementation.

Concrete implementation of the issue tracker API using the Trello REST API.
See: https://developer.atlassian.com/cloud/trello/rest/api-group-cards/
"""

from collections.abc import Iterator
from typing import Any, cast

import requests

import issue_tracker_client_api
from issue_tracker_client_api import Board, Client, Issue, Member

from .board import TrelloBoard, _TrelloBoardResponse
from .issue import TrelloCard, _TrelloCardResponse
from .member import TrelloMember, _TrelloMemberResponse

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
        interactive: bool = False,
    ) -> None:
        """Initialize TrelloClient with injected credentials.

        Args:
            api_key: Trello API key
            token: Trello token
            board_id: Optional default board ID
            interactive: Whether to enable interactive mode
        """
        if not api_key or not token:
            raise ValueError("api_key and token are required")
        self.api_key = api_key
        self._token = token
        self._default_board_id = board_id
        self.interactive = interactive

    @property
    def token(self) -> str:
        return self._token

    def _query(self, **kwargs: str) -> dict[str, str]:
        return {"key": self.api_key, "token": self.token, **kwargs}

    def _get(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any] | list[Any]:
        url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
        resp = requests.request(
            "GET",
            url,
            headers={"Accept": "application/json"},
            params=params or self._query(),
            timeout=30,
        )
        resp.raise_for_status()
        result: dict[str, Any] | list[Any] = resp.json()
        return result

    def _delete(self, path: str) -> None:
        url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
        resp = requests.request(
            "DELETE",
            url,
            headers={"Accept": "application/json"},
            params=self._query(),
            timeout=30,
        )
        resp.raise_for_status()

    def _put(self, path: str, payload: dict[str, Any] | None = None) -> None:
        url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
        resp = requests.request(
            "PUT",
            url,
            headers={"Accept": "application/json"},
            params=self._query(),
            json=payload or {},
            timeout=30,
        )
        resp.raise_for_status()

    def _post(self, path: str, params: dict[str, str] | None = None) -> None:
        url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
        resp = requests.request(
            "POST",
            url,
            headers={"Accept": "application/json"},
            params={**self._query(), **(params or {})},
            timeout=30,
        )
        resp.raise_for_status()

    def get_issue(self, issue_id: str) -> Issue:
        data = self._get(f"/cards/{issue_id}")
        if not isinstance(data, dict):
            raise TypeError("Expected dict from cards API")
        return TrelloCard.from_api(cast("_TrelloCardResponse", data))

    def delete_issue(self, issue_id: str) -> bool:
        self._put(f"/cards/{issue_id}", payload={"closed": True})
        self._delete(f"/cards/{issue_id}")
        return True

    def mark_complete(self, issue_id: str) -> bool:
        self._put(f"/cards/{issue_id}", payload={"dueComplete": True})
        return True

    def update_status(self, issue_id: str, status: str) -> bool:
        if status == "complete":
            self._put(f"/cards/{issue_id}", payload={"dueComplete": True})
        elif status == "in_progress":
            self._put(f"/cards/{issue_id}", payload={"dueComplete": False})
        return True

    def get_issues(self, max_issues: int = 10) -> Iterator[Issue]:
        board_id = self._default_board_id
        if not board_id:
            boards = self._get("/members/me/boards")
            if not isinstance(boards, list) or not boards:
                return
            first: dict[str, Any] = boards[0]
            board_id = first["id"]
        data = self._get(f"/boards/{board_id}/cards")
        if not isinstance(data, list):
            return
        for count, card in enumerate(data):
            if count >= max_issues:
                break
            if isinstance(card, dict):
                yield TrelloCard.from_api(cast("_TrelloCardResponse", card))

    def get_board(self, board_id: str) -> Board:
        data = self._get(f"/boards/{board_id}")
        if not isinstance(data, dict):
            raise TypeError("Expected dict from boards API")
        return TrelloBoard.from_api(cast("_TrelloBoardResponse", data))

    def get_boards(self) -> Iterator[Board]:
        data = self._get("/members/me/boards")
        if not isinstance(data, list):
            return
        for board in data:
            if isinstance(board, dict):
                yield TrelloBoard.from_api(cast("_TrelloBoardResponse", board))

    def get_members_on_card(self, issue_id: str) -> list[Member]:
        data = self._get(f"/cards/{issue_id}/members")
        if not isinstance(data, list):
            return []
        return [
            TrelloMember.from_api(cast("_TrelloMemberResponse", m))
            for m in data
            if isinstance(m, dict)
        ]

    def assign_issue(self, issue_id: str, member_id: str) -> bool:
        self._post(f"/cards/{issue_id}/idMembers", params={"idMember": member_id})
        return True


def get_client_impl(**kwargs: Any) -> Client:
    """Return an instance of the Trello client.

    Extracts Trello-specific credentials from generic kwargs provided by consumer.

    Args:
        **kwargs: Configuration dictionary. Must contain:
            - api_key: Trello API key
            - token: Trello token
            - board_id (optional): Default board ID
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
        interactive=kwargs.get("interactive", False),
    )


def register() -> None:
    """Register the Trello client factory with the issue tracker client API.

    This allows consumers to use:
        from issue_tracker_client_api import get_client
        client = get_client(api_key="...", token="...", board_id="...", ...)
    """
    issue_tracker_client_api.get_client = get_client_impl