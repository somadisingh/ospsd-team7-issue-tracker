"""Local in-memory implementation of the shared chat client contract."""

from __future__ import annotations

from datetime import datetime, timezone

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
        # Store messages by their opaque message ID.
        self._messages: dict[str, Message] = {}

    def send_message(self, channel_id: str, text: str) -> Message:
        # Send a message to a channel identifier and return the saved Message object.
        # This local implementation does not validate that the channel exists first.
        now = datetime.now(timezone.utc)
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
        # This local implementation does not track channel objects.
        return []

    def get_channel(self, channel_id: str) -> Channel:
        # Channel lookup is not supported by this local implementation.
        raise ChannelNotFoundError(f"Channel not found: {channel_id}")

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Message]:
        # Cursor support is optional in the shared contract, and this local
        # storage implementation keeps it simple by ignoring pagination.
        channel_messages = [
            message for message in self._messages.values() if message.channel == channel_id
        ]
        channel_messages.sort(key=lambda message: message.timestamp, reverse=True)
        return channel_messages[:limit]

    def get_message(self, message_id: str) -> Message:
        # Return a previously sent message by its opaque ID.
        if message_id not in self._messages:
            raise MessageNotFoundError(f"Message not found: {message_id}")
        return self._messages[message_id]

    def delete_message(self, message_id: str) -> None:
        # Delete a message from the local store. If it is missing, raise an error.
        if message_id not in self._messages:
            raise MessageDeleteError(f"Cannot delete message: {message_id}")
        del self._messages[message_id]


def get_client_impl() -> ChatClient:
    """Return a fresh LocalChatClient instance for the shared factory."""
    return LocalChatClient()
