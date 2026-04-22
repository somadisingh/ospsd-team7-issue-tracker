"""Abstract contract for an AI assistant client.

Providers (Anthropic Claude, OpenAI, …) implement :class:`AIClient` in a
separate package and register a factory via :func:`register_client`.
The FastAPI service depends only on this ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ai_client_api.types import AIReply

__all__ = ["AIClient", "get_client", "register_client"]


class AIClient(ABC):
    """Stateless, provider-agnostic AI assistant contract.

    Each call is independent: the client does not retain conversation
    history. If multi-turn memory is ever needed it should be passed in
    via ``context``.
    """

    @abstractmethod
    def send_message(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AIReply:
        """Answer ``prompt``, optionally calling server tools along the way.

        Args:
            prompt: Free-form user text. Implementations MUST sanitize
                this (length cap + secret/PII scrubbing) before any
                upstream call.
            context: Optional per-request scoping hints (e.g.
                ``{"board_id": "abc", "channel_id": "C0123"}``). Never
                contains credentials; servers inject those separately.

        Returns:
            :class:`~ai_client_api.types.AIReply` with the final natural-
            language answer, the log of tool calls that ran, and a
            ``truncated`` flag.

        Raises:
            AIUnsafeRequestError: rejected by a safety guard before any
                upstream call.
            AIProviderError: upstream provider failed (network, 5xx,
                rate-limit, malformed response).
            AIToolError: an unrecoverable tool-dispatch failure.

        """


# ---------------------------------------------------------------------- #
# Factory registry — same pattern as the chat ABC.
# ---------------------------------------------------------------------- #


class _ClientRegistry:
    """Holds a single registered client factory.

    Kept private so callers only see the public register/get helpers.
    """

    _factory: Callable[[], AIClient] | None = None

    @classmethod
    def set(cls, factory: Callable[[], AIClient]) -> None:
        """Register ``factory`` as the active AI client provider."""
        cls._factory = factory

    @classmethod
    def get(cls) -> Callable[[], AIClient] | None:
        """Return the registered factory, or ``None`` if unregistered."""
        return cls._factory


def register_client(factory: Callable[[], AIClient]) -> None:
    """Register an AI client implementation factory.

    Call this once at application startup (e.g. from an implementation's
    ``__init__.py``) so ``get_client()`` returns the right provider.
    """
    _ClientRegistry.set(factory)


def get_client() -> AIClient:
    """Return an instance of the registered :class:`AIClient`.

    Raises:
        RuntimeError: if no implementation has been registered.

    """
    factory = _ClientRegistry.get()
    if factory is None:
        msg = (
            "No AI client implementation registered. Import a concrete "
            "provider package (e.g. ``claude_ai_client_impl``) to register it."
        )
        raise RuntimeError(msg)
    return factory()
