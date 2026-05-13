"""Tests for :mod:`ai_client_api.resilience`."""

from __future__ import annotations

import time

import pytest
from ai_client_api.resilience import (
    CircuitBreaker,
    IdempotencyMemory,
    RetryPolicy,
    call_with_resilience,
    idempotency_scope,
)


def test_call_with_resilience_zero_attempts_raises() -> None:
    with pytest.raises(RuntimeError, match="exhausted"):
        call_with_resilience(
            lambda: "never",
            retry=RetryPolicy(max_attempts=0, base_delay_s=0.0, max_delay_s=0.0),
        )


def test_call_with_resilience_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            msg = "503 Service Unavailable"
            raise RuntimeError(msg)
        return "ok"

    monkeypatch.setattr(time, "sleep", lambda _s: None)
    out = call_with_resilience(
        flaky,
        retry=RetryPolicy(max_attempts=5, base_delay_s=0.01, max_delay_s=0.05),
    )
    assert out == "ok"
    assert calls["n"] == 3


def test_call_with_resilience_gives_up() -> None:
    def always_fail() -> None:
        raise ConnectionError("boom")

    with pytest.raises(ConnectionError):
        call_with_resilience(
            always_fail,
            retry=RetryPolicy(max_attempts=2, base_delay_s=0.0, max_delay_s=0.0),
        )


def test_circuit_breaker_resets_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    br = CircuitBreaker(threshold=1, reset_timeout_s=10.0)
    t = {"v": 0.0}

    def mono() -> float:
        return t["v"]

    monkeypatch.setattr(time, "monotonic", mono)
    br.record_failure()
    assert br.allow() is False
    t["v"] = 11.0
    assert br.allow() is True


def test_call_with_resilience_breaker_success_clears_failures() -> None:
    br = CircuitBreaker(threshold=2, reset_timeout_s=3600.0)
    with pytest.raises(RuntimeError):
        call_with_resilience(
            lambda: (_ for _ in ()).throw(RuntimeError("500")),
            retry=None,
            breaker=br,
        )
    assert br.allow() is True
    out = call_with_resilience(lambda: "done", retry=None, breaker=br)
    assert out == "done"
    assert br.allow() is True


def test_circuit_breaker_opens() -> None:
    br = CircuitBreaker(threshold=2, reset_timeout_s=3600.0)
    assert br.allow() is True
    with pytest.raises(RuntimeError):
        call_with_resilience(
            lambda: (_ for _ in ()).throw(RuntimeError("500")),
            retry=None,
            breaker=br,
        )
    assert br.allow() is True
    with pytest.raises(RuntimeError):
        call_with_resilience(
            lambda: (_ for _ in ()).throw(RuntimeError("500")),
            retry=None,
            breaker=br,
        )
    assert br.allow() is False
    with pytest.raises(RuntimeError, match="Circuit breaker"):
        call_with_resilience(lambda: "x", retry=None, breaker=br)


def test_idempotency_scope_and_memory() -> None:
    mem = IdempotencyMemory()
    with idempotency_scope("k1"):
        from ai_client_api.resilience import current_idempotency_key

        assert current_idempotency_key() == "k1"
    assert current_idempotency_key() is None
    mem.remember("k1", "t", "{}", "cached")
    assert mem.lookup("k1", "t", "{}") == "cached"
