from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.delete_board_boards_board_id_delete_response_delete_board_boards_board_id_delete import (
    DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    board_id: str,
    *,
    x_session_token: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Session-Token"] = x_session_token

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/boards/{board_id}".format(
            board_id=quote(str(board_id), safe=""),
        ),
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete.from_dict(response.json())

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
) -> Response[DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    board_id: str,
    *,
    client: AuthenticatedClient | Client,
    x_session_token: str,
) -> Response[DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError]:
    """Delete Board

    Args:
        board_id (str):
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        board_id=board_id,
        x_session_token=x_session_token,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    board_id: str,
    *,
    client: AuthenticatedClient | Client,
    x_session_token: str,
) -> DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError | None:
    """Delete Board

    Args:
        board_id (str):
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError
    """

    return sync_detailed(
        board_id=board_id,
        client=client,
        x_session_token=x_session_token,
    ).parsed


async def asyncio_detailed(
    board_id: str,
    *,
    client: AuthenticatedClient | Client,
    x_session_token: str,
) -> Response[DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError]:
    """Delete Board

    Args:
        board_id (str):
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        board_id=board_id,
        x_session_token=x_session_token,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    board_id: str,
    *,
    client: AuthenticatedClient | Client,
    x_session_token: str,
) -> DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError | None:
    """Delete Board

    Args:
        board_id (str):
        x_session_token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteBoardBoardsBoardIdDeleteResponseDeleteBoardBoardsBoardIdDelete | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            board_id=board_id,
            client=client,
            x_session_token=x_session_token,
        )
    ).parsed
