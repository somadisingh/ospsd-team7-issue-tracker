"""Unit tests for ai_client_api.types."""

from __future__ import annotations

import pytest
from ai_client_api.types import AIReply, ToolAction


@pytest.mark.unit
class TestToolAction:
    def test_construction(self) -> None:
        action = ToolAction(tool="get_issue", arguments={"issue_id": "1"}, ok=True)
        assert action.tool == "get_issue"
        assert action.ok is True
        assert action.error is None

    def test_error_field(self) -> None:
        action = ToolAction(tool="x", arguments={}, ok=False, error="unknown tool")
        assert action.ok is False
        assert action.error == "unknown tool"

    def test_frozen(self) -> None:
        action = ToolAction(tool="x", arguments={}, ok=True)
        with pytest.raises(AttributeError):
            action.tool = "y"  # type: ignore[misc]


@pytest.mark.unit
class TestAIReply:
    def test_defaults(self) -> None:
        reply = AIReply(reply="hi")
        assert reply.actions == []
        assert reply.truncated is False

    def test_actions_list(self) -> None:
        action = ToolAction(tool="a", arguments={}, ok=True)
        reply = AIReply(reply="done", actions=[action], truncated=True)
        assert reply.actions == [action]
        assert reply.truncated is True
