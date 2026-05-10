"""Unit tests for the Team 9 Slack adapter.

These tests mock the inner ``SlackClient`` so no real Slack workspace is
required. The adapter's job is to (a) normalize Slack ``ts`` strings into
tz-aware ``datetime`` instances and (b) convert their plain ``ValueError``
into our typed ``ChatError`` subclasses.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from chat_client_api import (
    Channel,
    ChannelNotFoundError,
    ChatError,
    Message,
    MessageDeleteError,
    MessageNotFoundError,
)
from chat_client_impl.slack import SlackChatAdapter, _to_datetime, make_slack_adapter


def _slack_message(ts: str = "1715300123.001", text: str = "hi") -> Message:
    """Build a Message with a string timestamp the way Team 9 does."""
    return Message(
        message_id=f"C0123ENG:{ts}",
        channel="C0123ENG",
        text=text,
        sender="U001",
        timestamp=ts,  # type: ignore[arg-type]  # intentional ABC violation
    )


@pytest.fixture
def inner() -> MagicMock:
    return MagicMock(name="SlackClient")


@pytest.fixture
def adapter(inner: MagicMock) -> SlackChatAdapter:
    return SlackChatAdapter(inner)


@pytest.mark.unit
class TestTimestampNormalization:
    def test_slack_ts_string_becomes_datetime(self) -> None:
        result = _to_datetime("1715300123.5")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_already_datetime_passes_through(self) -> None:
        now = datetime.now(tz=datetime.now().astimezone().tzinfo)
        assert _to_datetime(now) == now

    def test_garbage_falls_back_to_now(self) -> None:
        result = _to_datetime("not-a-timestamp")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


@pytest.mark.unit
class TestSendMessage:
    def test_returns_message_with_datetime_timestamp(
        self, adapter: SlackChatAdapter, inner: MagicMock
    ) -> None:
        inner.send_message.return_value = _slack_message()
        result = adapter.send_message("C0123ENG", "hi")
        assert isinstance(result.timestamp, datetime), (
            "Adapter must convert Slack ts string → datetime, otherwise "
            "downstream serializers crash on .isoformat()."
        )
        assert result.text == "hi"
        inner.send_message.assert_called_once_with("C0123ENG", "hi")

    def test_value_error_becomes_chat_error(
        self, adapter: SlackChatAdapter, inner: MagicMock
    ) -> None:
        inner.send_message.side_effect = ValueError("not_in_channel")
        with pytest.raises(ChatError) as exc:
            adapter.send_message("C0BAD", "hi")
        assert "not_in_channel" in str(exc.value)


@pytest.mark.unit
class TestGetChannel:
    def test_value_error_becomes_channel_not_found_error(
        self, adapter: SlackChatAdapter, inner: MagicMock
    ) -> None:
        inner.get_channel.side_effect = ValueError("Channel not found: C0XX")
        with pytest.raises(ChannelNotFoundError):
            adapter.get_channel("C0XX")

    def test_happy_path_returns_inner_channel(
        self, adapter: SlackChatAdapter, inner: MagicMock
    ) -> None:
        ch = Channel(channel_id="C0123ENG", name="eng", is_private=False)
        inner.get_channel.return_value = ch
        assert adapter.get_channel("C0123ENG") is ch


@pytest.mark.unit
class TestGetMessages:
    def test_normalizes_every_message_timestamp(
        self, adapter: SlackChatAdapter, inner: MagicMock
    ) -> None:
        inner.get_messages.return_value = [
            _slack_message(ts="1715300123.001", text="m1"),
            _slack_message(ts="1715300124.002", text="m2"),
        ]
        result = adapter.get_messages("C0123ENG", limit=10)
        assert len(result) == 2
        assert all(isinstance(m.timestamp, datetime) for m in result)


@pytest.mark.unit
class TestGetMessage:
    def test_value_error_becomes_message_not_found_error(
        self, adapter: SlackChatAdapter, inner: MagicMock
    ) -> None:
        inner.get_message.side_effect = ValueError("Message not found: C:1")
        with pytest.raises(MessageNotFoundError):
            adapter.get_message("C0123ENG:1")

    def test_normalizes_returned_timestamp(
        self, adapter: SlackChatAdapter, inner: MagicMock
    ) -> None:
        inner.get_message.return_value = _slack_message()
        result = adapter.get_message("C0123ENG:1715300123.001")
        assert isinstance(result.timestamp, datetime)


@pytest.mark.unit
class TestDeleteMessage:
    def test_value_error_becomes_message_delete_error(
        self, adapter: SlackChatAdapter, inner: MagicMock
    ) -> None:
        inner.delete_message.side_effect = ValueError("Failed to delete")
        with pytest.raises(MessageDeleteError):
            adapter.delete_message("C0123ENG:1715300123.001")


@pytest.mark.unit
class TestMakeSlackAdapter:
    def test_missing_token_raises_keyerror(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        with pytest.raises(KeyError):
            make_slack_adapter()

    def test_with_token_constructs_adapter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-not-real")
        adapter = make_slack_adapter()
        assert isinstance(adapter, SlackChatAdapter)


@pytest.mark.unit
class TestRegistration:
    def test_explicit_register_overrides_team9_factory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Calling chat_client_impl.slack.register() must win.

        Team 9's slack_client_impl/__init__.py calls
        register_client(_create_slack_client) on import. Our module
        exposes register() (called eagerly on import AND by
        ai_deps._chat_client every time CHAT_BACKEND=slack is resolved)
        so we get last-write-wins behaviour regardless of test order.
        """
        from chat_client_api import get_client
        from chat_client_impl import slack

        slack.register()
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-not-real")
        client = get_client()
        assert isinstance(client, SlackChatAdapter)
