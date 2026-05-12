"""Tests for the tool dispatcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from ai_client_api.exceptions import AIToolError
from chat_client_impl import LocalChatClient
from claude_ai_client_impl.tools import ToolDispatcher


@pytest.fixture
def dispatcher_rw(
    mock_issue_tracker: MagicMock, mock_chat: LocalChatClient
) -> ToolDispatcher:
    return ToolDispatcher(
        issue_tracker=mock_issue_tracker,
        chat=mock_chat,
        allow_mutations=True,
    )


@pytest.fixture
def dispatcher_ro(
    mock_issue_tracker: MagicMock, mock_chat: LocalChatClient
) -> ToolDispatcher:
    return ToolDispatcher(
        issue_tracker=mock_issue_tracker,
        chat=mock_chat,
        allow_mutations=False,
    )


@pytest.mark.unit
class TestSchemas:
    def test_catalogue_contains_expected_tools(
        self, dispatcher_rw: ToolDispatcher
    ) -> None:
        names = {s["name"] for s in dispatcher_rw.schemas()}
        assert {
            "list_boards",
            "get_board",
            "list_issues_on_board",
            "get_issue",
            "create_issue",
            "update_issue_status",
            "assign_issue",
            "list_channels",
            "get_channel",
            "get_recent_messages",
            "send_chat_message",
        } <= names

    def test_ro_mode_strips_mutating(self, dispatcher_ro: ToolDispatcher) -> None:
        names = {s["name"] for s in dispatcher_ro.schemas()}
        assert "create_issue" not in names
        assert "update_issue_status" not in names
        assert "assign_issue" not in names
        assert "send_chat_message" not in names

    def test_no_delete_tools_anywhere(self, dispatcher_rw: ToolDispatcher) -> None:
        names = dispatcher_rw.known_tool_names()
        assert all("delete" not in n for n in names)


@pytest.mark.unit
class TestDispatch:
    def test_unknown_tool_raises(self, dispatcher_rw: ToolDispatcher) -> None:
        with pytest.raises(AIToolError, match="Unknown tool"):
            dispatcher_rw.dispatch("sudo_delete_everything", {})

    def test_mutating_tool_blocked_in_ro_mode(
        self,
        dispatcher_ro: ToolDispatcher,
    ) -> None:
        with pytest.raises(AIToolError, match="mutating"):
            dispatcher_ro.dispatch("create_issue", {"board_id": "b1", "title": "x"})

    def test_bad_args_raise(self, dispatcher_rw: ToolDispatcher) -> None:
        with pytest.raises(AIToolError, match="Invalid arguments"):
            dispatcher_rw.dispatch("get_issue", {})  # missing issue_id

    def test_list_boards_returns_serialized(
        self,
        dispatcher_rw: ToolDispatcher,
        mock_issue_tracker: MagicMock,
    ) -> None:
        result = dispatcher_rw.dispatch("list_boards", {})
        assert result == [{"id": "b1", "name": "Sprint 5"}]
        mock_issue_tracker.get_boards.assert_called_once()

    def test_list_issues_returns_serialized(
        self,
        dispatcher_rw: ToolDispatcher,
        mock_issue_tracker: MagicMock,
    ) -> None:
        result = dispatcher_rw.dispatch("list_issues_on_board", {"board_id": "b1"})
        assert isinstance(result, list)
        assert result[0]["id"] == "i1"
        assert result[0]["status"] == "to_do"
        assert "title" in result[0]
        mock_issue_tracker.get_issues.assert_called_with("b1")

    def test_create_issue_runs_and_returns_serialized(
        self,
        dispatcher_rw: ToolDispatcher,
        mock_issue_tracker: MagicMock,
    ) -> None:
        result = dispatcher_rw.dispatch(
            "create_issue",
            {"board_id": "b1", "title": "New bug", "desc": "details"},
        )
        assert result["id"] == "i1"
        mock_issue_tracker.create_issue.assert_called_once()

    def test_update_issue_status_rejects_bad_status(
        self,
        dispatcher_rw: ToolDispatcher,
    ) -> None:
        with pytest.raises(AIToolError, match="Invalid status"):
            dispatcher_rw.dispatch(
                "update_issue_status",
                {"issue_id": "i1", "status": "pending"},
            )

    def test_update_issue_status_ok(
        self,
        dispatcher_rw: ToolDispatcher,
        mock_issue_tracker: MagicMock,
    ) -> None:
        result = dispatcher_rw.dispatch(
            "update_issue_status",
            {"issue_id": "i1", "status": "completed"},
        )
        assert result["id"] == "i1"
        mock_issue_tracker.update_issue.assert_called_once()

    def test_assign_issue_calls_client(
        self,
        dispatcher_rw: ToolDispatcher,
        mock_issue_tracker: MagicMock,
    ) -> None:
        result = dispatcher_rw.dispatch(
            "assign_issue",
            {"issue_id": "i1", "member_id": "mem42"},
        )
        assert result == {"success": True}
        mock_issue_tracker.assign_issue.assert_called_once_with(
            issue_id="i1",
            member_id="mem42",
        )

    def test_get_recent_messages_from_mock_chat(
        self,
        dispatcher_rw: ToolDispatcher,
    ) -> None:
        result = dispatcher_rw.dispatch(
            "get_recent_messages",
            {"channel_id": "C0123SUPPORT", "limit": 5},
        )
        assert len(result) >= 1
        assert result[0]["channel_id"] == "C0123SUPPORT"

    def test_send_chat_message_writes_to_mock_chat(
        self,
        dispatcher_rw: ToolDispatcher,
        mock_chat: LocalChatClient,
    ) -> None:
        before = len(mock_chat.get_messages("C0123ENG", limit=50))
        dispatcher_rw.dispatch(
            "send_chat_message",
            {"channel_id": "C0123ENG", "text": "hello"},
        )
        after = len(mock_chat.get_messages("C0123ENG", limit=50))
        assert after == before + 1
