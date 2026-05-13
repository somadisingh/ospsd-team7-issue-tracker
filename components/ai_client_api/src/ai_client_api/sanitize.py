"""Pre-flight sanitization helpers.

Called on every user prompt (and every tool-result payload) before any
LLM call. The goal is *defense in depth*, not completeness: the LLM must
never be the last line of defense for keeping a secret off the wire.

Rules implemented here:

* Cap prompt size.
* Redact obvious secret shapes: API keys, bearer/OAuth tokens, AWS keys,
  email addresses, phone numbers.
* Strip ANSI / control characters that could be used to hide instructions.
"""

from __future__ import annotations

import re
from typing import Final

# Hard cap on prompt length (characters). A long prompt should be rejected
# rather than silently truncated so the user gets a clear error.
MAX_PROMPT_CHARS: Final[int] = 8000

# Default replacement token used for redaction.
REDACTION: Final[str] = "[redacted]"

# Compiled once — these run on every request.
_PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    # Anthropic keys:    sk-ant-…  (any provider "sk-…" style)
    (re.compile(r"\bsk-[a-z0-9-]{20,}\b", re.IGNORECASE), REDACTION),
    # OpenAI-style keys starting with "sk-proj-" also match the above.
    # AWS access key IDs
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), REDACTION),
    # Bearer tokens in headers
    (re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}\b"), "Bearer " + REDACTION),
    # Generic OAuth tokens: long base64url-ish strings with "token" nearby
    (
        re.compile(
            r"\b(oauth[_-]?token|access[_-]?token|session[_-]?token)\s*[:=]\s*[A-Za-z0-9._\-]{16,}",
            re.IGNORECASE,
        ),
        r"\1=" + REDACTION,
    ),
    # Email addresses — PII. (RFC-lite; fine for scrubbing.)
    (
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        REDACTION,
    ),
    # Phone numbers (simple North-American / international)
    (
        re.compile(r"(?<!\d)(\+?\d[\d\- ]{7,}\d)(?!\d)"),
        REDACTION,
    ),
)

# ANSI escape sequences and other control chars except \n, \r, \t.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def enforce_length(prompt: str) -> None:
    """Raise ``ValueError`` if ``prompt`` exceeds :data:`MAX_PROMPT_CHARS`."""
    if len(prompt) > MAX_PROMPT_CHARS:
        msg = f"Prompt is {len(prompt)} characters; limit is {MAX_PROMPT_CHARS}."
        raise ValueError(msg)


def scrub(text: str) -> str:
    """Return ``text`` with secret/PII shapes redacted.

    Safe to call on user prompts, tool-result payloads, or any other
    string that will be forwarded to the LLM provider.
    """
    cleaned = _CONTROL_CHARS.sub("", text)
    for pattern, replacement in _PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def sanitize_prompt(prompt: str) -> str:
    """Validate + scrub a user-supplied prompt in one call.

    Raises:
        ValueError: if the prompt is too long.

    """
    enforce_length(prompt)
    return scrub(prompt)
