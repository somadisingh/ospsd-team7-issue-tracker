"""Dependency-injection wiring for the AI route.

Kept out of ``main.py`` so test code can override ``get_ai_client`` with
``app.dependency_overrides`` without pulling in the real Anthropic SDK.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from chat_client_api import ChatClient  # type: ignore[import-untyped]
from fastapi import Depends, Header, HTTPException

from claude_ai_client_impl import ClaudeAIClient, ClaudeConfig, MockChatClient
from trello_client_impl.client import TrelloClient

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _chat_client() -> ChatClient:
    """Return a process-wide :class:`ChatClient` instance.

    Today we always return the in-memory mock shipped with the Claude
    impl. T2 (Saakshi) swaps this for a concrete chat implementation by
    replacing the body with a real one-liner, e.g.::

        return SlackChatClient.from_env()

    The rest of the AI pipeline does not change.
    """
    logger.info("Wiring in MockChatClient (T2 will replace this)")
    return MockChatClient()


@lru_cache(maxsize=1)
def _claude_config() -> ClaudeConfig:
    return ClaudeConfig.from_env()


def _authenticated_issue_tracker(
    x_session_token: str = Header(..., alias="X-Session-Token"),
) -> TrelloClient:
    """Resolve the user's :class:`TrelloClient` from their session token.

    This intentionally mirrors
    ``issue_tracker_service.main.get_authenticated_client`` but lives
    here to avoid importing ``main`` at module-init time (circular
    import). The behaviour — and thus the test surface — is identical.
    """
    from issue_tracker_service.main import user_sessions
    from issue_tracker_service.routes.auth import _trello_config

    session = user_sessions.get(x_session_token)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing session token",
        )

    config = _trello_config()
    return TrelloClient(
        api_key=config["api_key"],
        secret=config["secret"],
        access_token=session["access_token"],
        access_token_secret=session["access_token_secret"],
    )


def get_ai_client(
    issue_tracker: TrelloClient = Depends(_authenticated_issue_tracker),
) -> ClaudeAIClient:
    """Build a request-scoped :class:`ClaudeAIClient`.

    The issue-tracker client is user-scoped (holds OAuth creds); the
    chat client and Anthropic config are process-wide.
    """
    return ClaudeAIClient(
        issue_tracker=issue_tracker,
        chat=_chat_client(),
        config=_claude_config(),
    )
