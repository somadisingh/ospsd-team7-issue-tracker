"""Configuration for :class:`ClaudeAIClient`.

All fields are pulled from the environment via :meth:`ClaudeConfig.from_env`.
Defaults are tuned for development; production should set them explicitly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_HOPS = 6
DEFAULT_MAX_TOKENS = 1024


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, *, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class ClaudeConfig:
    """Runtime knobs for :class:`ClaudeAIClient`.

    Attributes:
        api_key: ``ANTHROPIC_API_KEY``. Never forwarded to Claude content.
        model: Anthropic model identifier.
        max_tool_hops: Maximum number of model/tool round trips before
            the client aborts the loop and returns ``truncated=True``.
        allow_mutations: When ``False``, mutating tools are stripped from
            the catalogue and dispatch refuses them. Defaults to ``False``.
        max_tokens: Maximum response size per Claude call.

    """

    api_key: str
    model: str = DEFAULT_MODEL
    max_tool_hops: int = DEFAULT_MAX_HOPS
    allow_mutations: bool = False
    max_tokens: int = DEFAULT_MAX_TOKENS

    @classmethod
    def from_env(cls) -> ClaudeConfig:
        """Build a config from environment variables.

        Raises:
            RuntimeError: if ``ANTHROPIC_API_KEY`` is missing.

        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "ANTHROPIC_API_KEY is not set; cannot build ClaudeConfig."
            raise RuntimeError(msg)
        return cls(
            api_key=api_key,
            model=os.getenv("CLAUDE_MODEL", DEFAULT_MODEL),
            max_tool_hops=_env_int("AI_MAX_TOOL_HOPS", default=DEFAULT_MAX_HOPS),
            allow_mutations=_env_bool("AI_ALLOW_MUTATIONS", default=False),
            max_tokens=_env_int("AI_MAX_TOKENS", default=DEFAULT_MAX_TOKENS),
        )
