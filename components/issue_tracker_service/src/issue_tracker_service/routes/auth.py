"""OAuth 1.0 authentication routes."""

from typing import Any, Dict
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from trello_client_impl.client import TrelloClient

# In-memory OAuth state management (mini-demo)
# In production, use a database with expiration
oauth1_request_secrets: Dict[str, str] = {}


class AuthCallbackResponse(BaseModel):
    """OAuth callback response with session token."""

    session_token: str
    session_user_token: str


router = APIRouter(prefix="/auth", tags=["authentication"])


def _trello_config() -> Dict[str, str]:
    """Load Trello OAuth credentials from environment.

    Returns:
        Dictionary with api_key, secret, and callback_url.

    Raises:
        RuntimeError: If required environment variables are missing.
    """
    from os import environ

    try:
        return {
            "api_key": environ["TRELLO_API_KEY"],
            "secret": environ["TRELLO_API_SECRET"],
            "callback_url": environ.get("TRELLO_CALLBACK_URL", "http://localhost:8000/auth/callback"),
        }
    except KeyError as exc:
        raise RuntimeError("Missing Trello OAuth credentials in environment") from exc


@router.get("/login")
async def auth_login() -> RedirectResponse:
    """Initiate OAuth 1.0 flow with Trello.

    Redirects user to Trello authorization page.

    Returns:
        RedirectResponse: Redirect to Trello authorization URL.

    Raises:
        HTTPException: If request token fetch fails.
    """
    config = _trello_config()
    client = TrelloClient(api_key=config["api_key"], secret=config["secret"])
    auth_url = client.get_authorization_url(callback_url=config["callback_url"])
    parsed = parse_qs(urlparse(auth_url).query)
    request_token = parsed.get("oauth_token", [None])[0]
    if not request_token:
        raise HTTPException(status_code=500, detail="Failed to fetch oauth_token from Trello")

    if not client.request_token_secret:
        raise HTTPException(status_code=500, detail="Missing request token secret from Trello client")

    oauth1_request_secrets[request_token] = client.request_token_secret

    return RedirectResponse(auth_url)


@router.get("/callback", response_model=AuthCallbackResponse)
async def auth_callback(
    oauth_token: str = Query(...),
    oauth_verifier: str = Query(...),
) -> AuthCallbackResponse:
    """Handle OAuth callback from Trello.

    Exchanges request token and verifier for access token.
    Creates user session and returns session token.

    Args:
        oauth_token: OAuth token from Trello callback.
        oauth_verifier: OAuth verifier from Trello callback.

    Returns:
        AuthCallbackResponse: Session token and user token.

    Raises:
        HTTPException: If token exchange fails or token is invalid.
    """
    # Import here to avoid circular imports
    from issue_tracker_service.main import user_sessions

    config = _trello_config()
    request_token_secret = oauth1_request_secrets.pop(oauth_token, None)
    if not request_token_secret:
        raise HTTPException(status_code=400, detail="Unknown or expired oauth_token")

    client = TrelloClient(
        api_key=config["api_key"],
        secret=config["secret"],
        request_token_secret=request_token_secret,
    )
    client.exchange_request_token(oauth_token=oauth_token, oauth_verifier=oauth_verifier)

    if not client.token or not client.access_token_secret:
        raise HTTPException(status_code=500, detail="Failed to obtain access token")

    session_token = uuid4().hex
    user_sessions[session_token] = {
        "access_token": client.token,
        "access_token_secret": client.access_token_secret,
    }

    return AuthCallbackResponse(session_token=session_token, session_user_token=client.token)
