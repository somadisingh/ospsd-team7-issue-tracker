from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.assign_issue_issues_issue_id_assign_post_response_assign_issue_issues_issue_id_assign_post import (
    AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response


def _get_kwargs(
    issue_id: str,
    *,
    member_id: str,
    x_session_token: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Session-Token"] = x_session_token

    params: dict[str, Any] = {}

    params["member_id"] = member_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/issues/{issue_id}/assign".format(
            issue_id=quote(str(issue_id), safe=""),
        ),
        "params": params,
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    issue_id: str,
    *,
    client: AuthenticatedClient | Client,
    member_id: str,
    x_session_token: str,
) -> Response[AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError]:
    """Assign Issue

    Args:
        issue_id (str):
        member_id (str):
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        issue_id=issue_id,
        member_id=member_id,
        x_session_token=x_session_token,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    issue_id: str,
    *,
    client: AuthenticatedClient | Client,
    member_id: str,
    x_session_token: str,
) -> AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError | None:
    """Assign Issue

    Args:
        issue_id (str):
        member_id (str):
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError
    """

    return sync_detailed(
        issue_id=issue_id,
        client=client,
        member_id=member_id,
        x_session_token=x_session_token,
    ).parsed


async def asyncio_detailed(
    issue_id: str,
    *,
    client: AuthenticatedClient | Client,
    member_id: str,
    x_session_token: str,
) -> Response[AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError]:
    """Assign Issue

    Args:
        issue_id (str):
        member_id (str):
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        issue_id=issue_id,
        member_id=member_id,
        x_session_token=x_session_token,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    issue_id: str,
    *,
    client: AuthenticatedClient | Client,
    member_id: str,
    x_session_token: str,
) -> AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError | None:
    """Assign Issue

    Args:
        issue_id (str):
        member_id (str):
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AssignIssueIssuesIssueIdAssignPostResponseAssignIssueIssuesIssueIdAssignPost | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            issue_id=issue_id,
            client=client,
            member_id=member_id,
            x_session_token=x_session_token,
        )
    ).parsed
