"""In-memory ``ChatClient`` used for dev + tests before T2 ships a real one.

Lives inside the Claude impl rather than ``ai_client_api`` because it is
an implementation detail, not part of the public AI contract.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime

from chat_client_api import (  # type: ignore[import-untyped]
    Channel,
    ChannelNotFoundError,
    ChatClient,
    Message,
)


class MockChatClient(ChatClient):  # type: ignore[misc]
    """Deterministic fake :class:`ChatClient`.

    Seeded with a couple of channels and messages so the AI can
    meaningfully exercise ``list_channels`` / ``get_recent_messages`` in
    local development and CI.
    """

    def __init__(self) -> None:
        self._channels: dict[str, Channel] = {
            "C0123ENG": Channel(
                channel_id="C0123ENG",
                name="eng",
                is_private=False,
                channel_type="group",
            ),
            "C0123SUPPORT": Channel(
                channel_id="C0123SUPPORT",
                name="support",
                is_private=False,
                channel_type="group",
            ),
        }
        self._messages: dict[str, list[Message]] = {
            "C0123ENG": [
                Message(
                    message_id="C0123ENG:1",
                    channel="C0123ENG",
                    text="Daily standup thread. Drop updates here.",
                    sender="jenny-bot",
                    timestamp=datetime(2026, 4, 20, 13, 0, tzinfo=UTC),
                ),
            ],
            "C0123SUPPORT": [
                Message(
                    message_id="C0123SUPPORT:1",
                    channel="C0123SUPPORT",
                    text="Hi team — our export-to-CSV button crashes on Safari.",
                    sender="alice",
                    timestamp=datetime(2026, 4, 20, 14, 2, tzinfo=UTC),
                ),
                Message(
                    message_id="C0123SUPPORT:2",
                    channel="C0123SUPPORT",
                    text="ack — can you attach the console log?",
                    sender="bob",
                    timestamp=datetime(2026, 4, 20, 14, 4, tzinfo=UTC),
                ),
            ],
        }
        self._counter = itertools.count(100)

    def send_message(self, channel_id: str, text: str) -> Message:
        channel = self._channels.get(channel_id)
        if channel is None:
            raise ChannelNotFoundError(channel_id)
        message = Message(
            message_id=f"{channel_id}:{next(self._counter)}",
            channel=channel_id,
            text=text,
            sender="issue-tracker-bot",
            timestamp=datetime.now(tz=UTC),
        )
        self._messages.setdefault(channel_id, []).append(message)
        return message

    def get_channels(self) -> list[Channel]:
        return list(self._channels.values())

    def get_channel(self, channel_id: str) -> Channel:
        channel = self._channels.get(channel_id)
        if channel is None:
            raise ChannelNotFoundError(channel_id)
        return channel

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,  # noqa: ARG002 - unsupported here
    ) -> list[Message]:
        channel = self._channels.get(channel_id)
        if channel is None:
            raise ChannelNotFoundError(channel_id)
        return list(self._messages.get(channel_id, []))[-limit:]

    def get_message(self, message_id: str) -> Message:
        for messages in self._messages.values():
            for message in messages:
                if message.message_id == message_id:
                    return message
        from chat_client_api import MessageNotFoundError  # type: ignore[import-untyped]

        raise MessageNotFoundError(message_id)

    def delete_message(self, message_id: str) -> None:  # pragma: no cover - not exposed
        # Never exposed as a tool; implement for interface completeness.
        from chat_client_api import MessageDeleteError  # type: ignore[import-untyped]

        for messages in self._messages.values():
            for index, message in enumerate(messages):
                if message.message_id == message_id:
                    del messages[index]
                    return
        raise MessageDeleteError(message_id)
