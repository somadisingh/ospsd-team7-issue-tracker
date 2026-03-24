"""Client implementation.

Concrete implementation of the issue tracker API using the Trello REST API.
See: https://developer.atlassian.com/cloud/trello/rest/api-group-cards/
"""

from collections.abc import Iterator
from typing import Any

import issue_tracker_client_api
import requests
from issue_tracker_client_api import Board, Client, Issue, List, Member
from requests_oauthlib import OAuth1, OAuth1Session

from .board import TrelloBoard, _is_trello_board_response
from .issue import TrelloCard, _is_trello_card_response
from .list import TrelloList, _is_trello_list_response
from .member import TrelloMember, _is_trello_member_response

BASE_URL = "https://api.trello.com/1"
OAUTH_BASE_URL = "https://trello.com/1"  # OAuth endpoints have separate base URL


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
        secret: str | None = None,
        token: str | None = None,  # Deprecated, use access_token
        access_token: str | None = None,
        access_token_secret: str | None = None,
        request_token_secret: str | None = None,
        board_id: str | None = None,
        status_list_ids: dict[str, str] | None = None,
        interactive: bool = False,
    ) -> None:
        """Initialize TrelloClient with injected credentials.

        Args:
            api_key: Trello API key
            secret: Trello API secret (for OAuth)
            token: Deprecated, use access_token
            access_token: OAuth access token
            access_token_secret: OAuth access token secret
            board_id: Optional default board ID
            status_list_ids: Optional mapping of status name to list ID for
                update_status (e.g. {"todo": "id1", "in_progress": "id2", "complete": "id3"}).
                When set, update_status moves the issue to the list for that status.
            request_token_secret: OAuth request token secret (for OAuth flow).
            interactive: Whether to enable interactive mode

        """
        if not api_key:
            raise ValueError("api_key is required")
        if token and access_token:
            raise ValueError("Use access_token, not token")
        self.api_key = api_key
        self.secret = secret
        self._access_token = access_token or token
        self._access_token_secret = access_token_secret
        self._default_board_id = board_id
        self._status_list_ids = status_list_ids or {}
        self.interactive = interactive
        # state var for OAuth flow
        self._request_token_secret = request_token_secret
        self._request_token = None

        self._oauth = None
        if self._access_token and self._access_token_secret and secret:
            self._oauth = OAuth1(api_key, secret, self._access_token, self._access_token_secret)
        elif self._access_token and not self._access_token_secret:
            # Old way, no OAuth
            pass

    def get_authorization_url(self, callback_url: str | None = None) -> str:
        if not self.secret:
            raise ValueError("Secret is required for OAuth")
        oauth = OAuth1Session(self.api_key, client_secret=self.secret, callback_uri=callback_url)
        request_token_url = f"{OAUTH_BASE_URL}/OAuthGetRequestToken"
        fetch_response = oauth.fetch_request_token(request_token_url)
        self._request_token = fetch_response.get("oauth_token")
        self._request_token_secret = fetch_response.get("oauth_token_secret")
        if not self._request_token or not self._request_token_secret:
            msg = "Trello OAuth did not return request token and secret"
            raise ValueError(msg)
        return f"{OAUTH_BASE_URL}/OAuthAuthorizeToken?oauth_token={self._request_token}"

    @property
    def request_token_secret(self) -> str | None:
        return self._request_token_secret

    @property
    def access_token_secret(self) -> str | None:
        return self._access_token_secret

    def exchange_request_token(self, oauth_token: str, oauth_verifier: str) -> None:
        if not self.secret or not self._request_token_secret:
            raise ValueError("OAuth secret and request_token_secret are required to exchange tokens.")
        if self._request_token and self._request_token != oauth_token:
            raise ValueError("OAuth token mismatch for current OAuth session.")

        oauth = OAuth1Session(
            self.api_key,
            client_secret=self.secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=self._request_token_secret,
            verifier=oauth_verifier,
        )
        access_token_url = f"{OAUTH_BASE_URL}/OAuthGetAccessToken"
        oauth_tokens = oauth.fetch_access_token(access_token_url)
        self._access_token = oauth_tokens.get("oauth_token")
        self._access_token_secret = oauth_tokens.get("oauth_token_secret")
        if not self._access_token or not self._access_token_secret:
            raise ValueError("Trello OAuth did not return access token and secret")

        self._request_token = oauth_token
        self._oauth = OAuth1(self.api_key, self.secret, self._access_token, self._access_token_secret)

    @property
    def token(self) -> str | None:
        return self._access_token

    def _query(self, **kwargs: str) -> dict[str, str]:
        if self._oauth:
            return kwargs
        if self._access_token:
            return {"key": self.api_key, "token": self._access_token, **kwargs}
        return {"key": self.api_key, **kwargs}

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
            auth=self._oauth,
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
            - secret: Trello API secret (for OAuth)
            - request_token_secret: Trello request token secret (for OAuth)
            - board_id (optional): Default board ID
            - status_list_ids (optional): Map status name -> list ID for update_status
            - interactive (optional): Whether to enable interactive mode

    Returns:
        TrelloClient instance

    Raises:
        ValueError: If required credentials (api_key) is missing

    """
    api_key = kwargs.get("api_key")
    token = kwargs.get("token")
    secret = kwargs.get("secret")
    request_token_secret = kwargs.get("request_token_secret")
    if not api_key:
        raise ValueError(
            "Issue Tracker requires 'api_key' in configuration. "
            f"Got: {set(kwargs.keys())}"
        )
    if not token and not secret:
        raise ValueError(
            "Issue Tracker requires either 'token' (for authenticated requests) "
            "or 'secret' (to initiate OAuth flow) in configuration."
        )
    return TrelloClient(
        api_key=api_key,
        token=token,
        secret=secret,
        request_token_secret=request_token_secret,
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
