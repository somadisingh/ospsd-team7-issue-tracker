"""Unit tests for ai_client_api.sanitize."""

from __future__ import annotations

import pytest
from ai_client_api import sanitize


@pytest.mark.unit
class TestEnforceLength:
    def test_accepts_short_prompt(self) -> None:
        sanitize.enforce_length("short")

    def test_rejects_oversize_prompt(self) -> None:
        big = "a" * (sanitize.MAX_PROMPT_CHARS + 1)
        with pytest.raises(ValueError, match="limit is"):
            sanitize.enforce_length(big)


@pytest.mark.unit
class TestScrub:
    def test_redacts_anthropic_api_key(self) -> None:
        out = sanitize.scrub("key is sk-ant-api03-abcdefghijklmnopqrst done")
        assert "sk-ant" not in out
        assert sanitize.REDACTION in out

    def test_redacts_aws_access_key(self) -> None:
        out = sanitize.scrub("AKIAIOSFODNN7EXAMPLE leaked")
        assert "AKIA" not in out

    def test_redacts_bearer_token(self) -> None:
        out = sanitize.scrub("Authorization: Bearer abcdef1234567890abcdef")
        assert "abcdef1234567890abcdef" not in out
        assert "Bearer " + sanitize.REDACTION in out

    def test_redacts_oauth_token_field(self) -> None:
        out = sanitize.scrub("access_token=aaaaaaaaaaaaaaaaaaaaa done")
        assert "aaaaaaaaaaaaaaaaaaaaa" not in out

    def test_redacts_email(self) -> None:
        out = sanitize.scrub("ping me at alice@example.com please")
        assert "alice@example.com" not in out

    def test_redacts_phone(self) -> None:
        out = sanitize.scrub("call 212-555-1234 now")
        assert "212-555-1234" not in out

    def test_strips_control_chars(self) -> None:
        out = sanitize.scrub("hello\x00\x1bworld")
        assert "\x00" not in out
        assert "\x1b" not in out
        assert out == "helloworld"

    def test_keeps_benign_text(self) -> None:
        assert sanitize.scrub("ship it") == "ship it"


@pytest.mark.unit
class TestSanitizePrompt:
    def test_happy_path(self) -> None:
        out = sanitize.sanitize_prompt("create ticket for README typo")
        assert out == "create ticket for README typo"

    def test_raises_on_oversize(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            sanitize.sanitize_prompt("x" * (sanitize.MAX_PROMPT_CHARS + 1))

    def test_redacts_secret_in_prompt(self) -> None:
        out = sanitize.sanitize_prompt(
            "here is my key sk-ant-api03-abcdefghijklmnopqrst keep it safe"
        )
        assert "sk-ant" not in out
