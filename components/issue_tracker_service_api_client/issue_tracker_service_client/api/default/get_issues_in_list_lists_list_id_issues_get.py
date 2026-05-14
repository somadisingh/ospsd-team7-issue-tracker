from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.issue_response import IssueResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    list_id: str,
    *,
    max_issues: int | Unset = 100,
    x_session_token: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Session-Token"] = x_session_token

    params: dict[str, Any] = {}

    params["max_issues"] = max_issues

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/lists/{list_id}/issues".format(
            list_id=quote(str(list_id), safe=""),
        ),
        "params": params,
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | list[IssueResponse] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = IssueResponse.from_dict(response_200_item_data)

            response_200.append(response_200_item)

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
) -> Response[HTTPValidationError | list[IssueResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    list_id: str,
    *,
    client: AuthenticatedClient | Client,
    max_issues: int | Unset = 100,
    x_session_token: str,
) -> Response[HTTPValidationError | list[IssueResponse]]:
    """Get Issues In List

    Args:
        list_id (str):
        max_issues (int | Unset):  Default: 100.
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[IssueResponse]]
    """

    kwargs = _get_kwargs(
        list_id=list_id,
        max_issues=max_issues,
        x_session_token=x_session_token,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    list_id: str,
    *,
    client: AuthenticatedClient | Client,
    max_issues: int | Unset = 100,
    x_session_token: str,
) -> HTTPValidationError | list[IssueResponse] | None:
    """Get Issues In List

    Args:
        list_id (str):
        max_issues (int | Unset):  Default: 100.
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[IssueResponse]
    """

    return sync_detailed(
        list_id=list_id,
        client=client,
        max_issues=max_issues,
        x_session_token=x_session_token,
    ).parsed


async def asyncio_detailed(
    list_id: str,
    *,
    client: AuthenticatedClient | Client,
    max_issues: int | Unset = 100,
    x_session_token: str,
) -> Response[HTTPValidationError | list[IssueResponse]]:
    """Get Issues In List

    Args:
        list_id (str):
        max_issues (int | Unset):  Default: 100.
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[IssueResponse]]
    """

    kwargs = _get_kwargs(
        list_id=list_id,
        max_issues=max_issues,
        x_session_token=x_session_token,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    list_id: str,
    *,
    client: AuthenticatedClient | Client,
    max_issues: int | Unset = 100,
    x_session_token: str,
) -> HTTPValidationError | list[IssueResponse] | None:
    """Get Issues In List

    Args:
        list_id (str):
        max_issues (int | Unset):  Default: 100.
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[IssueResponse]
    """

    return (
        await asyncio_detailed(
            list_id=list_id,
            client=client,
            max_issues=max_issues,
            x_session_token=x_session_token,
        )
    ).parsed
