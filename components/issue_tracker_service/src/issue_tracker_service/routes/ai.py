"""AI assistant routes.

``POST /ai/chat``  — user prompt → AI reply (optionally runs tools); requires ``X-Session-Token``.
Optional header ``X-AI-Provider: claude`` or ``openai`` overrides ``AI_PROVIDER`` for that request only.
``GET  /ai/health`` — verifies the AI stack can be constructed; no session or upstream LLM call (reflects ``AI_PROVIDER`` default only).

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


class AIProviderHealth(BaseModel):
    """Per-provider slice of the AI health probe.

    One of these is produced for every supported LLM stack on every
    ``GET /ai/health`` call (without invoking the upstream LLM), so callers
    can show the right model name when overriding ``AI_PROVIDER`` via the
    per-request ``X-AI-Provider`` header on ``POST /ai/chat``.
    """

    status: str = Field(
        description="`ok` when the provider config loads; `unconfigured` when the API key is missing.",
    )
    model: str = Field(description="Model id for this provider, or empty if unconfigured.")
    api_key_loaded: bool = Field(
        description="Whether this provider's API key was found in the environment.",
    )


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
    providers: dict[str, AIProviderHealth] = Field(
        default_factory=dict,
        description=(
            "Per-provider probes (`claude`, `openai`). Lets clients display the right "
            "model when overriding `AI_PROVIDER` with the `X-AI-Provider` header on "
            "`POST /ai/chat`. Both providers are probed on every health call."
        ),
    )


# ---------------------------------------------------------------------- #
# Endpoints
# ---------------------------------------------------------------------- #


def _probe_claude() -> tuple[AIProviderHealth, bool]:
    """Return (public health, allow_mutations) for the Claude stack.

    ``allow_mutations`` is returned separately because it is a process-wide
    setting (``AI_ALLOW_MUTATIONS``) surfaced at the top of
    :class:`AIHealthResponse` rather than per-provider.
    """
    try:
        cfg = ClaudeConfig.from_env()
    except RuntimeError:
        return (
            AIProviderHealth(status="unconfigured", model="", api_key_loaded=False),
            False,
        )
    return (
        AIProviderHealth(
            status="ok",
            model=cfg.model,
            api_key_loaded=bool(cfg.api_key),
        ),
        cfg.allow_mutations,
    )


def _probe_openai() -> tuple[AIProviderHealth, bool]:
    """Return (public health, allow_mutations) for the OpenAI stack."""
    try:
        cfg = OpenAIConfig.from_env()
    except RuntimeError:
        return (
            AIProviderHealth(status="unconfigured", model="", api_key_loaded=False),
            False,
        )
    return (
        AIProviderHealth(
            status="ok",
            model=cfg.model,
            api_key_loaded=bool(cfg.api_key),
        ),
        cfg.allow_mutations,
    )


@router.get("/health", response_model=AIHealthResponse)
async def ai_health() -> AIHealthResponse:
    """Return which LLM provider is active and whether it is configured.

    Does **not** call Anthropic or OpenAI. Use this in Swagger **Try it out** to
    demonstrate multiprovider deployment: redeploy or change server env
    (`AI_PROVIDER`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, `OPENAI_MODEL`) and
    compare responses.

    The response also includes a `providers` map probing **both** Claude and
    OpenAI so frontends that let users override `AI_PROVIDER` per request (via
    `X-AI-Provider` on `POST /ai/chat`) can display the correct model name for
    the chosen stack without hardcoding it client-side.
    """
    claude_info, claude_allow_mut = _probe_claude()
    openai_info, openai_allow_mut = _probe_openai()
    providers = {"claude": claude_info, "openai": openai_info}

    active = os.getenv("AI_PROVIDER", "claude").strip().lower()
    if active not in providers:
        active = "claude"
    active_info = providers[active]
    active_allow_mut = openai_allow_mut if active == "openai" else claude_allow_mut

    return AIHealthResponse(
        status=active_info.status,
        provider=active,
        model=active_info.model,
        allow_mutations=active_allow_mut,
        api_key_loaded=active_info.api_key_loaded,
        providers=providers,
    )


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    ai: AIClient = Depends(get_ai_client),
) -> AIChatResponse:
    """Send ``body.prompt`` to the LLM (Claude or OpenAI).

    Default stack comes from ``AI_PROVIDER`` in the service environment.
    Optional header ``X-AI-Provider: claude`` or ``openai`` overrides that for
    this request only (see OpenAPI **Parameters** for this route). The JSON
    body does not select the provider. Returns the final answer and a per-request
    tool action log.
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
