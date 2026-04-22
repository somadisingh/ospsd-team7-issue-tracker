"""Tests for ClaudeConfig env parsing."""

from __future__ import annotations

import pytest
from claude_ai_client_impl.config import (
    DEFAULT_MAX_HOPS,
    DEFAULT_MODEL,
    ClaudeConfig,
)


@pytest.mark.unit
class TestClaudeConfigFromEnv:
    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            ClaudeConfig.from_env()

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxxx")
        for key in (
            "CLAUDE_MODEL",
            "AI_MAX_TOOL_HOPS",
            "AI_ALLOW_MUTATIONS",
            "AI_MAX_TOKENS",
        ):
            monkeypatch.delenv(key, raising=False)

        config = ClaudeConfig.from_env()
        assert config.model == DEFAULT_MODEL
        assert config.max_tool_hops == DEFAULT_MAX_HOPS
        assert config.allow_mutations is False

    def test_allow_mutations_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxxx")
        monkeypatch.setenv("AI_ALLOW_MUTATIONS", "true")
        assert ClaudeConfig.from_env().allow_mutations is True

    def test_allow_mutations_false_on_garbage(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxxx")
        monkeypatch.setenv("AI_ALLOW_MUTATIONS", "maybe")
        assert ClaudeConfig.from_env().allow_mutations is False

    def test_int_env_falls_back_on_bad(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxxx")
        monkeypatch.setenv("AI_MAX_TOOL_HOPS", "not-a-number")
        assert ClaudeConfig.from_env().max_tool_hops == DEFAULT_MAX_HOPS
