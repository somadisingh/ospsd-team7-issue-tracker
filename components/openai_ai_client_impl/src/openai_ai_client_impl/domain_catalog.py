"""Issue-tracker + chat tools for OpenAI, using signature-generated schemas."""

from __future__ import annotations

from typing import Any

from ai_client_api.exceptions import AIToolError
from ai_client_api.resilience import IdempotencyMemory
from ai_client_api.signature_tools import SignatureToolCatalog
from chat_client_api import ChatClient
from claude_ai_client_impl import serializers
from claude_ai_client_impl.prompt import SYSTEM_PROMPT
from issue_tracker_client_api import Client as IssueTrackerClient

__all__ = ["SYSTEM_PROMPT", "build_domain_catalog"]


def build_domain_catalog(
    issue_tracker: IssueTrackerClient,
    chat: ChatClient,
    *,
    allow_mutations: bool,
    idempotency: IdempotencyMemory | None = None,
) -> SignatureToolCatalog:
    """Register the same logical tool surface as the Claude dispatcher."""
    it = issue_tracker
    ch = chat
    cat: SignatureToolCatalog = SignatureToolCatalog(
        allow_mutations=allow_mutations,
        idempotency=idempotency,
    )

    @cat.register("list_boards", "List all boards the user can access.", mutating=False)
    def list_boards() -> list[dict[str, Any]]:
        return [serializers.serialize_board(b) for b in it.get_boards()]

    @cat.register("get_board", "Fetch a single board by id.", mutating=False)
    def get_board(board_id: str) -> dict[str, Any]:
        return serializers.serialize_board(it.get_board(board_id))

    @cat.register(
        "list_issues_on_board",
        "List all issues on the given board.",
        mutating=False,
    )
    def list_issues_on_board(board_id: str) -> list[dict[str, Any]]:
        return [serializers.serialize_issue(i) for i in it.get_issues(board_id)]

    @cat.register("get_issue", "Fetch a single issue by id.", mutating=False)
    def get_issue(issue_id: str) -> dict[str, Any]:
        return serializers.serialize_issue(it.get_issue(issue_id))

    @cat.register(
        "create_board",
        "Create a new empty board with the given name.",
        mutating=True,
    )
    def create_board(name: str) -> dict[str, Any]:
        board = it.create_board(name=name)
        return serializers.serialize_board(board)

    @cat.register("rename_board", "Rename an existing board.", mutating=True)
    def rename_board(board_id: str, name: str) -> dict[str, Any]:
        return serializers.serialize_board(
            it.update_board(board_id=board_id, name=name)
        )

    @cat.register(
        "create_issue",
        "Create a new issue on a board with title and optional description.",
        mutating=True,
    )
    def create_issue(
        board_id: str,
        title: str,
        desc: str | None = None,
    ) -> dict[str, Any]:
        issue = it.create_issue(title=title, board_id=board_id, desc=desc)
        return serializers.serialize_issue(issue)

    @cat.register(
        "update_issue_status",
        "Move an issue to a new status (to_do, in_progress, completed).",
        mutating=True,
    )
    def update_issue_status(issue_id: str, status: str) -> dict[str, Any]:
        from api.issue import Status

        try:
            st = Status(status)
        except ValueError as exc:
            allowed = [s.value for s in Status]
            msg = f"Invalid status {status!r}. Expected one of {allowed}."
            raise AIToolError(msg) from exc
        updated = it.update_issue(issue_id=issue_id, status=st)
        return serializers.serialize_issue(updated)

    @cat.register(
        "assign_issue",
        "Assign a board member to an issue. Only when the user explicitly asks.",
        mutating=True,
    )
    def assign_issue(issue_id: str, member_id: str) -> dict[str, Any]:
        ok = it.assign_issue(issue_id=issue_id, member_id=member_id)
        return {"success": bool(ok)}

    @cat.register(
        "list_channels",
        "List chat channels the bot can see.",
        mutating=False,
    )
    def list_channels() -> list[dict[str, Any]]:
        return [serializers.serialize_channel(c) for c in ch.get_channels()]

    @cat.register("get_channel", "Fetch one chat channel by id.", mutating=False)
    def get_channel(channel_id: str) -> dict[str, Any]:
        return serializers.serialize_channel(ch.get_channel(channel_id))

    @cat.register(
        "get_recent_messages",
        "Fetch recent messages in a channel (limit 1-50).",
        mutating=False,
    )
    def get_recent_messages(channel_id: str, limit: int = 10) -> list[dict[str, Any]]:
        msgs = ch.get_messages(channel_id, limit=limit)
        return [serializers.serialize_message(m) for m in msgs]

    @cat.register(
        "send_chat_message",
        "Post a message to a chat channel when the user explicitly asks.",
        mutating=True,
    )
    def send_chat_message(channel_id: str, text: str) -> dict[str, Any]:
        return serializers.serialize_message(ch.send_message(channel_id, text))

    return cat
