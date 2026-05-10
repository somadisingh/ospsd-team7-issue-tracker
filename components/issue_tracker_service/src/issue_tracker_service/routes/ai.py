"""AI assistant routes.

``POST /ai/chat``  — user prompt → AI reply (optionally runs tools).
``GET  /ai/health`` — verifies the AI stack can be constructed.

Both routes authenticate with the existing ``X-Session-Token`` flow and
reuse the authenticated ``TrelloClient`` via dependency injection. The
AI client is built per-request so its tool dispatcher binds to the
user's own Trello credentials — mirrors how every other endpoint in the
service handles auth.
"""

from __future__ import annotations

import logging
from typing import Any

from ai_client_api.exceptions import (
    AIError,
    AIProviderError,
    AIToolError,
    AIUnsafeRequestError,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from claude_ai_client_impl import ClaudeAIClient, ClaudeConfig

from issue_tracker_service.ai_deps import get_ai_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# ---------------------------------------------------------------------- #
# Request / response models
# ---------------------------------------------------------------------- #


class AIChatRequest(BaseModel):
    """User prompt plus optional scoping context."""

    prompt: str = Field(min_length=1, max_length=8000)
    board_id: str | None = None
    channel_id: str | None = None


class AIToolActionResponse(BaseModel):
    tool: str
    ok: bool
    error: str | None = None


class AIChatResponse(BaseModel):
    reply: str
    actions: list[AIToolActionResponse] = Field(default_factory=list)
    truncated: bool = False


class AIHealthResponse(BaseModel):
    status: str
    model: str
    allow_mutations: bool
    api_key_loaded: bool


# ---------------------------------------------------------------------- #
# Endpoints
# ---------------------------------------------------------------------- #


@router.get("/health", response_model=AIHealthResponse)
async def ai_health() -> AIHealthResponse:
    """Verify the AI stack is configured.

    Does NOT call Claude — this is a liveness/readiness probe for the
    configuration layer only.
    """
    try:
        config = ClaudeConfig.from_env()
    except RuntimeError:
        return AIHealthResponse(
            status="unconfigured",
            model="",
            allow_mutations=False,
            api_key_loaded=False,
        )
    return AIHealthResponse(
        status="ok",
        model=config.model,
        allow_mutations=config.allow_mutations,
        api_key_loaded=bool(config.api_key),
    )


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    ai: ClaudeAIClient = Depends(get_ai_client),
) -> AIChatResponse:
    """Send ``body.prompt`` to Claude. Returns the final answer + action log."""
    context: dict[str, Any] = {}
    if body.board_id is not None:
        context["board_id"] = body.board_id
    if body.channel_id is not None:
        context["channel_id"] = body.channel_id

    try:
        reply = ai.send_message(body.prompt, context=context or None)
    except AIUnsafeRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIProviderError as exc:
        logger.warning("AI provider failure: %s", exc)
        raise HTTPException(status_code=502, detail="AI provider unavailable") from exc
    except AIToolError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIError as exc:
        logger.exception("AI unexpected error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AIChatResponse(
        reply=reply.reply,
        actions=[AIToolActionResponse(tool=a.tool, ok=a.ok, error=a.error) for a in reply.actions],
        truncated=reply.truncated,
    )


__all__ = ["router"]
