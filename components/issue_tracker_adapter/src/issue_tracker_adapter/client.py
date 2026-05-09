"""Service client adapter.

Implements the abstract Client API by delegating to the auto-generated
HTTP client produced by openapi-python-client.  This achieves location
transparency: consumers program against the same interface regardless of
whether the implementation talks to Trello directly or goes through the
deployed FastAPI service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
from issue_tracker_service_client import errors as api_errors
from issue_tracker_service_client.models.http_validation_error import (
    HTTPValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

import issue_tracker_client_api
from issue_tracker_client_api import Board, Client, Issue, List, Member
from issue_tracker_service_client.api.default import (
    add_member_to_board_boards_board_id_members_post as add_member_api,
)
from issue_tracker_service_client.api.default import (
    assign_issue_issues_issue_id_assign_post as assign_api,
)
from issue_tracker_service_client.api.default import (
    create_board_boards_post as create_board_api,
)
from issue_tracker_service_client.api.default import (
    create_issue_issues_post as create_issue_api,
)
from issue_tracker_service_client.api.default import (
    create_list_lists_post as create_list_api,
)
from issue_tracker_service_client.api.default import (
    delete_issue_issues_issue_id_delete as delete_issue_api,
)
from issue_tracker_service_client.api.default import (
    delete_list_lists_list_id_delete as delete_list_api,
)
from issue_tracker_service_client.api.default import (
    get_board_boards_board_id_get as get_board_api,
)
from issue_tracker_service_client.api.default import (
    get_issue_issues_issue_id_get as get_issue_api,
)
from issue_tracker_service_client.api.default import (
    get_issue_members_issues_issue_id_members_get as get_members_api,
)
from issue_tracker_service_client.api.default import (
    get_issues_in_list_lists_list_id_issues_get as get_issues_api,
)
from issue_tracker_service_client.api.default import (
    get_list_lists_list_id_get as get_list_api,
)
from issue_tracker_service_client.api.default import (
    get_lists_boards_board_id_lists_get as get_lists_api,
)
from issue_tracker_service_client.api.default import (
    list_boards_boards_get as list_boards_api,
)
from issue_tracker_service_client.api.default import (
    update_issue_status_issues_issue_id_status_put as update_status_api,
)
from issue_tracker_service_client.api.default import (
    update_list_lists_list_id_put as update_list_api,
)
from issue_tracker_service_client.client import Client as HttpClient
from issue_tracker_service_client.models.add_member_to_board_request import (
    AddMemberToBoardRequest,
)
from issue_tracker_service_client.models.assign_issue_request import (
    AssignIssueRequest,
)
from issue_tracker_service_client.models.board_response import BoardResponse
from issue_tracker_service_client.models.create_board_request import (
    CreateBoardRequest,
)
from issue_tracker_service_client.models.create_issue_request import (
    CreateIssueRequest,
)
from issue_tracker_service_client.models.create_list_request import CreateListRequest
from issue_tracker_service_client.models.issue_response import IssueResponse
from issue_tracker_service_client.models.list_response import ListResponse
from issue_tracker_service_client.models.member_response import MemberResponse
from issue_tracker_service_client.models.update_list_request import (
    UpdateListRequest,
)
from issue_tracker_service_client.models.update_status_request import (
    UpdateStatusRequest,
)

from issue_tracker_adapter.board import ServiceBoard
from issue_tracker_adapter.issue import ServiceIssue
from issue_tracker_adapter.list import ServiceList
from issue_tracker_adapter.member import ServiceMember


class ServiceClientAdapter(Client):
    """Adapter that implements the Client ABC via the deployed service.

    Uses the auto-generated HTTP client (Step D) to call the FastAPI
    service and converts responses into abstract domain objects.
    """

    def __init__(self, *, base_url: str, session_token: str) -> None:
        """Initialize the adapter.

        Args:
            base_url: Base URL of the deployed service
                (e.g. ``https://issue-tracker-service-PROJECT_NUMBER.region.run.app`` from ``terraform output -raw service_url``).
            session_token: Session token obtained from the ``/auth/callback``
                endpoint after completing the OAuth flow.

        """
        self._session_token = session_token
        self._http_client = HttpClient(base_url=base_url)

    def _ensure_board(self, result: object) -> BoardResponse:
        if not isinstance(result, BoardResponse):
            msg = f"Expected BoardResponse, got {type(result)}"
            raise TypeError(msg)
        return result

    def _ensure_issue(self, result: object) -> IssueResponse:
        if not isinstance(result, IssueResponse):
            msg = f"Expected IssueResponse, got {type(result)}"
            raise TypeError(msg)
        return result

    def _ensure_list(self, result: object) -> ListResponse:
        if not isinstance(result, ListResponse):
            msg = f"Expected ListResponse, got {type(result)}"
            raise TypeError(msg)
        return result

    def _check_validation_error(self, result: object) -> None:
        """Raise ``ValueError`` when the service returns a 422 validation error."""
        if isinstance(result, HTTPValidationError):
            detail = getattr(result, "detail", None)
            if isinstance(detail, list):
                msgs = "; ".join(str(e.to_dict()) for e in detail)
            else:
                msgs = "unknown validation error"
            raise ValueError(f"Validation error from service: {msgs}")  # noqa: TRY004

    def _call_api(self, api_func: Callable[..., Any], **kwargs: Any) -> Any:  # noqa: ANN401
        """Call a generated API function, translating HTTP errors.

        Catches transport-level errors (timeouts, connection failures) and
        unexpected HTTP status codes from the generated client and re-raises
        them as standard Python exceptions.  Also detects 422 validation
        error responses and raises ``ValueError``.
        """
        try:
            result = api_func(
                client=self._http_client,
                x_session_token=self._session_token,
                **kwargs,
            )
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Request to service timed out: {exc}") from exc
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Could not connect to service: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ConnectionError(f"HTTP transport error: {exc}") from exc
        except api_errors.UnexpectedStatus as exc:
            raise RuntimeError(
                f"Service returned unexpected status {exc.status_code}"
            ) from exc
        self._check_validation_error(result)
        return result

    # ------------------------------------------------------------------
    # Board operations
    # ------------------------------------------------------------------

    def get_board(self, board_id: str) -> Board:
        result = self._call_api(get_board_api.sync, board_id=board_id)
        return ServiceBoard.from_response(self._ensure_board(result))

    def get_boards(self) -> Iterator[Board]:
        result = self._call_api(list_boards_api.sync)
        if not isinstance(result, list):
            return
        for board_resp in result:
            if isinstance(board_resp, BoardResponse):
                yield ServiceBoard.from_response(board_resp)

    def create_board(self, name: str) -> Board:
        result = self._call_api(
            create_board_api.sync,
            body=CreateBoardRequest(name=name),
        )
        return ServiceBoard.from_response(self._ensure_board(result))

    def add_member_to_board(self, board_id: str, member_id: str) -> bool:
        result = self._call_api(
            add_member_api.sync,
            board_id=board_id,
            body=AddMemberToBoardRequest(member_id=member_id),
        )
        if result is None:
            return False
        return bool(getattr(result, "additional_properties", {}).get("success", False))

    # ------------------------------------------------------------------
    # List operations
    # ------------------------------------------------------------------

    def get_list(self, list_id: str) -> List:
        result = self._call_api(get_list_api.sync, list_id=list_id)
        return ServiceList.from_response(self._ensure_list(result))

    def get_lists(self, board_id: str) -> Iterator[List]:
        result = self._call_api(get_lists_api.sync, board_id=board_id)
        if not isinstance(result, list):
            return
        for list_resp in result:
            if isinstance(list_resp, ListResponse):
                yield ServiceList.from_response(list_resp)

    def create_list(self, board_id: str, name: str) -> List:
        result = self._call_api(
            create_list_api.sync,
            body=CreateListRequest(board_id=board_id, name=name),
        )
        return ServiceList.from_response(self._ensure_list(result))

    def update_list(self, list_id: str, name: str) -> List:
        result = self._call_api(
            update_list_api.sync,
            list_id=list_id,
            body=UpdateListRequest(name=name),
        )
        return ServiceList.from_response(self._ensure_list(result))

    def delete_list(self, list_id: str) -> bool:
        result = self._call_api(delete_list_api.sync, list_id=list_id)
        if result is None:
            return False
        return bool(getattr(result, "additional_properties", {}).get("success", False))

    # ------------------------------------------------------------------
    # Issue operations
    # ------------------------------------------------------------------

    def get_issue(self, issue_id: str) -> Issue:
        result = self._call_api(get_issue_api.sync, issue_id=issue_id)
        return ServiceIssue.from_response(self._ensure_issue(result))

    def get_issues_in_list(
        self,
        list_id: str,
        max_issues: int = 100,
    ) -> Iterator[Issue]:
        result = self._call_api(
            get_issues_api.sync,
            list_id=list_id,
            max_issues=max_issues,
        )
        if not isinstance(result, list):
            return
        for issue_resp in result:
            if isinstance(issue_resp, IssueResponse):
                yield ServiceIssue.from_response(issue_resp)

    def create_issue(
        self,
        title: str,
        list_id: str,
        *,
        description: str | None = None,
    ) -> Issue:
        result = self._call_api(
            create_issue_api.sync,
            body=CreateIssueRequest(
                title=title,
                list_id=list_id,
                description=description,
            ),
        )
        return ServiceIssue.from_response(self._ensure_issue(result))

    def update_status(self, issue_id: str, status: str) -> bool:
        result = self._call_api(
            update_status_api.sync,
            issue_id=issue_id,
            body=UpdateStatusRequest(status=status),
        )
        if result is None:
            return False
        return bool(getattr(result, "additional_properties", {}).get("success", False))

    def delete_issue(self, issue_id: str) -> bool:
        result = self._call_api(delete_issue_api.sync, issue_id=issue_id)
        if result is None:
            return False
        return bool(getattr(result, "additional_properties", {}).get("success", False))

    # ------------------------------------------------------------------
    # Member operations
    # ------------------------------------------------------------------

    def get_members_on_issue(self, issue_id: str) -> list[Member]:
        result = self._call_api(get_members_api.sync, issue_id=issue_id)
        if not isinstance(result, list):
            return []
        return [
            ServiceMember.from_response(m)
            for m in result
            if isinstance(m, MemberResponse)
        ]

    def assign_issue(self, issue_id: str, member_id: str) -> bool:
        result = self._call_api(
            assign_api.sync,
            issue_id=issue_id,
            body=AssignIssueRequest(member_id=member_id),
        )
        if result is None:
            return False
        return bool(getattr(result, "additional_properties", {}).get("success", False))

    # ------------------------------------------------------------------
    # OAuth — handled by the service, not the adapter
    # ------------------------------------------------------------------

    def get_authorization_url(self, callback_url: str | None = None) -> str:
        raise NotImplementedError(
            "OAuth is handled by the service directly via /auth/login"
        )

    def exchange_request_token(
        self,
        oauth_token: str,
        oauth_verifier: str,
    ) -> None:
        raise NotImplementedError(
            "OAuth is handled by the service directly via /auth/callback"
        )


def get_client_impl(**kwargs: Any) -> Client:  # noqa: ANN401
    """Return an instance of the service client adapter.

    Args:
        **kwargs: Must contain:
            - base_url: URL of the deployed service
            - session_token: Session token from the OAuth flow

    Returns:
        ServiceClientAdapter instance

    Raises:
        ValueError: If required parameters are missing.

    """
    base_url = kwargs.get("base_url")
    session_token = kwargs.get("session_token")
    if not base_url:
        raise ValueError(
            "ServiceClientAdapter requires 'base_url' in configuration. "
            f"Got: {set(kwargs.keys())}"
        )
    if not session_token:
        raise ValueError(
            "ServiceClientAdapter requires 'session_token' in configuration. "
            f"Got: {set(kwargs.keys())}"
        )
    return ServiceClientAdapter(
        base_url=base_url,
        session_token=session_token,
    )


def register() -> None:
    """Register the service adapter with the issue tracker client API.

    After calling this, ``issue_tracker_client_api.get_client(...)`` will
    return a ``ServiceClientAdapter`` that talks to the deployed service.
    """
    issue_tracker_client_api.get_client = get_client_impl  # type: ignore[assignment]
