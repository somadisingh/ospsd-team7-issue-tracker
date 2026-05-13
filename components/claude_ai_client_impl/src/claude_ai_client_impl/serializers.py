"""Allow-listed projections for domain objects.

Each function returns a plain ``dict`` containing only fields that are
safe to forward to the LLM. Anything not in the explicit field list is
dropped — the point is that a future property added to a domain class
cannot accidentally leak to the provider.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_client_api import sanitize

if TYPE_CHECKING:
    from chat_client_api import Channel, Message
    from issue_tracker_client_api import Board, Issue, List, Member


# Keep description snippets short so we do not blow past the prompt budget
# with a single giant ticket body.
_DESC_SNIPPET_CHARS = 400
_MSG_TEXT_SNIPPET_CHARS = 400


def serialize_board(board: Board) -> dict[str, Any]:
    """Project a :class:`Board` to a safe dict."""
    return {"id": board.id, "name": board.board_name}


def serialize_issue(issue: Issue) -> dict[str, Any]:
    """Project an :class:`Issue` to a safe dict."""
    desc = (issue.desc or "")[:_DESC_SNIPPET_CHARS]
    return {
        "id": issue.id,
        "title": sanitize.scrub(issue.title),
        "status": issue.status.value,
        "desc_snippet": sanitize.scrub(desc),
        "due_date": issue.due_date,
        "board_id": issue.board_id,
    }


def serialize_list(lst: List) -> dict[str, Any]:
    """Project a :class:`List` to a safe dict."""
    return {
        "id": lst.id,
        "name": lst.name,
        "board_id": lst.board_id,
    }


def serialize_member(member: Member) -> dict[str, Any]:
    """Project a :class:`Member` to a safe dict.

    Deliberately omits email; display name only.
    """
    return {"id": member.id, "display_name": member.username or ""}


def serialize_channel(channel: Channel) -> dict[str, Any]:
    """Project a :class:`Channel` to a safe dict."""
    return {
        "channel_id": channel.channel_id,
        "name": channel.name,
        "is_private": channel.is_private,
        "channel_type": channel.channel_type,
    }


def serialize_message(message: Message) -> dict[str, Any]:
    """Project a :class:`Message` to a safe dict.

    Text content is scrubbed and truncated — incoming chat messages are
    the single biggest prompt-injection surface.
    """
    text = (message.text or "")[:_MSG_TEXT_SNIPPET_CHARS]
    return {
        "message_id": message.message_id,
        "channel_id": message.channel,
        "sender": message.sender,
        "timestamp": message.timestamp.isoformat()
        if message.timestamp is not None
        else None,
        "text_snippet": sanitize.scrub(text),
    }
