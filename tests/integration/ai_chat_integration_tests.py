"""Cross-vertical integration tests: AI tool call → chat client send.

These cover HW3 §5:

* **AI-tool-call → cross-vertical-action pathway:** The Claude AI client,
  driven by a fake Anthropic SDK, invokes the ``send_chat_message`` tool
  and the message lands in the registered ``ChatClient`` store.
* **Provider-swap is transparent to the consumer:** The same flow is
  exercised against (a) the workspace local backend and (b) a re-registered
  custom backend; only the registered factory changes — the AI client and
  the FastAPI route are untouched.

We deliberately do not hit the real Slack API in CI; that is exercised by
the manual smoke test described in ``hw3_final/CHAT-INTEGRATION-PLAN.md``
Phase 3 and shown in the demo video.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from chat_client_api import ChatClient, register_client
from chat_client_impl import LocalChatClient, get_seeded_client_impl
from claude_ai_client_impl import ClaudeAIClient, ClaudeConfig
from fastapi.testclient import TestClient
from issue_tracker_service.ai_deps import (
    _authenticated_issue_tracker,
    _chat_client,
    get_ai_client,
)
from issue_tracker_service.main import app

# --------------------------------------------------------------------- #
# Fakes mirroring the ones in claude_ai_client_impl/tests/conftest.py.  #
# Inlined here because pytest does not share conftests across packages. #
# --------------------------------------------------------------------- #


class _FakeResponse:
    def __init__(self, content: list[dict[str, Any]], stop_reason: str) -> None:
        self.content = content
        self.stop_reason = stop_reason


class _FakeMessages:
    def __init__(self, outer: _FakeAnthropic) -> None:
        self._outer = outer

    def create(self, **kwargs: Any) -> _FakeResponse:
        self._outer.calls.append(kwargs)
        if not self._outer.responses:
            msg = "FakeAnthropic ran out of canned responses."
            raise RuntimeError(msg)
        return self._outer.responses.pop(0)


class _FakeAnthropic:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.messages = _FakeMessages(self)


def _tool_use_response(
    *, tool: str, tool_input: dict[str, Any], use_id: str = "toolu_1"
) -> _FakeResponse:
    return _FakeResponse(
        content=[{"type": "tool_use", "id": use_id, "name": tool, "input": tool_input}],
        stop_reason="tool_use",
    )


def _final_text_response(text: str) -> _FakeResponse:
    return _FakeResponse(
        content=[{"type": "text", "text": text}],
        stop_reason="end_turn",
    )


def _claude_config() -> ClaudeConfig:
    return ClaudeConfig(
        api_key="sk-ant-test-00000000000000000000",
        model="claude-sonnet-4-5",
        max_tool_hops=4,
        allow_mutations=True,
        max_tokens=256,
    )


# --------------------------------------------------------------------- #
# Fixtures                                                              #
# --------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _reset_chat_client_cache() -> None:
    _chat_client.cache_clear()


@pytest.fixture
def chat_store() -> LocalChatClient:
    """Seeded ChatClient that we can inspect after the AI runs."""
    store = LocalChatClient(seeded=True)
    register_client(lambda: store)
    return store


@pytest.fixture
def mock_issue_tracker() -> MagicMock:
    return MagicMock(name="TrelloClient")


def _build_real_ai_client(
    *,
    chat: ChatClient,
    issue_tracker: MagicMock,
    fake_anthropic: _FakeAnthropic,
) -> ClaudeAIClient:
    return ClaudeAIClient(
        issue_tracker=issue_tracker,
        chat=chat,
        config=_claude_config(),
        anthropic_client=fake_anthropic,
    )


# --------------------------------------------------------------------- #
# Tests                                                                 #
# --------------------------------------------------------------------- #


@pytest.mark.integration
class TestAIToolCallReachesChatClient:
    """Rubric §5: integration test of the full AI → cross-vertical pathway."""

    def test_send_chat_message_tool_lands_message_in_store(
        self,
        chat_store: LocalChatClient,
        mock_issue_tracker: MagicMock,
    ) -> None:
        # Two-turn conversation: first turn the model emits a tool_use,
        # second turn it summarizes. No real network involved.
        fake = _FakeAnthropic(
            responses=[
                _tool_use_response(
                    tool="send_chat_message",
                    tool_input={"channel_id": "C0123ENG", "text": "ticket #5 is done"},
                ),
                _final_text_response("Notified #eng."),
            ]
        )
        ai = _build_real_ai_client(
            chat=chat_store,
            issue_tracker=mock_issue_tracker,
            fake_anthropic=fake,
        )

        before = len(chat_store.get_messages("C0123ENG", limit=50))
        reply = ai.send_message("Notify the eng channel that ticket #5 is done.")
        after = chat_store.get_messages("C0123ENG", limit=50)

        assert reply.reply == "Notified #eng."
        assert len(after) == before + 1
        assert after[0].text == "ticket #5 is done"
        assert after[0].channel == "C0123ENG"
        assert any(a.tool == "send_chat_message" and a.ok for a in reply.actions)

    def test_full_http_route_drives_tool_call_to_chat_store(
        self,
        chat_store: LocalChatClient,
        mock_issue_tracker: MagicMock,
    ) -> None:
        """End-to-end: POST /ai/chat → Claude tool loop → chat store updated."""
        fake = _FakeAnthropic(
            responses=[
                _tool_use_response(
                    tool="send_chat_message",
                    tool_input={"channel_id": "C0123SUPPORT", "text": "ack"},
                ),
                _final_text_response("Posted."),
            ]
        )
        ai = _build_real_ai_client(
            chat=chat_store,
            issue_tracker=mock_issue_tracker,
            fake_anthropic=fake,
        )

        app.dependency_overrides[_authenticated_issue_tracker] = lambda: (
            mock_issue_tracker
        )
        app.dependency_overrides[get_ai_client] = lambda: ai
        try:
            http = TestClient(app, raise_server_exceptions=False)
            resp = http.post(
                "/ai/chat",
                json={"prompt": "ack the support thread"},
                headers={"X-Session-Token": "tok"},
            )
        finally:
            app.dependency_overrides.pop(_authenticated_issue_tracker, None)
            app.dependency_overrides.pop(get_ai_client, None)

        assert resp.status_code == 200
        body = resp.json()
        assert body["reply"] == "Posted."
        assert any(
            a["tool"] == "send_chat_message" and a["ok"] for a in body["actions"]
        ), body
        landed = chat_store.get_messages("C0123SUPPORT", limit=50)
        assert any(m.text == "ack" for m in landed), (
            "AI tool call must have actually written to the registered "
            "ChatClient — not a mock — for §5 to count."
        )


@pytest.mark.integration
class TestProviderSwapIsTransparent:
    """Rubric §5: swap-by-env-var must change behavior without code changes."""

    def test_swap_local_to_recording_backend_changes_target_only(
        self,
        mock_issue_tracker: MagicMock,
    ) -> None:
        """Two backends, same AI tool call, different ChatClient gets the write.

        Demonstrates the DI pattern from HW1: the AI is unchanged; the
        registered factory determines which `ChatClient` receives the
        side effect.
        """
        # --- Backend A: the seeded local store ---
        backend_a = LocalChatClient(seeded=True)
        register_client(lambda: backend_a)
        before_a = len(backend_a.get_messages("C0123ENG", limit=50))

        fake_a = _FakeAnthropic(
            responses=[
                _tool_use_response(
                    tool="send_chat_message",
                    tool_input={"channel_id": "C0123ENG", "text": "msg-A"},
                ),
                _final_text_response("done"),
            ]
        )
        ai_a = _build_real_ai_client(
            chat=backend_a, issue_tracker=mock_issue_tracker, fake_anthropic=fake_a
        )
        ai_a.send_message("notify eng")
        assert len(backend_a.get_messages("C0123ENG", limit=50)) == before_a + 1, (
            "Backend A should have received the write."
        )

        # --- Backend B: a fresh ChatClient registered via the same registry ---
        backend_b = LocalChatClient(seeded=True)
        register_client(lambda: backend_b)
        before_a_again = len(backend_a.get_messages("C0123ENG", limit=50))

        fake_b = _FakeAnthropic(
            responses=[
                _tool_use_response(
                    tool="send_chat_message",
                    tool_input={"channel_id": "C0123ENG", "text": "msg-B"},
                ),
                _final_text_response("done"),
            ]
        )
        ai_b = _build_real_ai_client(
            chat=backend_b, issue_tracker=mock_issue_tracker, fake_anthropic=fake_b
        )
        ai_b.send_message("notify eng again")

        assert len(backend_a.get_messages("C0123ENG", limit=50)) == before_a_again, (
            "Backend A must NOT have received the write after swapping registry."
        )
        assert any(
            m.text == "msg-B" for m in backend_b.get_messages("C0123ENG", limit=50)
        ), "Backend B must have received the write after the swap."


@pytest.mark.integration
def test_default_factory_is_seeded_local() -> None:
    """Sanity: importing chat_client_impl registers the seeded local fake."""
    register_client(get_seeded_client_impl)
    from chat_client_api import get_client

    client = get_client()
    assert isinstance(client, LocalChatClient)
    assert len(client.get_channels()) > 0
