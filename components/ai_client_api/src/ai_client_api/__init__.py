"""Public export surface for ``ai_client_api``.

This package is the stable, provider-agnostic contract for an AI assistant.
Concrete providers live in separate ``<provider>_ai_client_impl`` packages
and are wired in via :func:`register_client`.
"""

from ai_client_api.client import AIClient, get_client, register_client
from ai_client_api.exceptions import (
    AIError,
    AIProviderError,
    AIRateLimitError,
    AIStructuredOutputError,
    AIToolError,
    AIToolHopLimitError,
    AIUnsafeRequestError,
)
from ai_client_api.resilience import (
    CircuitBreaker,
    IdempotencyMemory,
    RetryPolicy,
    call_with_resilience,
    current_idempotency_key,
    idempotency_scope,
)
from ai_client_api.signature_tools import SignatureToolCatalog, build_argument_model
from ai_client_api.structured_output import (
    StructuredAIEnvelope,
    parse_structured_envelope,
    system_prompt_with_structured_mode,
)
from ai_client_api.tool import Tool, ToolDispatcher
from ai_client_api.types import AIReply, ToolAction

__all__ = [
    "AIClient",
    "AIError",
    "AIProviderError",
    "AIRateLimitError",
    "AIReply",
    "AIStructuredOutputError",
    "AIToolError",
    "AIToolHopLimitError",
    "AIUnsafeRequestError",
    "CircuitBreaker",
    "IdempotencyMemory",
    "RetryPolicy",
    "SignatureToolCatalog",
    "StructuredAIEnvelope",
    "Tool",
    "ToolAction",
    "ToolDispatcher",
    "build_argument_model",
    "call_with_resilience",
    "current_idempotency_key",
    "get_client",
    "idempotency_scope",
    "parse_structured_envelope",
    "register_client",
    "system_prompt_with_structured_mode",
]
