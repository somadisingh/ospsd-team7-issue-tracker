"""Adapter from Team 9's ``slack_client_impl.SlackClient`` to our ABC.

Team 9 ships a working Slack ``ChatClient`` (HW3 §5 cross-vertical
integration) but it was written against an in-repo workspace copy of
``chat_client_api`` that diverges from the canonical ``Shared-API@main`` we
pin:

* Their ``Message.timestamp`` is ``str`` (Slack ``ts`` like ``"1715300123.001"``);
  ours is ``datetime`` (timezone-aware).
* They raise plain ``ValueError`` for everything; we have typed
  ``ChatError`` / ``ChannelNotFoundError`` / ``MessageNotFoundError`` /
  ``MessageDeleteError``.

This module is the bridge. It:

1. Wraps ``SlackClient`` so the rest of our codebase keeps the canonical
   contract guarantees (``serializers.serialize_message`` calls
   ``.isoformat()`` on the timestamp, which would crash on a raw Slack
   ``ts`` string).
2. Maps ``ValueError`` to the typed exception subclasses our error
   handling expects.
3. Re-registers itself via ``chat_client_api.register_client`` so
   ``get_client()`` returns the wrapped adapter, not the raw
   ``SlackClient`` that Team 9's ``__init__.py`` registered first.

The day Team 9 syncs their workspace ABC with ``Shared-API@main``, this
module becomes a no-op shim and can be deleted.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from chat_client_api import (  # type: ignore[import-untyped]
    ChannelNotFoundError,
    ChatClient,
    ChatError,
    Message,
    MessageDeleteError,
    MessageNotFoundError,
    register_client,
)
from slack_client_impl.client import SlackClient

if TYPE_CHECKING:
    from chat_client_api import Channel  # type: ignore[import-untyped]


def _to_datetime(slack_ts: object) -> datetime:
    """Convert a Slack ``ts`` (epoch seconds as string) to tz-aware datetime."""
    if isinstance(slack_ts, datetime):
        return slack_ts
    try:
        return datetime.fromtimestamp(float(str(slack_ts)), tz=UTC)
    except (TypeError, ValueError):
        return datetime.now(tz=UTC)


def _normalize(msg: Message) -> Message:
    """Return a Message whose ``timestamp`` is a tz-aware ``datetime``."""
    if isinstance(msg.timestamp, datetime):
        return msg
    return Message(
        message_id=msg.message_id,
        channel=msg.channel,
        text=msg.text,
        sender=msg.sender,
        timestamp=_to_datetime(msg.timestamp),
    )


class SlackChatAdapter(ChatClient):  # type: ignore[misc]
    """Wraps Team 9's :class:`SlackClient` to the canonical ChatClient ABC.

    Every method delegates to the inner client, then normalizes the result
    or maps exceptions so consumers get the contract they expect.
    """

    def __init__(self, inner: SlackClient) -> None:
        """Bind the underlying Slack client.

        Args:
            inner: A configured :class:`SlackClient` from Team 9.

        """
        self._inner = inner

    def send_message(self, channel_id: str, text: str) -> Message:
        try:
            return _normalize(self._inner.send_message(channel_id, text))
        except ValueError as exc:
            raise ChatError(str(exc)) from exc

    def get_channels(self) -> list[Channel]:
        return list(self._inner.get_channels())

    def get_channel(self, channel_id: str) -> Channel:
        try:
            return self._inner.get_channel(channel_id)
        except ValueError as exc:
            raise ChannelNotFoundError(str(exc)) from exc

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Message]:
        return [
            _normalize(m) for m in self._inner.get_messages(channel_id, limit, cursor)
        ]

    def get_message(self, message_id: str) -> Message:
        try:
            return _normalize(self._inner.get_message(message_id))
        except ValueError as exc:
            raise MessageNotFoundError(str(exc)) from exc

    def delete_message(self, message_id: str) -> None:
        try:
            self._inner.delete_message(message_id)
        except ValueError as exc:
            raise MessageDeleteError(str(exc)) from exc


def make_slack_adapter() -> SlackChatAdapter:
    """Build a :class:`SlackChatAdapter` from the ``SLACK_BOT_TOKEN`` env var.

    Raises:
        KeyError: If ``SLACK_BOT_TOKEN`` is not set. We fail loudly at
            startup rather than at first send-message so misconfiguration
            is obvious.

    """
    token = os.environ["SLACK_BOT_TOKEN"]
    return SlackChatAdapter(SlackClient(token))


def register() -> None:
    """Register the Slack adapter as the active ``ChatClient`` factory.

    Callable explicitly by ``ai_deps._chat_client`` so we get
    last-write-wins behaviour every time CHAT_BACKEND=slack is resolved,
    regardless of whether other tests in the same process previously
    registered a different factory.
    """
    register_client(make_slack_adapter)


# Eager registration on import keeps the auto-discovery pattern working
# for callers that just `import chat_client_impl.slack`. The explicit
# register() above is what `_chat_client` calls every time, so test
# ordering cannot leave a stale factory behind.
register()
