"""Abstractions for server-side tool execution.

The shape here is deliberately minimal. Each ``Tool`` describes a
single server-side capability that an LLM may propose calling; a
``ToolDispatcher`` bundles the catalogue of tools and is responsible
for validating arguments, enforcing the allow-list, and running the
callable.

Concrete providers (e.g. ``claude_ai_client_impl``) hold their own
dispatcher; tests can inject a stub.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """A single server-side action the LLM may propose.

    ``name`` is the canonical identifier used in tool-use blocks.
    ``description`` is surfaced to the model.
    ``json_schema`` is the JSON Schema for ``arguments`` (draft 2020-12).
    ``mutating`` is ``True`` iff the tool can alter server state.
    """

    name: str
    description: str
    json_schema: dict[str, Any]
    mutating: bool

    def run(self, arguments: dict[str, Any]) -> Any:  # noqa: ANN401 — opaque
        """Execute the tool and return a JSON-serializable result."""
        ...


@runtime_checkable
class ToolDispatcher(Protocol):
    """Registry + executor for :class:`Tool` instances.

    Implementations are expected to:

    * Reject unknown tool names (``AIToolError``).
    * Validate arguments (``AIToolError``).
    * Refuse mutating tools when mutations are disabled (``AIToolError``).
    * Return a JSON-serializable result on success.
    """

    def schemas(self) -> list[dict[str, Any]]:
        """Return the provider-facing schema list for all enabled tools."""
        ...

    def dispatch(self, name: str, arguments: dict[str, Any]) -> Any:  # noqa: ANN401 — opaque
        """Run tool ``name`` with ``arguments`` and return its result."""
        ...
