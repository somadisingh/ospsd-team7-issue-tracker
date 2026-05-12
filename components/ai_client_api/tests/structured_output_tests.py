"""Tests for structured AI envelope parsing."""

from __future__ import annotations

import pytest
from ai_client_api.exceptions import AIStructuredOutputError
from ai_client_api.structured_output import (
    StructuredAIEnvelope,
    parse_structured_envelope,
    system_prompt_with_structured_mode,
)


def test_parse_structured_envelope_ok() -> None:
    text = '  {"reply": "hello", "rationale": "because"}  '
    env = parse_structured_envelope(text)
    assert env.reply == "hello"
    assert env.rationale == "because"


def test_parse_structured_envelope_accepts_markdown_fence() -> None:
    text = '```json\n{"reply": "hi", "rationale": null}\n```'
    env = parse_structured_envelope(text)
    assert env.reply == "hi"
    assert env.rationale is None


def test_parse_structured_envelope_accepts_preamble() -> None:
    text = 'Sure — here you go:\n{"reply": "Listed 2 boards.", "rationale": null}\n'
    env = parse_structured_envelope(text)
    assert env.reply == "Listed 2 boards."
def test_parse_structured_envelope_invalid() -> None:
    with pytest.raises(AIStructuredOutputError):
        parse_structured_envelope("not json")
    with pytest.raises(AIStructuredOutputError):
        parse_structured_envelope('{"reply": ""}')
    with pytest.raises(AIStructuredOutputError):
        parse_structured_envelope("[]")


def test_structured_model() -> None:
    m = StructuredAIEnvelope(reply="x", rationale=None)
    assert m.reply == "x"


def test_system_prompt_with_structured_mode_appends_rules() -> None:
    out = system_prompt_with_structured_mode("BASE", structured_output=True)
    assert out.startswith("BASE")
    assert "Final assistant message" in out
    assert system_prompt_with_structured_mode("BASE", structured_output=False) == "BASE"
