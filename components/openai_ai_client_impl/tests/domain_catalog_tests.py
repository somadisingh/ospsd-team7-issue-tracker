"""Tests for :mod:`openai_ai_client_impl.domain_catalog`."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from ai_client_api.exceptions import AIToolError
from api.issue import Status
from chat_client_api import Channel, Message
from openai_ai_client_impl.domain_catalog import build_domain_catalog


@pytest.mark.unit
def test_update_issue_status_invalid_status_raises() -> None:
    it = MagicMock()
    chat = MagicMock()
    cat = build_domain_catalog(it, chat, allow_mutations=True)
    with pytest.raises(AIToolError, match="Invalid status"):
        cat.dispatch(
            "update_issue_status",
            {"issue_id": "i1", "status": "bogus"},
        )


@pytest.mark.unit
def test_dispatch_hits_issue_tracker_and_chat_tools() -> None:
    board = MagicMock()
    board.id = "b1"
    board.board_name = "B"

    issue = MagicMock()
    issue.id = "i1"
    issue.title = "T"
    issue.desc = None
    issue.status = Status.TO_DO
    issue.due_date = None
    issue.board_id = "b1"

    it = MagicMock()
    it.get_boards.return_value = [board]
    it.get_board.return_value = board
    it.get_issues.return_value = [issue]
    it.get_issue.return_value = issue
    it.create_board.return_value = board
    it.update_board.return_value = board
    it.create_issue.return_value = issue
    it.update_issue.return_value = issue
    it.assign_issue.return_value = True

    ch = Channel(
        channel_id="c1",
        name="general",
        is_private=False,
        channel_type="group",
    )
    msg = Message(
        message_id="c1:1",
        channel="c1",
        text="hi",
        sender="bot",
        timestamp=datetime.now(UTC),
    )

    chat = MagicMock()
    chat.get_channels.return_value = [ch]
    chat.get_channel.return_value = ch
    chat.get_messages.return_value = [msg]
    chat.send_message.return_value = msg

    cat = build_domain_catalog(it, chat, allow_mutations=True)

    assert cat.dispatch("list_boards", {})
    assert cat.dispatch("get_board", {"board_id": "b1"})
    assert cat.dispatch("list_issues_on_board", {"board_id": "b1"})
    assert cat.dispatch("get_issue", {"issue_id": "i1"})
    assert cat.dispatch("create_board", {"name": "N"})
    assert cat.dispatch("rename_board", {"board_id": "b1", "name": "Z"})
    assert cat.dispatch(
        "create_issue",
        {"board_id": "b1", "title": "x", "desc": None},
    )
    assert cat.dispatch("update_issue_status", {"issue_id": "i1", "status": "to_do"})
    assert cat.dispatch("assign_issue", {"issue_id": "i1", "member_id": "m1"}) == {
        "success": True,
    }
    it.assign_issue.assert_called_once_with(issue_id="i1", member_id="m1")
    assert cat.dispatch("list_channels", {})
    assert cat.dispatch("get_channel", {"channel_id": "c1"})
    assert cat.dispatch("get_recent_messages", {"channel_id": "c1", "limit": 5})
    assert cat.dispatch("send_chat_message", {"channel_id": "c1", "text": "x"})
