"""Public export surface for ``ai_client_api``.

This package is the stable, provider-agnostic contract for an AI assistant.
Concrete providers live in separate ``<provider>_ai_client_impl`` packages
and are wired in via :func:`register_client`.
"""

from ai_client_api.client import AIClient, get_client, register_client
from ai_client_api.exceptions import (
    AIError,
    AIProviderError,
    AIToolError,
    AIToolHopLimitError,
    AIUnsafeRequestError,
)
from ai_client_api.tool import Tool, ToolDispatcher
from ai_client_api.types import AIReply, ToolAction

__all__ = [
    "AIClient",
    "AIError",
    "AIProviderError",
    "AIReply",
    "AIToolError",
    "AIToolHopLimitError",
    "AIUnsafeRequestError",
    "Tool",
    "ToolAction",
    "ToolDispatcher",
    "get_client",
    "register_client",
]
