"""Fixtures for claude_ai_client_impl tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from api.issue import Status
from chat_client_impl import LocalChatClient
from claude_ai_client_impl.config import ClaudeConfig


@pytest.fixture
def mock_issue_tracker() -> MagicMock:
    """MagicMock with realistic domain-object return values."""
    it = MagicMock(name="IssueTrackerClient")

    board = MagicMock()
    board.id = "b1"
    board.board_name = "Sprint 5"
    it.get_boards.return_value = [board]
    it.get_board.return_value = board

    issue = MagicMock()
    issue.id = "i1"
    issue.title = "Fix Safari export"
    issue.desc = "reported by alice"
    issue.status = Status.TO_DO
    issue.due_date = None
    issue.board_id = "b1"
    it.get_issues.return_value = [issue]
    it.get_issue.return_value = issue
    it.create_issue.return_value = issue
    it.update_issue.return_value = issue
    return it


@pytest.fixture
def mock_chat() -> LocalChatClient:
    """Seeded in-memory ChatClient (replaces the deleted MockChatClient)."""
    return LocalChatClient(seeded=True)


@pytest.fixture
def default_config() -> ClaudeConfig:
    return ClaudeConfig(
        api_key="sk-ant-test-00000000000000000000",
        model="claude-sonnet-4-5",
        max_tool_hops=4,
        allow_mutations=True,
        max_tokens=256,
    )


class _FakeResponse:
    """Stand-in for anthropic.types.Message used by the client loop."""

    def __init__(self, content: list[dict[str, Any]], stop_reason: str) -> None:
        self.content = content
        self.stop_reason = stop_reason


def make_response(
    *blocks: dict[str, Any],
    stop_reason: str = "end_turn",
) -> _FakeResponse:
    return _FakeResponse(list(blocks), stop_reason)


@pytest.fixture
def response_factory() -> Any:
    return make_response


class _FakeAnthropic:
    """Return canned responses from ``messages.create`` in order."""

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

        class _Messages:
            def __init__(self, outer: _FakeAnthropic) -> None:
                self._outer = outer

            def create(self, **kwargs: Any) -> _FakeResponse:
                self._outer.calls.append(kwargs)
                if not self._outer._responses:
                    msg = "No more canned responses."
                    raise RuntimeError(msg)
                return self._outer._responses.pop(0)

        self.messages = _Messages(self)


@pytest.fixture
def fake_anthropic_factory() -> Any:
    return _FakeAnthropic
