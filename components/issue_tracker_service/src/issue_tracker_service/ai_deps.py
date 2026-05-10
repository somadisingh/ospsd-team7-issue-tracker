"""Dependency-injection wiring for the AI route.

Kept out of ``main.py`` so test code can override ``get_ai_client`` with
``app.dependency_overrides`` without pulling in the real Anthropic SDK.

The chat backend is selected at import time of the implementation module,
not at construction. Setting ``CHAT_BACKEND`` to ``"slack"`` causes
``chat_client_impl.slack`` to be imported, which in turn registers Team 9's
:class:`SlackClient` (wrapped by our :class:`SlackChatAdapter`) with the
shared ``chat_client_api`` registry. The default ``"local"`` backend uses
the seeded in-memory :class:`LocalChatClient`. Adding a new backend (e.g.
Discord, Telegram) is one entry in ``_CHAT_BACKEND_PACKAGES`` plus the
relevant impl pinned in ``pyproject.toml`` — no other code change.
"""

from __future__ import annotations

import importlib
import logging
import os
from functools import lru_cache

from chat_client_api import (  # type: ignore[import-untyped]
    ChatClient,
    get_client,
)
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from claude_ai_client_impl import ClaudeAIClient, ClaudeConfig
from issue_tracker_service.db import get_db, get_session_credentials
from trello_client_impl.client import TrelloClient

logger = logging.getLogger(__name__)


_CHAT_BACKEND_PACKAGES: dict[str, str] = {
    "local": "chat_client_impl",
    "slack": "chat_client_impl.slack",
    # "discord": "discord_client_impl",  # TBD pending Team 8 confirmation
}


@lru_cache(maxsize=1)
def _chat_client() -> ChatClient:
    """Resolve the registered :class:`ChatClient` for this process.

    Reads ``CHAT_BACKEND`` (default: ``"local"``) and imports the
    corresponding package. The package's ``__init__`` (or a top-level
    ``register_client`` call) wires its factory into the shared registry.
    We then return ``get_client()`` so callers always go through the
    canonical factory pattern from HW1.
    """
    backend = os.getenv("CHAT_BACKEND", "local").lower()
    package = _CHAT_BACKEND_PACKAGES.get(backend)
    if package is None:
        msg = f"Unknown CHAT_BACKEND={backend!r}. Expected one of {sorted(_CHAT_BACKEND_PACKAGES)}."
        raise RuntimeError(msg)
    logger.info("Wiring chat backend: %s (package=%s)", backend, package)
    module = importlib.import_module(package)
    register_fn = getattr(module, "register", None)
    if callable(register_fn):
        register_fn()
    return get_client()


@lru_cache(maxsize=1)
def _claude_config() -> ClaudeConfig:
    return ClaudeConfig.from_env()


def _authenticated_issue_tracker(
    x_session_token: str = Header(..., alias="X-Session-Token"),
    db: Session = Depends(get_db),
) -> TrelloClient:
    """Resolve the user's :class:`TrelloClient` from their session token.

    This intentionally mirrors
    ``issue_tracker_service.main.get_authenticated_client`` but lives
    here to avoid importing ``main`` at module-init time (circular
    import). The behaviour — and thus the test surface — is identical.
    """
    from issue_tracker_service.routes.auth import _trello_config

    creds = get_session_credentials(db, x_session_token)
    if not creds:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing session token",
        )

    config = _trello_config()
    return TrelloClient(
        api_key=config["api_key"],
        secret=config["secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
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
