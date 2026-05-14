from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.auth_callback_response import AuthCallbackResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response


def _get_kwargs(
    *,
    oauth_token: str,
    oauth_verifier: str,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["oauth_token"] = oauth_token

    params["oauth_verifier"] = oauth_verifier

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/auth/callback",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AuthCallbackResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = AuthCallbackResponse.from_dict(response.json())

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
) -> Response[AuthCallbackResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    oauth_token: str,
    oauth_verifier: str,
) -> Response[AuthCallbackResponse | HTTPValidationError]:
    """Auth Callback

     Handle OAuth callback from Trello.

    Exchanges request token and verifier for access token.
    Creates user session and returns session token.

    Args:
        oauth_token: OAuth token from Trello callback.
        oauth_verifier: OAuth verifier from Trello callback.

    Returns:
        AuthCallbackResponse: Session token and user token.

    Raises:
        HTTPException: If token exchange fails or token is invalid.

    Args:
        oauth_token (str): Request token returned by Trello on redirect to /auth/callback. Do not
            use session_token or session_user_token here.
        oauth_verifier (str): Verifier returned by Trello on redirect to /auth/callback for the
            same login attempt.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AuthCallbackResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        oauth_token=oauth_token,
        oauth_verifier=oauth_verifier,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    oauth_token: str,
    oauth_verifier: str,
) -> AuthCallbackResponse | HTTPValidationError | None:
    """Auth Callback

     Handle OAuth callback from Trello.

    Exchanges request token and verifier for access token.
    Creates user session and returns session token.

    Args:
        oauth_token: OAuth token from Trello callback.
        oauth_verifier: OAuth verifier from Trello callback.

    Returns:
        AuthCallbackResponse: Session token and user token.

    Raises:
        HTTPException: If token exchange fails or token is invalid.

    Args:
        oauth_token (str): Request token returned by Trello on redirect to /auth/callback. Do not
            use session_token or session_user_token here.
        oauth_verifier (str): Verifier returned by Trello on redirect to /auth/callback for the
            same login attempt.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AuthCallbackResponse | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        oauth_token=oauth_token,
        oauth_verifier=oauth_verifier,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    oauth_token: str,
    oauth_verifier: str,
) -> Response[AuthCallbackResponse | HTTPValidationError]:
    """Auth Callback

     Handle OAuth callback from Trello.

    Exchanges request token and verifier for access token.
    Creates user session and returns session token.

    Args:
        oauth_token: OAuth token from Trello callback.
        oauth_verifier: OAuth verifier from Trello callback.

    Returns:
        AuthCallbackResponse: Session token and user token.

    Raises:
        HTTPException: If token exchange fails or token is invalid.

    Args:
        oauth_token (str): Request token returned by Trello on redirect to /auth/callback. Do not
            use session_token or session_user_token here.
        oauth_verifier (str): Verifier returned by Trello on redirect to /auth/callback for the
            same login attempt.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AuthCallbackResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        oauth_token=oauth_token,
        oauth_verifier=oauth_verifier,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    oauth_token: str,
    oauth_verifier: str,
) -> AuthCallbackResponse | HTTPValidationError | None:
    """Auth Callback

     Handle OAuth callback from Trello.

    Exchanges request token and verifier for access token.
    Creates user session and returns session token.

    Args:
        oauth_token: OAuth token from Trello callback.
        oauth_verifier: OAuth verifier from Trello callback.

    Returns:
        AuthCallbackResponse: Session token and user token.

    Raises:
        HTTPException: If token exchange fails or token is invalid.

    Args:
        oauth_token (str): Request token returned by Trello on redirect to /auth/callback. Do not
            use session_token or session_user_token here.
        oauth_verifier (str): Verifier returned by Trello on redirect to /auth/callback for the
            same login attempt.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AuthCallbackResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            oauth_token=oauth_token,
            oauth_verifier=oauth_verifier,
        )
    ).parsed
