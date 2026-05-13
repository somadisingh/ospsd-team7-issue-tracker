"""Boundary data classes returned by :meth:`AIClient.send_message`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolAction:
    """Record of a tool the AI asked the server to run.

    Attributes:
        tool: The canonical tool name (e.g. ``"list_issues_on_board"``).
        arguments: The arguments the LLM proposed, after Pydantic
            validation. Never contains server secrets.
        ok: ``True`` if the tool executed without raising.
        error: Short, user-safe error message when ``ok`` is ``False``.
            Never includes stack traces or credentials.

    """

    tool: str
    arguments: dict[str, Any]
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class AIReply:
    """Final payload returned to the caller of :meth:`AIClient.send_message`.

    Attributes:
        reply: Natural-language answer from the LLM.
        actions: Ordered log of tools that were dispatched during the
            request. The caller can echo this back to the user so the
            audit trail is visible.
        truncated: ``True`` if the tool-use loop hit the hop limit and
            ``reply`` is a best-effort partial answer.

    """

    reply: str
    actions: list[ToolAction] = field(default_factory=list)
    truncated: bool = False
