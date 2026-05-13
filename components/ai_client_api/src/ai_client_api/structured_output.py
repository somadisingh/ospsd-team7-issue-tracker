"""Pydantic envelope for optional structured final assistant payloads."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ai_client_api.exceptions import AIStructuredOutputError


class StructuredAIEnvelope(BaseModel):
    """Validated JSON shape for the model's final natural-language reply."""

    reply: str = Field(min_length=1, max_length=16000)
    rationale: str | None = Field(default=None, max_length=4000)


STRUCTURED_OUTPUT_SYSTEM_APPENDIX = """\
## Final assistant message (mandatory when tools are finished)
Your **entire** assistant message for the user must be **only** one JSON object
(no markdown code fences, no “Here is…” lines before or after the JSON).
Required shape exactly:
{"reply": "<non-empty user-visible answer>", "rationale": null}
or with optional rationale text instead of null.
Do not wrap the JSON in a code block. Do not add any characters outside the object.
"""


def system_prompt_with_structured_mode(base: str, *, structured_output: bool) -> str:
    """Append structured-output rules to ``base`` when that mode is enabled."""
    if not structured_output:
        return base
    return f"{base.rstrip()}\n\n{STRUCTURED_OUTPUT_SYSTEM_APPENDIX}"


def _strip_markdown_json_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    first_nl = s.find("\n")
    if first_nl == -1:
        return s
    body = s[first_nl + 1 :]
    if body.rstrip().endswith("```"):
        body = body.rstrip()[:-3].rstrip()
    return body.strip()


def _decode_loose_json_object(text: str) -> object:
    """Parse the first JSON object in ``text``, tolerating preamble and fenced blocks."""
    s = _strip_markdown_json_fence(text).strip()
    dec = json.JSONDecoder()
    lead = s.lstrip()
    try:
        return dec.raw_decode(lead)[0]
    except json.JSONDecodeError:
        pass
    idx = 0
    while True:
        i = s.find("{", idx)
        if i < 0:
            break
        try:
            return dec.raw_decode(s, i)[0]
        except json.JSONDecodeError:
            idx = i + 1
    raise json.JSONDecodeError("No JSON object found", s, 0)


def parse_structured_envelope(text: str) -> StructuredAIEnvelope:
    """Parse ``text`` as JSON and validate as :class:`StructuredAIEnvelope`.

    Accepts a short prose preamble or a fenced JSON code block when models
    ignore formatting instructions; still rejects invalid envelopes.

    Raises:
        AIStructuredOutputError: if JSON is invalid or validation fails.

    """
    stripped = text.strip()
    try:
        data: Any = _decode_loose_json_object(stripped)
    except json.JSONDecodeError as exc:
        raise AIStructuredOutputError(
            "Final assistant output is not valid JSON."
        ) from exc
    if not isinstance(data, dict):
        msg = "Structured envelope must be a JSON object."
        raise AIStructuredOutputError(msg)
    try:
        return StructuredAIEnvelope.model_validate(data)
    except ValidationError as exc:
        raise AIStructuredOutputError(f"Structured envelope invalid: {exc}") from exc
