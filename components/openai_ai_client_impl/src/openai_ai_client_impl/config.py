"""OpenAI Chat Completions configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gpt-4o-mini"
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
class OpenAIConfig:
    """Runtime knobs for :class:`OpenAIAIClient`."""

    api_key: str
    model: str = DEFAULT_MODEL
    max_tool_hops: int = DEFAULT_MAX_HOPS
    allow_mutations: bool = False
    max_tokens: int = DEFAULT_MAX_TOKENS
    structured_output: bool = False

    @classmethod
    def from_env(cls) -> OpenAIConfig:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            msg = "OPENAI_API_KEY is not set; cannot build OpenAIConfig."
            raise RuntimeError(msg)
        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            max_tool_hops=_env_int("AI_MAX_TOOL_HOPS", default=DEFAULT_MAX_HOPS),
            allow_mutations=_env_bool("AI_ALLOW_MUTATIONS", default=False),
            max_tokens=_env_int("AI_MAX_TOKENS", default=DEFAULT_MAX_TOKENS),
            structured_output=_env_bool("AI_STRUCTURED_OUTPUT", default=False),
        )
