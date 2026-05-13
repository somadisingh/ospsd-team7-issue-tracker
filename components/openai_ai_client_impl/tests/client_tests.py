"""Tests for :class:`openai_ai_client_impl.client.OpenAIAIClient`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from ai_client_api.exceptions import AIProviderError, AIToolError, AIUnsafeRequestError
from ai_client_api.resilience import idempotency_scope
from ai_client_api.signature_tools import SignatureToolCatalog
from openai_ai_client_impl.client import OpenAIAIClient
from openai_ai_client_impl.config import OpenAIConfig


def _msg(
    *,
    content: str | None,
    tool_calls: list[SimpleNamespace] | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
    )


@pytest.mark.unit
def test_openai_client_tool_round_then_structured_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_HTTP_MAX_ATTEMPTS", "1")

    it = MagicMock()
    it.get_boards.return_value = []
    chat = MagicMock()
    chat.get_channels.return_value = []

    tool_call = SimpleNamespace(
        id="call_1",
        type="function",
        function=SimpleNamespace(
            name="list_boards",
            arguments="{}",
        ),
    )
    first = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=_msg(content=None, tool_calls=[tool_call]),
            ),
        ],
    )
    second = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=_msg(
                    content=json.dumps({"reply": "Listed.", "rationale": None}),
                    tool_calls=None,
                ),
            ),
        ],
    )

    state = {"i": 0}

    class _Completions:
        def create(self, **_kwargs: Any) -> SimpleNamespace:
            state["i"] += 1
            return first if state["i"] == 1 else second

    class _Chat:
        completions = _Completions()

    class FakeOpenAI:
        def __init__(self) -> None:
            self.chat = _Chat()

    fake = FakeOpenAI()

    cfg = OpenAIConfig(
        api_key="sk-test",
        model="gpt-test",
        max_tool_hops=4,
        allow_mutations=False,
        max_tokens=64,
        structured_output=True,
    )
    client = OpenAIAIClient(
        issue_tracker=it,
        chat=chat,
        config=cfg,
        openai_client=fake,
    )
    with idempotency_scope("req-1"):
        reply = client.send_message("show boards", context=None)
    assert reply.reply == "Listed."
    assert any(a.tool == "list_boards" and a.ok for a in reply.actions)
    assert state["i"] == 2


@pytest.mark.unit
def test_openai_unsafe_prompt_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_HTTP_MAX_ATTEMPTS", "1")
    it = MagicMock()
    chat = MagicMock()
    cfg = OpenAIConfig(api_key="sk", structured_output=False)
    client = OpenAIAIClient(
        issue_tracker=it, chat=chat, config=cfg, openai_client=MagicMock()
    )
    with pytest.raises(AIUnsafeRequestError):
        client.send_message("x" * 8001)


@pytest.mark.unit
def test_openai_empty_tool_list_still_calls_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_HTTP_MAX_ATTEMPTS", "1")
    it = MagicMock()
    chat = MagicMock()
    empty_cat = SignatureToolCatalog(allow_mutations=True)
    kwargs_box: dict[str, Any] = {}

    class _Completions:
        def create(self, **kwargs: Any) -> SimpleNamespace:
            kwargs_box.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=_msg(content="plain", tool_calls=None)),
                ],
            )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))
    cfg = OpenAIConfig(api_key="sk", structured_output=False)
    client = OpenAIAIClient(
        issue_tracker=it,
        chat=chat,
        config=cfg,
        openai_client=fake,
        catalog=empty_cat,
    )
    reply = client.send_message("hi")
    assert reply.reply == "plain"
    assert "tools" not in kwargs_box


@pytest.mark.unit
def test_openai_context_ignores_non_string_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_HTTP_MAX_ATTEMPTS", "1")
    it = MagicMock()
    it.get_boards.return_value = []
    chat = MagicMock()
    chat.get_channels.return_value = []

    class _Completions:
        def create(self, **_kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=_msg(content="ok", tool_calls=None)),
                ],
            )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))
    cfg = OpenAIConfig(api_key="sk", structured_output=False)
    client = OpenAIAIClient(issue_tracker=it, chat=chat, config=cfg, openai_client=fake)
    reply = client.send_message("x", context={"idempotency_key": 99})
    assert reply.reply == "ok"


@pytest.mark.unit
def test_openai_invalid_tool_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_HTTP_MAX_ATTEMPTS", "1")
    it = MagicMock()
    chat = MagicMock()
    tool_call = SimpleNamespace(
        id="c1",
        type="function",
        function=SimpleNamespace(name="list_boards", arguments="{"),
    )
    fake = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **_k: SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=_msg(content=None, tool_calls=[tool_call])
                        ),
                    ],
                ),
            ),
        ),
    )
    cfg = OpenAIConfig(api_key="sk", max_tool_hops=2)
    client = OpenAIAIClient(issue_tracker=it, chat=chat, config=cfg, openai_client=fake)
    with pytest.raises(AIToolError, match="Invalid tool JSON"):
        client.send_message("x")


@pytest.mark.unit
def test_openai_tool_runtime_error_becomes_action_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_HTTP_MAX_ATTEMPTS", "1")
    it = MagicMock()
    chat = MagicMock()

    cat = SignatureToolCatalog(allow_mutations=True)

    @cat.register("boom", "breaks", mutating=False)
    def boom() -> None:
        raise RuntimeError("explode")

    tool_call = SimpleNamespace(
        id="c1",
        type="function",
        function=SimpleNamespace(name="boom", arguments="{}"),
    )
    first = SimpleNamespace(
        choices=[
            SimpleNamespace(message=_msg(content=None, tool_calls=[tool_call])),
        ],
    )
    second = SimpleNamespace(
        choices=[SimpleNamespace(message=_msg(content="final", tool_calls=None))],
    )
    state = {"n": 0}

    class _Completions:
        def create(self, **_kwargs: Any) -> SimpleNamespace:
            state["n"] += 1
            return first if state["n"] == 1 else second

    fake = SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))
    cfg = OpenAIConfig(api_key="sk", max_tool_hops=4, structured_output=False)
    client = OpenAIAIClient(
        issue_tracker=it,
        chat=chat,
        config=cfg,
        openai_client=fake,
        catalog=cat,
    )
    reply = client.send_message("x")
    assert reply.reply == "final"
    assert any(a.tool == "boom" and not a.ok for a in reply.actions)


@pytest.mark.unit
def test_openai_hop_limit_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_HTTP_MAX_ATTEMPTS", "1")
    it = MagicMock()
    it.get_boards.return_value = []
    chat = MagicMock()
    tool_call = SimpleNamespace(
        id="c1",
        type="function",
        function=SimpleNamespace(name="list_boards", arguments="{}"),
    )
    resp = SimpleNamespace(
        choices=[
            SimpleNamespace(message=_msg(content=None, tool_calls=[tool_call])),
        ],
    )
    fake = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_k: resp)),
    )
    cfg = OpenAIConfig(api_key="sk", max_tool_hops=1, structured_output=False)
    client = OpenAIAIClient(issue_tracker=it, chat=chat, config=cfg, openai_client=fake)
    reply = client.send_message("x")
    assert reply.truncated is True


@pytest.mark.unit
def test_openai_upstream_error_wraps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_HTTP_MAX_ATTEMPTS", "1")
    it = MagicMock()
    chat = MagicMock()

    class _Completions:
        def create(self, **_kwargs: Any) -> None:
            raise ConnectionError("reset")

    fake = SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))
    cfg = OpenAIConfig(api_key="sk")
    client = OpenAIAIClient(issue_tracker=it, chat=chat, config=cfg, openai_client=fake)
    with pytest.raises(AIProviderError, match="Upstream OpenAI"):
        client.send_message("hi")


@pytest.mark.unit
def test_json_safe_falls_back_to_str() -> None:
    from openai_ai_client_impl.client import _json_safe

    assert isinstance(_json_safe(object()), str)
