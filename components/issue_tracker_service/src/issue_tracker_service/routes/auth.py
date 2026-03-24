"""OAuth 1.0 authentication routes."""

# import logging
from typing import Dict
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from trello_client_impl.client import TrelloClient

# Load .env file at module import time
load_dotenv()

# Configure logging
# logger = logging.getLogger(__name__)

# In-memory OAuth state management (mini-demo)
# In production, use a database with expiration
oauth1_request_secrets: Dict[str, str] = {}


class AuthCallbackResponse(BaseModel):
    """OAuth callback response with session token."""

    session_token: str = Field(description="Server session identifier used for subsequent API calls.")
    # session_user_token: str = Field(description="Trello OAuth access token associated with the session.")


router = APIRouter(prefix="/auth", tags=["authentication"])


def _trello_config() -> Dict[str, str]:
    """Load Trello OAuth credentials from environment or .env file.

    Returns:
        Dictionary with api_key, secret, and callback_url.

    Raises:
        RuntimeError: If required environment variables are missing.
    """
    import os

    api_key = os.getenv("TRELLO_API_KEY")
    secret = os.getenv("TRELLO_API_SECRET")

    if not api_key or not secret:
        raise RuntimeError(
            "Missing Trello OAuth credentials. Set TRELLO_API_KEY and TRELLO_API_SECRET in environment or .env file."
        )

    return {
        "api_key": api_key,
        "secret": secret,
        "callback_url": os.getenv("TRELLO_CALLBACK_URL", "http://localhost:8000/auth/callback"),
    }


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
    # logger.info(f"Stored request_token: {request_token}")
    # logger.info(f"Available tokens in cache: {list(oauth1_request_secrets.keys())}")

    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback", response_model=AuthCallbackResponse)
async def auth_callback(
    oauth_token: str = Query(
        ...,
        description=(
            "Request token returned by Trello on redirect to /auth/callback. "
            "Do not use session_token or session_user_token here."
        ),
    ),
    oauth_verifier: str = Query(
        ...,
        description="Verifier returned by Trello on redirect to /auth/callback for the same login attempt.",
    ),
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

    # logger.info(f"Callback received with oauth_token: {oauth_token}")
    # logger.info(f"Available tokens in cache: {list(oauth1_request_secrets.keys())}")

    config = _trello_config()
    request_token_secret = oauth1_request_secrets.pop(oauth_token, None)
    if not request_token_secret:
        # logger.error(f"Token not found: {oauth_token}. Cache contents: {list(oauth1_request_secrets.keys())}")
        raise HTTPException(
            status_code=400,
            detail=(
                "Unknown or expired oauth_token. Use oauth_token and oauth_verifier from Trello's redirect "
                "after /auth/login. Request tokens are one-time and are not the same as session_token/session_user_token."
            ),
        )

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

    # return AuthCallbackResponse(session_token=session_token, session_user_token=client.token)
    return AuthCallbackResponse(session_token=session_token)
