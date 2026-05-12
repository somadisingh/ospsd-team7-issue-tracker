"""E2E: same tool catalogue the AI uses, executed against live Trello.

These tests do **not** call Anthropic or OpenAI. They prove that
:class:`claude_ai_client_impl.tools.ToolDispatcher` forwards to a real
:class:`trello_client_impl.client.TrelloClient` when credentials are present.

Requires the same env as other Trello e2e tests (see ``tests/e2e/conftest.py``).
"""

from __future__ import annotations

import pytest
from chat_client_impl import LocalChatClient
from claude_ai_client_impl.tools import ToolDispatcher
from trello_client_impl import TrelloClient


@pytest.mark.e2e
def test_tool_dispatcher_list_boards_hits_real_trello(
    e2e_skip_if_no_credentials: None,
    e2e_credentials: dict[str, str],
) -> None:
    client = TrelloClient(**e2e_credentials)
    dispatcher = ToolDispatcher(
        issue_tracker=client,
        chat=LocalChatClient(seeded=True),
        allow_mutations=False,
    )
    boards = dispatcher.dispatch("list_boards", {})
    assert isinstance(boards, list)
    assert len(boards) >= 1
    assert "id" in boards[0] and "name" in boards[0]


@pytest.mark.e2e
def test_tool_dispatcher_get_board_hits_real_trello(
    e2e_skip_if_no_credentials: None,
    e2e_credentials: dict[str, str],
    e2e_board_id: str,
) -> None:
    if not e2e_board_id:
        pytest.skip("TRELLO_BOARD_ID not set")

    client = TrelloClient(**e2e_credentials)
    dispatcher = ToolDispatcher(
        issue_tracker=client,
        chat=LocalChatClient(seeded=True),
        allow_mutations=False,
    )
    board = dispatcher.dispatch("get_board", {"board_id": e2e_board_id})
    assert board["id"] == e2e_board_id
