from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.update_issue_status_issues_issue_id_status_put_response_update_issue_status_issues_issue_id_status_put import (
    UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut,
)
from ...models.update_status_request import UpdateStatusRequest
from ...types import Response


def _get_kwargs(
    issue_id: str,
    *,
    body: UpdateStatusRequest,
    x_session_token: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Session-Token"] = x_session_token

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/issues/{issue_id}/status".format(
            issue_id=quote(str(issue_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut | None
):
    if response.status_code == 200:
        response_200 = UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut.from_dict(
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
) -> Response[
    HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut
]:
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
    body: UpdateStatusRequest,
    x_session_token: str,
) -> Response[
    HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut
]:
    """Update Issue Status

    Args:
        issue_id (str):
        x_session_token (str):
        body (UpdateStatusRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut]
    """

    kwargs = _get_kwargs(
        issue_id=issue_id,
        body=body,
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
    body: UpdateStatusRequest,
    x_session_token: str,
) -> (
    HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut | None
):
    """Update Issue Status

    Args:
        issue_id (str):
        x_session_token (str):
        body (UpdateStatusRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut
    """

    return sync_detailed(
        issue_id=issue_id,
        client=client,
        body=body,
        x_session_token=x_session_token,
    ).parsed


async def asyncio_detailed(
    issue_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateStatusRequest,
    x_session_token: str,
) -> Response[
    HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut
]:
    """Update Issue Status

    Args:
        issue_id (str):
        x_session_token (str):
        body (UpdateStatusRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut]
    """

    kwargs = _get_kwargs(
        issue_id=issue_id,
        body=body,
        x_session_token=x_session_token,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    issue_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateStatusRequest,
    x_session_token: str,
) -> (
    HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut | None
):
    """Update Issue Status

    Args:
        issue_id (str):
        x_session_token (str):
        body (UpdateStatusRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | UpdateIssueStatusIssuesIssueIdStatusPutResponseUpdateIssueStatusIssuesIssueIdStatusPut
    """

    return (
        await asyncio_detailed(
            issue_id=issue_id,
            client=client,
            body=body,
            x_session_token=x_session_token,
        )
    ).parsed
