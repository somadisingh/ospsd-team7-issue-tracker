"""Local in-memory implementation of the shared chat client contract.

Used as the default backend when ``CHAT_BACKEND`` is unset (or ``"local"``)
so the AI tool dispatcher has a usable :class:`ChatClient` for development,
unit tests, and CI without needing a real Slack/Discord workspace.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime

from chat_client_api import (  # type: ignore[import-untyped]
    Channel,
    ChannelNotFoundError,
    ChatClient,
    Message,
    MessageDeleteError,
    MessageNotFoundError,
)


def _default_channels() -> dict[str, Channel]:
    return {
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


def _default_messages() -> dict[str, list[Message]]:
    return {
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
        ],
    }


class LocalChatClient(ChatClient):  # type: ignore[misc]
    """In-memory :class:`ChatClient`.

    By default the store is empty. Pass ``seeded=True`` (or use the
    :func:`get_seeded_client_impl` factory) to start with a deterministic
    set of channels and messages — useful for the AI tool-call demo and
    integration tests.
    """

    def __init__(self, *, seeded: bool = False) -> None:
        """Initialize the in-memory store, optionally with seed data."""
        if seeded:
            self._channels: dict[str, Channel] = _default_channels()
            self._messages_by_channel: dict[str, list[Message]] = _default_messages()
        else:
            self._channels = {}
            self._messages_by_channel = {}
        self._messages: dict[str, Message] = {
            m.message_id: m
            for messages in self._messages_by_channel.values()
            for m in messages
        }
        self._counter = itertools.count(100)

    def send_message(self, channel_id: str, text: str) -> Message:
        """Send a message to ``channel_id`` and store it in memory."""
        now = datetime.now(UTC)
        if self._channels and channel_id not in self._channels:
            raise ChannelNotFoundError(channel_id)
        message_id = f"{channel_id}:{next(self._counter)}-{now.isoformat()}"
        message = Message(
            message_id=message_id,
            channel=channel_id,
            text=text,
            sender="local-bot",
            timestamp=now,
        )
        self._messages[message_id] = message
        self._messages_by_channel.setdefault(channel_id, []).append(message)
        return message

    def get_channels(self) -> list[Channel]:
        """Return the list of channels tracked by this client."""
        return list(self._channels.values())

    def get_channel(self, channel_id: str) -> Channel:
        """Return a single channel by ID, or raise if unknown."""
        channel = self._channels.get(channel_id)
        if channel is None:
            raise ChannelNotFoundError(channel_id)
        return channel

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Message]:
        """Return recent messages for ``channel_id`` (most recent first)."""
        del cursor
        channel_messages = list(self._messages_by_channel.get(channel_id, []))
        if not channel_messages:
            channel_messages = [
                m for m in self._messages.values() if m.channel == channel_id
            ]
        channel_messages.sort(key=lambda m: m.timestamp, reverse=True)
        return channel_messages[:limit]

    def get_message(self, message_id: str) -> Message:
        """Return a previously sent message by its opaque ID."""
        if message_id not in self._messages:
            raise MessageNotFoundError(message_id)
        return self._messages[message_id]

    def delete_message(self, message_id: str) -> None:
        """Remove a stored message by its opaque ID."""
        if message_id not in self._messages:
            raise MessageDeleteError(message_id)
        message = self._messages.pop(message_id)
        bucket = self._messages_by_channel.get(message.channel, [])
        self._messages_by_channel[message.channel] = [
            m for m in bucket if m.message_id != message_id
        ]


def get_client_impl() -> ChatClient:
    """Return an empty :class:`LocalChatClient` (HW1-style factory)."""
    return LocalChatClient()


def get_seeded_client_impl() -> ChatClient:
    """Return a pre-seeded :class:`LocalChatClient` for AI/integration use."""
    return LocalChatClient(seeded=True)
