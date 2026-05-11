"""Client implementation.

Concrete implementation of the issue tracker API using the Trello REST API.
See: https://developer.atlassian.com/cloud/trello/rest/api-group-cards/

Trello lists are mapped to issue statuses internally.  Each board has
lists whose names are matched (case-insensitive) to ``Status`` values:
  * "To Do" / "Backlog" → ``Status.TO_DO``
  * "In Progress" / "Doing" → ``Status.IN_PROGRESS``
  * "Done" / "Completed" → ``Status.COMPLETED``
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import issue_tracker_client_api

if TYPE_CHECKING:
    from collections.abc import Iterator
import requests
from api.issue import Status
from issue_tracker_client_api import Board, Client, Issue, List, Member
from issue_tracker_client_api.exceptions import (
    AuthenticationError,
    IssueTrackerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from requests_oauthlib import OAuth1, OAuth1Session  # type: ignore[import-untyped]

from .board import TrelloBoard, _is_trello_board_response
from .issue import TrelloCard, _infer_status, _is_trello_card_response
from .list import TrelloList, _is_trello_list_response
from .member import TrelloMember, _is_trello_member_response

BASE_URL = "https://api.trello.com/1"
OAUTH_BASE_URL = "https://trello.com/1"


class TrelloClient(Client):
    """Implementation of the issue tracker Client for Trello.

    Credentials are injected via constructor to remain provider-agnostic.
    """

    def __init__(
        self,
        *,
        api_key: str,
        secret: str | None = None,
        token: str | None = None,
        access_token: str | None = None,
        access_token_secret: str | None = None,
        request_token_secret: str | None = None,
        interactive: bool = False,
    ) -> None:
        """Initialize TrelloClient with injected credentials.

        Args:
            api_key: Trello API key.
            secret: Trello API secret (for OAuth).
            token: Deprecated, use access_token.
            access_token: OAuth access token.
            access_token_secret: OAuth access token secret.
            request_token_secret: OAuth request token secret (for OAuth flow).
            interactive: Whether to enable interactive mode.

        """
        if not api_key:
            raise ValueError("api_key is required")
        if token and access_token:
            raise ValueError("Use access_token, not token")
        self.api_key = api_key
        self.secret = secret
        self._access_token = access_token or token
        self._access_token_secret = access_token_secret
        self.interactive = interactive
        self._request_token_secret = request_token_secret
        self._request_token: str | None = None

        # Fail fast when callers try OAuth1 auth with partial credentials.
        # (`token` without OAuth1 signing is still supported for key+token query auth.)
        oauth_parts = (self.secret, access_token, self._access_token_secret)
        if (access_token or self._access_token_secret) and not all(oauth_parts):
            raise ValueError(
                "Trello OAuth requires api_key, secret, access_token, and access_token_secret"
            )

        self._oauth: OAuth1 | None = None
        if all(oauth_parts):
            secret = self.secret
            access_token_value = self._access_token
            access_token_secret_value = self._access_token_secret
            if (
                secret is None
                or access_token_value is None
                or access_token_secret_value is None
            ):
                raise ValueError(
                    "Trello OAuth requires api_key, secret, access_token, and access_token_secret"
                )
            self._oauth = OAuth1(
                api_key,
                secret,
                access_token_value,
                access_token_secret_value,
            )

    # ------------------------------------------------------------------ #
    # OAuth helpers
    # ------------------------------------------------------------------ #

    def get_authorization_url(self, callback_url: str | None = None) -> str:
        if not self.secret:
            raise ValueError("Secret is required for OAuth")
        oauth = OAuth1Session(
            self.api_key, client_secret=self.secret, callback_uri=callback_url
        )
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
            raise ValueError(
                "OAuth secret and request_token_secret are required to exchange tokens."
            )
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
        self._oauth = OAuth1(
            self.api_key, self.secret, self._access_token, self._access_token_secret
        )

    @property
    def token(self) -> str | None:
        return self._access_token

    # ------------------------------------------------------------------ #
    # Low-level HTTP
    # ------------------------------------------------------------------ #

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
        try:
            resp = requests.request(
                method,
                url,
                headers={"Accept": "application/json"},
                params=req_params,
                json=json_payload,
                auth=self._oauth,
                timeout=30,
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status == 401:  # noqa: PLR2004
                raise AuthenticationError(
                    "Trello authentication failed — check API key and token"
                ) from exc
            if status == 404:  # noqa: PLR2004
                raise ResourceNotFoundError("resource", path) from exc
            if status >= 500:  # noqa: PLR2004
                raise ServiceUnavailableError(
                    f"Trello API returned server error {status}"
                ) from exc
            raise IssueTrackerError(
                f"Trello API request failed with status {status}"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ServiceUnavailableError(
                f"Could not connect to Trello API: {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ServiceUnavailableError(
                f"Trello API request timed out: {exc}"
            ) from exc
        return resp.json() if resp.content else None

    # ------------------------------------------------------------------ #
    # Internal: list ↔ status helpers
    # ------------------------------------------------------------------ #

    def _get_lists_raw(self, board_id: str) -> list[dict[str, Any]]:
        """Return raw list dicts for a board."""
        data = self._request("GET", f"/boards/{board_id}/lists")
        if not isinstance(data, list):
            return []
        return data  # type: ignore[return-value]

    def _list_id_for_status(self, board_id: str, status: Status) -> str:
        """Find the Trello list ID that corresponds to a Status value."""
        lists = self._get_lists_raw(board_id)
        for lst in lists:
            name = lst.get("name", "")
            if _infer_status(name) == status:
                return str(lst["id"])
        if lists:
            return str(lists[0]["id"])
        raise IssueTrackerError(
            f"Board {board_id} has no lists — cannot map status {status.value}"
        )

    def _list_name_by_id(self, list_id: str) -> str:
        """Return the name of a list by its ID."""
        data = self._request("GET", f"/lists/{list_id}")
        if isinstance(data, dict):
            return str(data.get("name", ""))
        return ""

    # ------------------------------------------------------------------ #
    # Board operations  (shared API)
    # ------------------------------------------------------------------ #

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
        data = self._request("POST", "/boards", params={"name": name})
        if not _is_trello_board_response(data):
            raise TypeError("Expected board response with id from boards API")
        return TrelloBoard.from_api(data)

    def update_board(
        self,
        board_id: str,
        name: str | None = None,
    ) -> Board:
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        data = self._request("PUT", f"/boards/{board_id}", json_payload=payload)
        if not _is_trello_board_response(data):
            raise TypeError("Expected board response with id from boards API")
        return TrelloBoard.from_api(data)

    def delete_board(self, board_id: str) -> bool:
        self._request("DELETE", f"/boards/{board_id}")
        return True

    # ------------------------------------------------------------------ #
    # Issue operations  (shared API)
    # ------------------------------------------------------------------ #

    def get_issue(self, issue_id: str) -> Issue:
        data = self._request("GET", f"/cards/{issue_id}")
        if not _is_trello_card_response(data):
            raise TypeError("Expected card response with id from cards API")
        list_id = data.get("idList", "")
        list_name = self._list_name_by_id(str(list_id)) if list_id else ""
        return TrelloCard.from_api(data, list_name=list_name)

    def get_issues(self, board_id: str) -> Iterator[Issue]:
        lists = self._get_lists_raw(board_id)
        for lst in lists:
            list_name = lst.get("name", "")
            cards_data = self._request("GET", f"/lists/{lst['id']}/cards")
            if not isinstance(cards_data, list):
                continue
            for card in cards_data:
                if _is_trello_card_response(card):
                    yield TrelloCard.from_api(card, list_name=list_name)

    def create_issue(
        self,
        title: str,
        board_id: str,
        desc: str | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        status: Status = Status.TO_DO,
    ) -> Issue:
        list_id = self._list_id_for_status(board_id, status)
        params: dict[str, str] = {"name": title, "idList": list_id}
        if desc is not None:
            params["desc"] = desc
        if members:
            params["idMembers"] = ",".join(members)
        if due_date is not None:
            params["due"] = due_date
        data = self._request("POST", "/cards", params=params)
        if not _is_trello_card_response(data):
            raise TypeError("Expected card response with id from cards API")
        list_name = self._list_name_by_id(list_id)
        return TrelloCard.from_api(data, list_name=list_name)

    def update_issue(
        self,
        issue_id: str,
        title: str | None = None,
        desc: str | None = None,
        members: list[str] | None = None,
        due_date: str | None = None,
        status: Status | None = None,
        board_id: str | None = None,
    ) -> Issue:
        payload: dict[str, Any] = {}
        if title is not None:
            payload["name"] = title
        if desc is not None:
            payload["desc"] = desc
        if members is not None:
            payload["idMembers"] = members
        if due_date is not None:
            payload["due"] = due_date
        if status is not None and board_id is not None:
            list_id = self._list_id_for_status(board_id, status)
            payload["idList"] = list_id
        elif status is not None:
            card_data = self._request("GET", f"/cards/{issue_id}")
            if isinstance(card_data, dict):
                bid = str(card_data.get("idBoard", ""))
                if bid:
                    list_id = self._list_id_for_status(bid, status)
                    payload["idList"] = list_id

        data = self._request("PUT", f"/cards/{issue_id}", json_payload=payload)
        if not _is_trello_card_response(data):
            raise TypeError("Expected card response with id from cards API")
        list_id_val = data.get("idList", "")
        list_name = self._list_name_by_id(str(list_id_val)) if list_id_val else ""
        return TrelloCard.from_api(data, list_name=list_name)

    def delete_issue(self, issue_id: str) -> bool:
        self._request("PUT", f"/cards/{issue_id}", json_payload={"closed": True})
        self._request("DELETE", f"/cards/{issue_id}")
        return True

    # ------------------------------------------------------------------ #
    # Internal List operations
    # ------------------------------------------------------------------ #

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

    def get_issues_in_list(
        self, list_id: str, max_issues: int = 100
    ) -> Iterator[Issue]:
        data = self._request("GET", f"/lists/{list_id}/cards")
        if not isinstance(data, list):
            return
        list_name = self._list_name_by_id(list_id)
        count = 0
        for issue in data:
            if count >= max_issues:
                break
            if _is_trello_card_response(issue):
                yield TrelloCard.from_api(issue, list_name=list_name)
                count += 1

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

    # ------------------------------------------------------------------ #
    # Internal Member operations
    # ------------------------------------------------------------------ #

    def add_member_to_board(self, board_id: str, member_id: str) -> bool:
        self._request(
            "PUT",
            f"/boards/{board_id}/members/{member_id}",
            json_payload={"type": "normal"},
        )
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


def get_client_impl(**kwargs: Any) -> Client:  # noqa: ANN401
    """Return an instance of the Trello client.

    Args:
        **kwargs: Configuration dictionary. Must contain:
            - api_key: Trello API key
            - token: Trello token
            - secret: Trello API secret (for OAuth)
            - request_token_secret: Trello request token secret (for OAuth)
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
        interactive=kwargs.get("interactive", False),
    )


def register() -> None:
    """Register the Trello client factory with the issue tracker client API."""
    issue_tracker_client_api.get_client = get_client_impl
