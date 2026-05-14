from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_issue_request import CreateIssueRequest
from ...models.http_validation_error import HTTPValidationError
from ...models.issue_response import IssueResponse
from ...types import Response


def _get_kwargs(
    *,
    body: CreateIssueRequest,
    x_session_token: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Session-Token"] = x_session_token

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/issues",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | IssueResponse | None:
    if response.status_code == 200:
        response_200 = IssueResponse.from_dict(response.json())

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
) -> Response[HTTPValidationError | IssueResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateIssueRequest,
    x_session_token: str,
) -> Response[HTTPValidationError | IssueResponse]:
    """Create Issue

    Args:
        x_session_token (str):
        body (CreateIssueRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | IssueResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        x_session_token=x_session_token,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: CreateIssueRequest,
    x_session_token: str,
) -> HTTPValidationError | IssueResponse | None:
    """Create Issue

    Args:
        x_session_token (str):
        body (CreateIssueRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | IssueResponse
    """

    return sync_detailed(
        client=client,
        body=body,
        x_session_token=x_session_token,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateIssueRequest,
    x_session_token: str,
) -> Response[HTTPValidationError | IssueResponse]:
    """Create Issue

    Args:
        x_session_token (str):
        body (CreateIssueRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | IssueResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        x_session_token=x_session_token,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: CreateIssueRequest,
    x_session_token: str,
) -> HTTPValidationError | IssueResponse | None:
    """Create Issue

    Args:
        x_session_token (str):
        body (CreateIssueRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | IssueResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            x_session_token=x_session_token,
        )
    ).parsed
