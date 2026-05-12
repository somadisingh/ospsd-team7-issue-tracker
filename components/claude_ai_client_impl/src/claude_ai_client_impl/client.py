"""Anthropic Claude implementation of :class:`ai_client_api.AIClient`.

The flow:

1. Sanitize the user prompt (length + secret/PII scrub).
2. Build a system prompt and initial user turn with scoped context.
3. Loop up to ``config.max_tool_hops``:
   a. Call ``anthropic.messages.create`` with the tool catalogue.
   b. If the model asked for a tool (``stop_reason == "tool_use"``),
      dispatch each ``tool_use`` block, append the results as a
      ``tool_result`` user turn, and go again.
   c. Otherwise, extract the text and return.
4. If the loop exits because of the hop limit, return the best partial
   text with ``truncated=True``.

The Anthropic SDK is injected via the constructor so tests can supply a
mock without any real HTTP traffic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any

from ai_client_api import sanitize
from ai_client_api.client import AIClient
from ai_client_api.exceptions import (
    AIProviderError,
    AIToolError,
    AIUnsafeRequestError,
)
from ai_client_api.resilience import RetryPolicy, call_with_resilience
from ai_client_api.structured_output import (
    parse_structured_envelope,
    system_prompt_with_structured_mode,
)
from ai_client_api.types import AIReply, ToolAction
from prometheus_client import Counter, Histogram

from claude_ai_client_impl.config import ClaudeConfig
from claude_ai_client_impl.prompt import SYSTEM_PROMPT, render_user_message
from claude_ai_client_impl.tools import ToolDispatcher

if TYPE_CHECKING:  # pragma: no cover
    import anthropic
    from chat_client_api import ChatClient
    from issue_tracker_client_api import Client as IssueTrackerClient

logger = logging.getLogger(__name__)


def _retry_policy() -> RetryPolicy:
    return RetryPolicy(
        max_attempts=int(os.getenv("AI_HTTP_MAX_ATTEMPTS", "4")),
        base_delay_s=float(os.getenv("AI_HTTP_RETRY_BASE_S", "0.1")),
        max_delay_s=float(os.getenv("AI_HTTP_RETRY_MAX_S", "2.0")),
    )


_anthropic_request_duration_seconds = Histogram(
    "issue_tracker_ai_anthropic_request_duration_seconds",
    "Anthropic API request latency in seconds.",
    labelnames=("model", "result"),
)
_ai_tool_invocations_total = Counter(
    "issue_tracker_ai_tool_invocations_total",
    "Total AI tool invocations by tool name and outcome.",
    labelnames=("tool", "outcome"),
)
_ai_anthropic_input_tokens_total = Counter(
    "issue_tracker_ai_anthropic_input_tokens_total",
    "Total Anthropic input tokens consumed.",
    labelnames=("model",),
)
_ai_anthropic_output_tokens_total = Counter(
    "issue_tracker_ai_anthropic_output_tokens_total",
    "Total Anthropic output tokens generated.",
    labelnames=("model",),
)
_ai_anthropic_cost_usd_total = Counter(
    "issue_tracker_ai_anthropic_cost_usd_total",
    "Estimated Anthropic request cost in USD (cumulative).",
    labelnames=("model",),
)
_ai_anthropic_request_cost_usd = Histogram(
    "issue_tracker_ai_anthropic_request_cost_usd",
    "Estimated Anthropic request cost in USD per call.",
    labelnames=("model",),
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, float("inf")),
)


class ClaudeAIClient(AIClient):
    """Concrete :class:`AIClient` backed by Anthropic Claude."""

    def __init__(
        self,
        *,
        issue_tracker: IssueTrackerClient,
        chat: ChatClient,
        config: ClaudeConfig,
        anthropic_client: anthropic.Anthropic | None = None,
        dispatcher: ToolDispatcher | None = None,
    ) -> None:
        self._config = config
        self._dispatcher = dispatcher or ToolDispatcher(
            issue_tracker=issue_tracker,
            chat=chat,
            allow_mutations=config.allow_mutations,
        )
        self._client = anthropic_client or self._build_anthropic_client()

    # ------------------------------------------------------------------ #
    # AIClient contract
    # ------------------------------------------------------------------ #

    def send_message(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AIReply:
        try:
            clean_prompt = sanitize.sanitize_prompt(prompt)
        except ValueError as exc:
            raise AIUnsafeRequestError(str(exc)) from exc

        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": render_user_message(clean_prompt, context),
            }
        ]
        actions: list[ToolAction] = []
        tools_schema = self._dispatcher.schemas()

        for _ in range(self._config.max_tool_hops):
            response = self._call_anthropic(messages, tools_schema)
            stop_reason = getattr(response, "stop_reason", None)

            # Always append the assistant's turn so the next call has the
            # conversation history Anthropic expects.
            messages.append(
                {
                    "role": "assistant",
                    "content": _content_to_list(response.content),
                }
            )

            if stop_reason != "tool_use":
                text = _extract_text(response.content)
                if self._config.structured_output and text.strip():
                    envelope = parse_structured_envelope(text)
                    text = envelope.reply
                return AIReply(
                    reply=text,
                    actions=actions,
                    truncated=False,
                )

            tool_results = self._run_tools(response.content, actions)
            messages.append({"role": "user", "content": tool_results})

        # Hop limit reached — surface whatever the model has said so far.
        partial = _extract_text(messages[-1].get("content", [])) if messages else ""
        if self._config.structured_output and partial.strip():
            envelope = parse_structured_envelope(partial)
            partial = envelope.reply
        return AIReply(
            reply=partial or "Reached the tool-hop limit without a final answer.",
            actions=actions,
            truncated=True,
        )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _build_anthropic_client(self) -> anthropic.Anthropic:
        import anthropic  # local import keeps the SDK optional at import time

        return anthropic.Anthropic(api_key=self._config.api_key)

    def _call_anthropic(
        self,
        messages: list[dict[str, Any]],
        tools_schema: list[dict[str, Any]],
    ) -> Any:
        start = time.perf_counter()

        def _invoke() -> Any:
            return self._client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                system=system_prompt_with_structured_mode(
                    SYSTEM_PROMPT,
                    structured_output=self._config.structured_output,
                ),
                tools=tools_schema,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
            )

        try:
            response = call_with_resilience(_invoke, retry=_retry_policy())
            result = str(getattr(response, "stop_reason", "unknown") or "unknown")
            _anthropic_request_duration_seconds.labels(
                model=self._config.model, result=result
            ).observe(time.perf_counter() - start)
            input_tokens, output_tokens = _extract_usage_tokens(response)
            _ai_anthropic_input_tokens_total.labels(model=self._config.model).inc(
                input_tokens
            )
            _ai_anthropic_output_tokens_total.labels(model=self._config.model).inc(
                output_tokens
            )
            estimated_cost = _estimate_cost_usd(input_tokens, output_tokens)
            _ai_anthropic_cost_usd_total.labels(model=self._config.model).inc(
                estimated_cost
            )
            _ai_anthropic_request_cost_usd.labels(model=self._config.model).observe(
                estimated_cost
            )
        except Exception as exc:
            _anthropic_request_duration_seconds.labels(
                model=self._config.model, result="error"
            ).observe(time.perf_counter() - start)
            logger.warning("Anthropic call failed: %s", exc)
            raise AIProviderError(f"Upstream Claude call failed: {exc}") from exc
        else:
            return response

    def _run_tools(
        self,
        content: Any,
        actions: list[ToolAction],
    ) -> list[dict[str, Any]]:
        """Dispatch every tool_use block and return the tool_result blocks."""
        results: list[dict[str, Any]] = []
        for block in _iter_blocks(content):
            if _block_type(block) != "tool_use":
                continue

            tool_name = _block_attr(block, "name", "")
            tool_use_id = _block_attr(block, "id", "")
            tool_input = _block_attr(block, "input", {}) or {}

            try:
                result = self._dispatcher.dispatch(tool_name, tool_input)
                ok = True
                error: str | None = None
                result_payload = _json_safe(result)
                _ai_tool_invocations_total.labels(tool=tool_name, outcome="ok").inc()
            except AIToolError as exc:
                ok = False
                error = str(exc)
                result_payload = f"[tool_error] {error}"
                logger.info("Tool %s rejected: %s", tool_name, error)
                _ai_tool_invocations_total.labels(
                    tool=tool_name, outcome="tool_error"
                ).inc()
            except Exception as exc:
                ok = False
                error = f"Tool {tool_name!r} failed: {exc}"
                result_payload = f"[tool_error] {error}"
                logger.warning("Tool %s raised: %s", tool_name, exc)
                _ai_tool_invocations_total.labels(
                    tool=tool_name, outcome="runtime_error"
                ).inc()

            actions.append(
                ToolAction(
                    tool=tool_name,
                    arguments=dict(tool_input),
                    ok=ok,
                    error=error,
                )
            )
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_payload
                    if isinstance(result_payload, str)
                    else json.dumps(result_payload),
                    "is_error": not ok,
                }
            )
        return results


# ---------------------------------------------------------------------- #
# Helpers that normalize Anthropic block objects vs dicts
# ---------------------------------------------------------------------- #


def _iter_blocks(content: Any) -> list[Any]:
    if isinstance(content, list):
        return content
    return [content]


def _block_type(block: Any) -> str:
    if isinstance(block, dict):
        return str(block.get("type", ""))
    return str(getattr(block, "type", ""))


def _block_attr(block: Any, name: str, default: Any) -> Any:
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def _content_to_list(content: Any) -> list[dict[str, Any]]:
    """Convert Anthropic's content blocks into plain dicts for replay.

    Anthropic expects the same shape back on the next call; passing the
    raw SDK objects also works, but dicts keep tests provider-agnostic.
    """
    blocks: list[dict[str, Any]] = []
    for block in _iter_blocks(content):
        btype = _block_type(block)
        if btype == "text":
            blocks.append({"type": "text", "text": _block_attr(block, "text", "")})
        elif btype == "tool_use":
            blocks.append(
                {
                    "type": "tool_use",
                    "id": _block_attr(block, "id", ""),
                    "name": _block_attr(block, "name", ""),
                    "input": _block_attr(block, "input", {}) or {},
                }
            )
    return blocks


def _extract_text(content: Any) -> str:
    parts: list[str] = []
    for block in _iter_blocks(content):
        if _block_type(block) == "text":
            parts.append(str(_block_attr(block, "text", "")))
    return "\n".join(p for p in parts if p).strip()


def _json_safe(value: Any) -> Any:
    """Coerce arbitrary Python data into JSON-serializable form."""
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def _extract_usage_tokens(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return (0, 0)

    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    return (input_tokens, output_tokens)


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    input_per_million = float(
        os.environ.get("AI_COST_INPUT_PER_MILLION_USD", "3.0").strip() or "3.0"
    )
    output_per_million = float(
        os.environ.get("AI_COST_OUTPUT_PER_MILLION_USD", "15.0").strip() or "15.0"
    )

    input_cost = (input_tokens / 1_000_000.0) * input_per_million
    output_cost = (output_tokens / 1_000_000.0) * output_per_million
    return input_cost + output_cost
