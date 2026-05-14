"""Service client adapter for the Issue Tracker API.

This package provides ``ServiceClientAdapter``, an implementation of the
``issue_tracker_client_api.Client`` ABC that delegates to the deployed
FastAPI service via the auto-generated HTTP client.

Importing this package and calling ``register()`` replaces the global
``get_client`` factory so that all consumers transparently use the remote
service instead of the local Trello client.
"""

from issue_tracker_adapter.client import ServiceClientAdapter, register

__all__ = [
    "ServiceClientAdapter",
    "register",
]
