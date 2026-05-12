"""Unit + integration tests for the /ai routes."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pytest
from ai_client_api.client import AIClient
from ai_client_api.exceptions import (
    AIError,
    AIProviderError,
    AIStructuredOutputError,
    AIToolError,
    AIUnsafeRequestError,
)
from ai_client_api.types import AIReply, ToolAction
from fastapi.testclient import TestClient
from issue_tracker_service.main import app


class _FixedAI(AIClient):
    """Stub AIClient that returns pre-programmed AIReplies."""

    def __init__(self, reply: AIReply | Exception) -> None:
        self._reply = reply
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def send_message(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AIReply:
        self.calls.append((prompt, context))
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


@contextmanager
def _override_ai(client: AIClient) -> Iterator[TestClient]:
    """Context manager that yields a TestClient with AI deps overridden."""
    from issue_tracker_service.ai_deps import (
        _authenticated_issue_tracker,
        get_ai_client,
    )

    app.dependency_overrides[_authenticated_issue_tracker] = lambda: object()
    app.dependency_overrides[get_ai_client] = lambda: client
    http = TestClient(app, raise_server_exceptions=False)
    try:
        yield http
    finally:
        app.dependency_overrides.pop(get_ai_client, None)
        app.dependency_overrides.pop(_authenticated_issue_tracker, None)


@pytest.mark.unit
class TestAIHealth:
    def test_unconfigured_when_no_api_key(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        raw = TestClient(app)
        resp = raw.get("/ai/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "unconfigured"
        assert body["provider"] == "claude"
        assert body["api_key_loaded"] is False

    def test_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxxx")
        monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-4-5")
        monkeypatch.delenv("AI_PROVIDER", raising=False)
        raw = TestClient(app)
        resp = raw.get("/ai/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["provider"] == "claude"
        assert body["api_key_loaded"] is True
        assert body["model"] == "claude-sonnet-4-5"

    def test_openai_health_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
        raw = TestClient(app)
        resp = raw.get("/ai/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "openai"
        assert body["status"] == "ok"

    def test_openai_health_unconfigured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        raw = TestClient(app)
        resp = raw.get("/ai/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "unconfigured"
        assert body["provider"] == "openai"
        assert body["api_key_loaded"] is False


@pytest.mark.unit
class TestAIChat:
    def test_happy_path(self) -> None:
        stub = _FixedAI(
            AIReply(
                reply="ok",
                actions=[ToolAction(tool="list_boards", arguments={}, ok=True)],
                truncated=False,
            ),
        )
        with _override_ai(stub) as http:
            resp = http.post(
                "/ai/chat",
                json={"prompt": "list boards", "board_id": "b1"},
                headers={"X-Session-Token": "tok"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["reply"] == "ok"
        assert body["actions"][0]["tool"] == "list_boards"
        assert body["truncated"] is False
        assert stub.calls[0][1] == {"board_id": "b1"}

    def test_missing_prompt_422(self) -> None:
        stub = _FixedAI(AIReply(reply="unused"))
        with _override_ai(stub) as http:
            resp = http.post("/ai/chat", json={}, headers={"X-Session-Token": "tok"})
        assert resp.status_code == 422

    def test_unsafe_request_400(self) -> None:
        stub = _FixedAI(AIUnsafeRequestError("prompt too long"))
        with _override_ai(stub) as http:
            resp = http.post(
                "/ai/chat",
                json={"prompt": "hi"},
                headers={"X-Session-Token": "tok"},
            )
        assert resp.status_code == 400
        assert "prompt too long" in resp.json()["detail"]

    def test_provider_error_502(self) -> None:
        stub = _FixedAI(AIProviderError("upstream boom"))
        with _override_ai(stub) as http:
            resp = http.post(
                "/ai/chat",
                json={"prompt": "hi"},
                headers={"X-Session-Token": "tok"},
            )
        assert resp.status_code == 502

    def test_structured_output_error_422(self) -> None:
        stub = _FixedAI(AIStructuredOutputError("bad envelope"))
        with _override_ai(stub) as http:
            resp = http.post(
                "/ai/chat",
                json={"prompt": "hi"},
                headers={"X-Session-Token": "tok"},
            )
        assert resp.status_code == 422
        assert "bad envelope" in resp.json()["detail"]

    def test_channel_id_passed_in_context(self) -> None:
        stub = _FixedAI(AIReply(reply="ok", actions=[], truncated=False))
        with _override_ai(stub) as http:
            resp = http.post(
                "/ai/chat",
                json={"prompt": "hi", "channel_id": "C123"},
                headers={"X-Session-Token": "tok"},
            )
        assert resp.status_code == 200
        assert stub.calls[0][1] == {"channel_id": "C123"}

    def test_tool_error_400(self) -> None:
        stub = _FixedAI(AIToolError("bad tool args"))
        with _override_ai(stub) as http:
            resp = http.post(
                "/ai/chat",
                json={"prompt": "hi"},
                headers={"X-Session-Token": "tok"},
            )
        assert resp.status_code == 400

    def test_generic_ai_error_500(self) -> None:
        stub = _FixedAI(AIError("unexpected"))
        with _override_ai(stub) as http:
            resp = http.post(
                "/ai/chat",
                json={"prompt": "hi"},
                headers={"X-Session-Token": "tok"},
            )
        assert resp.status_code == 500
