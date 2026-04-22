"""Unit tests for ai_client_api.client."""

from __future__ import annotations

from abc import ABC

import pytest
from ai_client_api.client import AIClient, get_client, register_client
from ai_client_api.types import AIReply


@pytest.mark.unit
class TestAIClientABC:
    def test_aiclient_is_abstract(self) -> None:
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = AIClient()  # type: ignore[abstract]

    def test_aiclient_inherits_abc(self) -> None:
        assert issubclass(AIClient, ABC)

    def test_stub_implementation_returns_reply(self, stub_client) -> None:  # type: ignore[no-untyped-def]
        reply = stub_client.send_message("hi", context={"board_id": "b1"})
        assert isinstance(reply, AIReply)
        assert reply.reply == "ok"
        assert stub_client.calls == [("hi", {"board_id": "b1"})]


@pytest.mark.unit
class TestRegistry:
    def test_get_client_unregistered_raises(self) -> None:
        from ai_client_api.client import _ClientRegistry

        saved = _ClientRegistry._factory
        _ClientRegistry._factory = None
        try:
            with pytest.raises(RuntimeError, match="No AI client implementation"):
                get_client()
        finally:
            _ClientRegistry._factory = saved

    def test_register_client_then_get(self, stub_client) -> None:  # type: ignore[no-untyped-def]
        from ai_client_api.client import _ClientRegistry

        saved = _ClientRegistry._factory
        try:
            register_client(lambda: stub_client)
            assert get_client() is stub_client
        finally:
            _ClientRegistry._factory = saved
