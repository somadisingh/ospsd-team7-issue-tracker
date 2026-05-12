"""OpenAI Chat Completions implementation of :class:`ai_client_api.AIClient`."""

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
from ai_client_api.resilience import (
    IdempotencyMemory,
    RetryPolicy,
    call_with_resilience,
    idempotency_scope,
)
from ai_client_api.signature_tools import SignatureToolCatalog
from ai_client_api.structured_output import (
    parse_structured_envelope,
    system_prompt_with_structured_mode,
)
from ai_client_api.types import AIReply, ToolAction
from claude_ai_client_impl.prompt import SYSTEM_PROMPT, render_user_message
from openai import OpenAI
from prometheus_client import Counter, Histogram

from openai_ai_client_impl.config import OpenAIConfig
from openai_ai_client_impl.domain_catalog import build_domain_catalog

if TYPE_CHECKING:
    from chat_client_api import ChatClient  # type: ignore[import-untyped]
    from issue_tracker_client_api import Client as IssueTrackerClient

logger = logging.getLogger(__name__)

_openai_request_duration_seconds = Histogram(
    "issue_tracker_ai_openai_request_duration_seconds",
    "OpenAI API request latency in seconds.",
    labelnames=("model", "result"),
)
_ai_tool_invocations_total = Counter(
    "issue_tracker_ai_openai_tool_invocations_total",
    "Total AI tool invocations by tool name and outcome (OpenAI path).",
    labelnames=("tool", "outcome"),
)


def _retry_policy() -> RetryPolicy:
    return RetryPolicy(
        max_attempts=_env_int("AI_HTTP_MAX_ATTEMPTS", default=4),
        base_delay_s=float(os.getenv("AI_HTTP_RETRY_BASE_S", "0.1")),
        max_delay_s=float(os.getenv("AI_HTTP_RETRY_MAX_S", "2.0")),
    )


def _env_int(name: str, *, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class OpenAIAIClient(AIClient):
    """Concrete :class:`AIClient` using OpenAI function calling."""

    def __init__(
        self,
        *,
        issue_tracker: IssueTrackerClient,
        chat: ChatClient,
        config: OpenAIConfig,
        openai_client: OpenAI | None = None,
        catalog: SignatureToolCatalog | None = None,
        idempotency: IdempotencyMemory | None = None,
    ) -> None:
        self._config = config
        self._idem = idempotency or IdempotencyMemory()
        self._catalog = catalog or build_domain_catalog(
            issue_tracker,
            chat,
            allow_mutations=config.allow_mutations,
            idempotency=self._idem,
        )
        self._client = openai_client or OpenAI(api_key=config.api_key)

    def send_message(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AIReply:
        try:
            clean_prompt = sanitize.sanitize_prompt(prompt)
        except ValueError as exc:
            raise AIUnsafeRequestError(str(exc)) from exc

        idem_key = None
        if context:
            idem_key = context.get("idempotency_key")
            if isinstance(idem_key, str) and idem_key:
                idem_key = idem_key[:128]
            else:
                idem_key = None

        user_text = render_user_message(clean_prompt, context or {})
        system_text = system_prompt_with_structured_mode(
            SYSTEM_PROMPT,
            structured_output=self._config.structured_output,
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ]
        tools = self._catalog.schemas_openai()
        actions: list[ToolAction] = []

        with idempotency_scope(idem_key):
            for _ in range(self._config.max_tool_hops):
                completion = self._call_openai(messages, tools)
                choice = completion.choices[0].message
                tool_calls = getattr(choice, "tool_calls", None) or []

                if tool_calls:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": choice.content,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments,
                                    },
                                }
                                for tc in tool_calls
                            ],
                        }
                    )
                    for tc in tool_calls:
                        name = tc.function.name
                        raw_args = tc.function.arguments or "{}"
                        try:
                            args_dict = json.loads(raw_args)
                        except json.JSONDecodeError as exc:
                            raise AIToolError(
                                f"Invalid tool JSON for {name!r}"
                            ) from exc
                        try:
                            result = self._catalog.dispatch(name, args_dict)
                            ok = True
                            err: str | None = None
                            payload = _json_safe(result)
                            _ai_tool_invocations_total.labels(
                                tool=name, outcome="ok"
                            ).inc()
                        except AIToolError as exc:
                            ok = False
                            err = str(exc)
                            payload = f"[tool_error] {err}"
                            _ai_tool_invocations_total.labels(
                                tool=name, outcome="tool_error"
                            ).inc()
                        except Exception as exc:
                            ok = False
                            err = f"Tool {name!r} failed: {exc}"
                            payload = f"[tool_error] {err}"
                            logger.warning("Tool %s raised: %s", name, exc)
                            _ai_tool_invocations_total.labels(
                                tool=name, outcome="runtime_error"
                            ).inc()

                        actions.append(
                            ToolAction(
                                tool=name,
                                arguments=dict(args_dict),
                                ok=ok,
                                error=err,
                            )
                        )
                        content = (
                            payload if isinstance(payload, str) else json.dumps(payload)
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": content,
                            }
                        )
                    continue

                text = (choice.content or "").strip()
                if self._config.structured_output and text:
                    envelope = parse_structured_envelope(text)
                    text = envelope.reply
                return AIReply(reply=text, actions=actions, truncated=False)

        partial = ""
        if messages:
            partial = str(messages[-1].get("content", "") or "")
        return AIReply(
            reply=partial or "Reached the tool-hop limit without a final answer.",
            actions=actions,
            truncated=True,
        )

    def _call_openai(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        start = time.perf_counter()

        def _invoke() -> Any:
            kwargs: dict[str, Any] = {
                "model": self._config.model,
                "messages": messages,
                "max_tokens": self._config.max_tokens,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            return self._client.chat.completions.create(**kwargs)

        try:
            out = call_with_resilience(_invoke, retry=_retry_policy())
            result = (
                "tool_calls"
                if getattr(out.choices[0].message, "tool_calls", None)
                else "message"
            )
            _openai_request_duration_seconds.labels(
                model=self._config.model, result=result
            ).observe(time.perf_counter() - start)
            return out
        except Exception as exc:
            _openai_request_duration_seconds.labels(
                model=self._config.model, result="error"
            ).observe(time.perf_counter() - start)
            logger.warning("OpenAI call failed: %s", exc)
            raise AIProviderError(f"Upstream OpenAI call failed: {exc}") from exc


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value
