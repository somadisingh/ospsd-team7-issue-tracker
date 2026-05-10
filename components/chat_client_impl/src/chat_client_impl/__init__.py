"""Local chat client implementation package.

Importing this package registers a simple in-memory chat client
implementation with the shared `chat_client_api` contract.
"""

from chat_client_api import register_client

from .client import get_client_impl

# Register the local implementation when this package is imported.
register_client(get_client_impl)

__all__ = ["get_client_impl"]
