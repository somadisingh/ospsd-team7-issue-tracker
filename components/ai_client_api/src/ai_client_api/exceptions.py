"""Domain-specific exceptions for the AI client.

These exceptions are part of the public contract so callers (e.g. the
FastAPI route) can map them to HTTP status codes without depending on
provider-specific error types.
"""


class AIError(Exception):
    """Base exception for all AI client domain errors."""


class AIProviderError(AIError):
    """Raised when the upstream LLM provider fails.

    Examples: rate limits, 5xx from the provider, network timeouts,
    malformed responses.
    """


class AIUnsafeRequestError(AIError):
    """Raised when a request is rejected by a safety guard before any LLM call.

    Examples: prompt exceeds maximum length, suspected attempt to exfiltrate
    server secrets.
    """


class AIToolError(AIError):
    """Raised when the LLM proposes a tool call that cannot be executed.

    Examples: unknown tool name, Pydantic validation failure on arguments,
    a mutating tool is proposed while ``AI_ALLOW_MUTATIONS=false``.
    """


class AIToolHopLimitError(AIError):
    """Raised when the model/tool interaction loop exceeds the hop limit.

    Implementations may choose to raise this OR surface the partial reply
    with ``AIReply.truncated=True`` instead. Raising is appropriate when
    there is no coherent partial reply to return.
    """


class AIStructuredOutputError(AIError):
    """Raised when the model output cannot be validated as structured data.

    Used when ``AI_STRUCTURED_OUTPUT`` (or provider-specific structured mode)
    is enabled and the final assistant payload is not valid JSON or fails
    Pydantic validation.
    """


class AIRateLimitError(AIProviderError):
    """Raised when the upstream provider signals rate limiting."""
