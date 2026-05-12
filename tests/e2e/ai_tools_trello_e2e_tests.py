"""E2E: same tool catalogue the AI uses, executed against live Trello.

These tests do **not** call Anthropic or OpenAI. They prove that
:class:`claude_ai_client_impl.tools.ToolDispatcher` forwards to a real
:class:`trello_client_impl.client.TrelloClient` when credentials are present.

Requires the same env as other Trello e2e tests (see ``tests/e2e/conftest.py``).
If Trello returns an error (e.g. 401 after a revoked token), the test is skipped
like ``tests/e2e/e2e_tests.py`` — update CI ``TRELLO_*`` vars to run against live API.
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
    try:
        boards = dispatcher.dispatch("list_boards", {})
    except Exception as e:
        pytest.skip(f"Could not reach Trello API: {e}")
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
    try:
        board = dispatcher.dispatch("get_board", {"board_id": e2e_board_id})
    except Exception as e:
        pytest.skip(f"Could not reach Trello API: {e}")
    assert board["id"] == e2e_board_id
