"""Pytest fixtures shared across ai_client_api tests."""

from __future__ import annotations

from typing import Any

import pytest
from ai_client_api.client import AIClient
from ai_client_api.types import AIReply


class _StubAIClient(AIClient):
    """Minimal concrete AIClient used to verify the ABC contract."""

    def __init__(self, reply: AIReply | None = None) -> None:
        self._reply = reply or AIReply(reply="ok")
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def send_message(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AIReply:
        self.calls.append((prompt, context))
        return self._reply


@pytest.fixture
def stub_client() -> _StubAIClient:
    return _StubAIClient()
