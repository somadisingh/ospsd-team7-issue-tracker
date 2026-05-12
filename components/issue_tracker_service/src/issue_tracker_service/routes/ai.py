"""AI assistant routes.

``POST /ai/chat``  — user prompt → AI reply (optionally runs tools); requires ``X-Session-Token``.
``GET  /ai/health`` — verifies the AI stack can be constructed; no session or upstream LLM call.

The chat route authenticates with the existing ``X-Session-Token`` flow and
reuse the authenticated ``TrelloClient`` via dependency injection. The
AI client is built per-request so its tool dispatcher binds to the
user's own Trello credentials — mirrors how every other endpoint in the
service handles auth.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ai_client_api.client import AIClient
from ai_client_api.exceptions import (
    AIError,
    AIProviderError,
    AIStructuredOutputError,
    AIToolError,
    AIUnsafeRequestError,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter

from claude_ai_client_impl import ClaudeConfig
from openai_ai_client_impl.config import OpenAIConfig

from issue_tracker_service.ai_deps import get_ai_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])
_ai_chat_requests_total = Counter(
    "issue_tracker_ai_chat_requests_total",
    "Total AI chat requests grouped by semantic result.",
    labelnames=("result",),
)


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
    """Probe of the configured LLM stack (no upstream LLM call)."""

    status: str = Field(
        description="`ok` when the provider config loads; `unconfigured` when the API key is missing.",
    )
    provider: str = Field(
        description="Active stack: `claude` or `openai`, from `AI_PROVIDER` (default `claude`).",
    )
    model: str = Field(description="Model id for the active provider, or empty if unconfigured.")
    allow_mutations: bool = Field(
        description="Whether mutating tools are enabled (`AI_ALLOW_MUTATIONS`).",
    )
    api_key_loaded: bool = Field(
        description="Whether the provider's API key was found in the environment.",
    )


# ---------------------------------------------------------------------- #
# Endpoints
# ---------------------------------------------------------------------- #


@router.get("/health", response_model=AIHealthResponse)
async def ai_health() -> AIHealthResponse:
    """Return which LLM provider is active and whether it is configured.

    Does **not** call Anthropic or OpenAI. Use this in Swagger **Try it out** to
    demonstrate multiprovider deployment: redeploy or change server env
    (`AI_PROVIDER`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, `OPENAI_MODEL`) and
    compare responses.
    """
    provider = os.getenv("AI_PROVIDER", "claude").strip().lower()
    if provider == "openai":
        try:
            cfg = OpenAIConfig.from_env()
        except RuntimeError:
            return AIHealthResponse(
                status="unconfigured",
                provider=provider,
                model="",
                allow_mutations=False,
                api_key_loaded=False,
            )
        return AIHealthResponse(
            status="ok",
            provider=provider,
            model=cfg.model,
            allow_mutations=cfg.allow_mutations,
            api_key_loaded=bool(cfg.api_key),
        )

    try:
        config = ClaudeConfig.from_env()
    except RuntimeError:
        return AIHealthResponse(
            status="unconfigured",
            provider="claude",
            model="",
            allow_mutations=False,
            api_key_loaded=False,
        )
    return AIHealthResponse(
        status="ok",
        provider="claude",
        model=config.model,
        allow_mutations=config.allow_mutations,
        api_key_loaded=bool(config.api_key),
    )


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    ai: AIClient = Depends(get_ai_client),
) -> AIChatResponse:
    """Send ``body.prompt`` to the **server-configured** LLM (Claude or OpenAI).

    The implementation is chosen via ``AI_PROVIDER`` in the service environment,
    not via this JSON body. Returns the final answer and a per-request tool
    action log.
    """
    context: dict[str, Any] = {}
    if body.board_id is not None:
        context["board_id"] = body.board_id
    if body.channel_id is not None:
        context["channel_id"] = body.channel_id

    try:
        reply = ai.send_message(body.prompt, context=context or None)
    except AIUnsafeRequestError as exc:
        _ai_chat_requests_total.labels(result="unsafe_request").inc()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIStructuredOutputError as exc:
        _ai_chat_requests_total.labels(result="structured_output_error").inc()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except AIProviderError as exc:
        logger.warning("AI provider failure: %s", exc)
        _ai_chat_requests_total.labels(result="provider_error").inc()
        raise HTTPException(status_code=502, detail="AI provider unavailable") from exc
    except AIToolError as exc:
        _ai_chat_requests_total.labels(result="tool_error").inc()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIError as exc:
        logger.exception("AI unexpected error")
        _ai_chat_requests_total.labels(result="internal_error").inc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _ai_chat_requests_total.labels(result="success").inc()
    return AIChatResponse(
        reply=reply.reply,
        actions=[AIToolActionResponse(tool=a.tool, ok=a.ok, error=a.error) for a in reply.actions],
        truncated=reply.truncated,
    )


__all__ = ["router"]
