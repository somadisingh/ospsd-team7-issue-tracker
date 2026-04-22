"""Tests for the ClaudeAIClient tool-use loop."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from ai_client_api.exceptions import AIProviderError, AIUnsafeRequestError
from claude_ai_client_impl.client import ClaudeAIClient
from claude_ai_client_impl.config import ClaudeConfig
from claude_ai_client_impl.mock_chat import MockChatClient


@pytest.fixture
def make_client(
    mock_issue_tracker: MagicMock,
    mock_chat: MockChatClient,
    default_config: ClaudeConfig,
):
    def _factory(
        anthropic_client: Any, *, config: ClaudeConfig | None = None
    ) -> ClaudeAIClient:
        return ClaudeAIClient(
            issue_tracker=mock_issue_tracker,
            chat=mock_chat,
            config=config or default_config,
            anthropic_client=anthropic_client,
        )

    return _factory


@pytest.mark.unit
class TestSendMessage:
    def test_simple_text_reply_no_tools(
        self,
        make_client,
        response_factory,
        fake_anthropic_factory,
    ) -> None:
        fake = fake_anthropic_factory(
            [
                response_factory(
                    {"type": "text", "text": "hi there"}, stop_reason="end_turn"
                )
            ],
        )
        client = make_client(fake)

        reply = client.send_message("hello")

        assert reply.reply == "hi there"
        assert reply.actions == []
        assert reply.truncated is False
        assert len(fake.calls) == 1

    def test_single_tool_hop_then_text(
        self,
        make_client,
        response_factory,
        fake_anthropic_factory,
    ) -> None:
        fake = fake_anthropic_factory(
            [
                response_factory(
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "list_boards",
                        "input": {},
                    },
                    stop_reason="tool_use",
                ),
                response_factory(
                    {"type": "text", "text": "You have 1 board: Sprint 5."},
                    stop_reason="end_turn",
                ),
            ],
        )
        client = make_client(fake)

        reply = client.send_message("what boards do I have?")

        assert reply.reply == "You have 1 board: Sprint 5."
        assert len(reply.actions) == 1
        assert reply.actions[0].tool == "list_boards"
        assert reply.actions[0].ok is True

    def test_unknown_tool_is_recorded_but_loop_continues(
        self,
        make_client,
        response_factory,
        fake_anthropic_factory,
    ) -> None:
        fake = fake_anthropic_factory(
            [
                response_factory(
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "nuke_database",
                        "input": {},
                    },
                    stop_reason="tool_use",
                ),
                response_factory(
                    {"type": "text", "text": "I can't do that."},
                    stop_reason="end_turn",
                ),
            ],
        )
        client = make_client(fake)

        reply = client.send_message("wipe everything")

        assert reply.reply == "I can't do that."
        assert len(reply.actions) == 1
        assert reply.actions[0].ok is False
        assert "Unknown tool" in (reply.actions[0].error or "")

    def test_hop_limit_truncates(
        self,
        make_client,
        response_factory,
        fake_anthropic_factory,
        default_config: ClaudeConfig,
    ) -> None:
        # Fake that keeps asking for tools forever.
        tool_use = response_factory(
            {
                "type": "tool_use",
                "id": "tool_1",
                "name": "list_boards",
                "input": {},
            },
            stop_reason="tool_use",
        )
        fake = fake_anthropic_factory([tool_use] * 10)
        config = ClaudeConfig(
            api_key=default_config.api_key,
            model=default_config.model,
            max_tool_hops=3,
            allow_mutations=True,
            max_tokens=default_config.max_tokens,
        )
        client = make_client(fake, config=config)

        reply = client.send_message("spin forever")

        assert reply.truncated is True
        assert len(reply.actions) == 3

    def test_upstream_error_becomes_aiproviderror(
        self,
        make_client,
    ) -> None:
        class _Boom:
            class messages:  # noqa: N801 - mirrors anthropic SDK shape
                @staticmethod
                def create(**_kwargs: Any) -> None:
                    msg = "rate limited"
                    raise RuntimeError(msg)

        client = make_client(_Boom)
        with pytest.raises(AIProviderError, match="rate limited"):
            client.send_message("hi")

    def test_oversize_prompt_rejected_before_call(
        self,
        make_client,
        fake_anthropic_factory,
    ) -> None:
        fake = fake_anthropic_factory([])
        client = make_client(fake)

        from ai_client_api import sanitize

        with pytest.raises(AIUnsafeRequestError):
            client.send_message("x" * (sanitize.MAX_PROMPT_CHARS + 1))
        assert fake.calls == []

    def test_context_header_rendered(
        self,
        make_client,
        response_factory,
        fake_anthropic_factory,
    ) -> None:
        fake = fake_anthropic_factory(
            [response_factory({"type": "text", "text": "ok"}, stop_reason="end_turn")],
        )
        client = make_client(fake)

        client.send_message("hi", context={"board_id": "b1"})

        first_user = fake.calls[0]["messages"][0]["content"]
        assert "[scope] board_id='b1'" in first_user

    def test_create_issue_round_trip(
        self,
        make_client,
        response_factory,
        fake_anthropic_factory,
        mock_issue_tracker: MagicMock,
    ) -> None:
        fake = fake_anthropic_factory(
            [
                response_factory(
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "create_issue",
                        "input": {"board_id": "b1", "title": "Safari export bug"},
                    },
                    stop_reason="tool_use",
                ),
                response_factory(
                    {"type": "text", "text": "Created #i1."},
                    stop_reason="end_turn",
                ),
            ],
        )
        client = make_client(fake)

        reply = client.send_message("open a ticket for the export bug")

        mock_issue_tracker.create_issue.assert_called_once()
        assert reply.reply == "Created #i1."
        assert reply.actions[0].tool == "create_issue"
        assert reply.actions[0].ok is True
