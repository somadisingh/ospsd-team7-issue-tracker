from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.add_member_to_board_boards_board_id_members_post_response_add_member_to_board_boards_board_id_members_post import (
    AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost,
)
from ...models.add_member_to_board_request import AddMemberToBoardRequest
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    board_id: str,
    *,
    body: AddMemberToBoardRequest,
    x_session_token: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Session-Token"] = x_session_token

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/boards/{board_id}/members".format(
            board_id=quote(str(board_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost
    | HTTPValidationError
    | None
):
    if response.status_code == 200:
        response_200 = (
            AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost.from_dict(
                response.json()
            )
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
    AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost | HTTPValidationError
]:
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
    body: AddMemberToBoardRequest,
    x_session_token: str,
) -> Response[
    AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost | HTTPValidationError
]:
    """Add Member To Board

    Args:
        board_id (str):
        x_session_token (str):
        body (AddMemberToBoardRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        board_id=board_id,
        body=body,
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
    body: AddMemberToBoardRequest,
    x_session_token: str,
) -> (
    AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost
    | HTTPValidationError
    | None
):
    """Add Member To Board

    Args:
        board_id (str):
        x_session_token (str):
        body (AddMemberToBoardRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost | HTTPValidationError
    """

    return sync_detailed(
        board_id=board_id,
        client=client,
        body=body,
        x_session_token=x_session_token,
    ).parsed


async def asyncio_detailed(
    board_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: AddMemberToBoardRequest,
    x_session_token: str,
) -> Response[
    AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost | HTTPValidationError
]:
    """Add Member To Board

    Args:
        board_id (str):
        x_session_token (str):
        body (AddMemberToBoardRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        board_id=board_id,
        body=body,
        x_session_token=x_session_token,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    board_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: AddMemberToBoardRequest,
    x_session_token: str,
) -> (
    AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost
    | HTTPValidationError
    | None
):
    """Add Member To Board

    Args:
        board_id (str):
        x_session_token (str):
        body (AddMemberToBoardRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AddMemberToBoardBoardsBoardIdMembersPostResponseAddMemberToBoardBoardsBoardIdMembersPost | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            board_id=board_id,
            client=client,
            body=body,
            x_session_token=x_session_token,
        )
    ).parsed
