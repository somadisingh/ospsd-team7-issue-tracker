"""Local chat client implementation package.

Importing this module registers a seeded in-memory :class:`LocalChatClient`
with the shared ``chat_client_api`` contract. Tests that need an empty
client may re-register :func:`get_client_impl` (the unseeded factory) in a
fixture.

The companion ``chat_client_impl.slack`` module provides the cross-vertical
adapter for Team 9's Slack implementation; it is loaded on demand by
``issue_tracker_service.ai_deps`` based on the ``CHAT_BACKEND`` env var.
"""

from chat_client_api import register_client

from .client import LocalChatClient, get_client_impl, get_seeded_client_impl


def register() -> None:
    """Register the seeded local fake as the active ``ChatClient`` factory.

    Callable explicitly by ``ai_deps._chat_client`` so re-resolving the
    "local" backend always re-registers, even if another test changed
    the registry mid-process.
    """
    register_client(get_seeded_client_impl)


register()

__all__ = [
    "LocalChatClient",
    "get_client_impl",
    "get_seeded_client_impl",
    "register",
]
