"""Unit + integration tests for the /ai routes."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pytest
from ai_client_api.client import AIClient
from ai_client_api.exceptions import AIProviderError, AIUnsafeRequestError
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
        assert body["api_key_loaded"] is False

    def test_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxxx")
        monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-4-5")
        raw = TestClient(app)
        resp = raw.get("/ai/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["api_key_loaded"] is True
        assert body["model"] == "claude-sonnet-4-5"


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
