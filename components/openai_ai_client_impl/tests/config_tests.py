"""Tests for :class:`openai_ai_client_impl.config.OpenAIConfig`."""

from __future__ import annotations

import pytest
from openai_ai_client_impl.config import OpenAIConfig


@pytest.mark.unit
def test_from_env_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIConfig.from_env()


@pytest.mark.unit
def test_from_env_defaults_and_bools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("AI_ALLOW_MUTATIONS", "yes")
    monkeypatch.setenv("AI_STRUCTURED_OUTPUT", "1")
    monkeypatch.setenv("AI_MAX_TOOL_HOPS", "not-int")
    monkeypatch.setenv("AI_MAX_TOKENS", "2048")
    cfg = OpenAIConfig.from_env()
    assert cfg.api_key == "sk-x"
    assert cfg.model == "gpt-4o-mini"
    assert cfg.allow_mutations is True
    assert cfg.structured_output is True
    assert cfg.max_tool_hops == 6
    assert cfg.max_tokens == 2048
