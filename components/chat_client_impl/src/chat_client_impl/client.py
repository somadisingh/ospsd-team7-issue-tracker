"""Local in-memory implementation of the shared chat client contract."""

from __future__ import annotations

from datetime import datetime

from chat_client_api import (
    Channel,
    ChannelNotFoundError,
    ChatClient,
    Message,
    MessageDeleteError,
    MessageNotFoundError,
)


class LocalChatClient(ChatClient):
    """A simple chat client that keeps messages in memory."""

    def __init__(self) -> None:
        """Initialize an empty local message store."""
        self._messages: dict[str, Message] = {}

    def send_message(self, channel_id: str, text: str) -> Message:
        """Send a message to the provided channel ID and store it in memory."""
        now = datetime.now(datetime.UTC)
        message_id = f"{channel_id}:{now.isoformat()}"

        message = Message(
            message_id=message_id,
            channel=channel_id,
            text=text,
            sender="local-bot",
            timestamp=now,
        )

        self._messages[message_id] = message
        return message

    def get_channels(self) -> list[Channel]:
        """Return the list of channels tracked by this client."""
        return []

    def get_channel(self, channel_id: str) -> Channel:
        """Look up a channel by ID. Not supported in this local implementation."""
        raise ChannelNotFoundError

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Message]:
        """Return recent messages for the requested channel ID."""
        if cursor is not None:
            pass

        channel_messages = [
            message for message in self._messages.values() if message.channel == channel_id
        ]
        channel_messages.sort(key=lambda message: message.timestamp, reverse=True)
        return channel_messages[:limit]

    def get_message(self, message_id: str) -> Message:
        """Return a previously sent message by its opaque ID."""
        if message_id not in self._messages:
            raise MessageNotFoundError
        return self._messages[message_id]

    def delete_message(self, message_id: str) -> None:
        """Remove a stored message by its opaque ID."""
        if message_id not in self._messages:
            raise MessageDeleteError
        del self._messages[message_id]


def get_client_impl() -> ChatClient:
    """Return a fresh LocalChatClient instance for the shared factory."""
    return LocalChatClient()
