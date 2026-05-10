"""Tests for allow-listed serializers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from api.issue import Status
from chat_client_api import Channel, Message
from claude_ai_client_impl import serializers


@pytest.mark.unit
class TestSerializeIssue:
    def test_fields_are_allow_listed(self) -> None:
        issue = MagicMock()
        issue.id = "i1"
        issue.title = "hello world"
        issue.desc = "long body " * 100
        issue.status = Status.IN_PROGRESS
        issue.due_date = "2026-05-01"
        issue.board_id = "b1"
        out = serializers.serialize_issue(issue)
        assert set(out) == {
            "id",
            "title",
            "status",
            "desc_snippet",
            "due_date",
            "board_id",
        }
        assert out["status"] == "in_progress"
        assert len(out["desc_snippet"]) <= 400

    def test_scrubs_secrets_in_title(self) -> None:
        issue = MagicMock()
        issue.id = "i1"
        issue.title = "paste sk-ant-api03-abcdefghijklmnopqrst here"
        issue.desc = ""
        issue.status = Status.TO_DO
        issue.due_date = None
        issue.board_id = "b1"
        out = serializers.serialize_issue(issue)
        assert "sk-ant" not in out["title"]


@pytest.mark.unit
class TestSerializeMember:
    def test_no_email_leak(self) -> None:
        member = MagicMock()
        member.id = "m1"
        member.username = "alice"
        out = serializers.serialize_member(member)
        assert set(out) == {"id", "display_name"}


@pytest.mark.unit
class TestSerializeChannelAndMessage:
    def test_channel(self) -> None:
        channel = Channel(
            channel_id="C1",
            name="general",
            is_private=False,
            channel_type="group",
        )
        assert serializers.serialize_channel(channel) == {
            "channel_id": "C1",
            "name": "general",
            "is_private": False,
            "channel_type": "group",
        }

    def test_message_scrubs_text_and_truncates(self) -> None:
        big_text = "contact me at alice@example.com " + "x" * 2000
        msg = Message(
            message_id="C1:1",
            channel="C1",
            text=big_text,
            sender="alice",
            timestamp=datetime(2026, 4, 20, tzinfo=UTC),
        )
        out = serializers.serialize_message(msg)
        assert "alice@example.com" not in out["text_snippet"]
        assert len(out["text_snippet"]) <= 400
        assert out["timestamp"].startswith("2026-04-20")
