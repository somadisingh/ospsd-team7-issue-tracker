"""Retry, backoff, rate-limit hints, and a simple circuit breaker.

Used by AI provider implementations around upstream HTTP calls.  Unit tests
exercise the pure functions and circuit state transitions without network.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_IDEMP_KEY: ContextVar[str | None] = ContextVar("ai_idempotency_key", default=None)


def _is_retryable(exc: BaseException) -> bool:
    """Heuristic: network blips, 429/5xx-ish messages, and timeout types."""
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    msg = str(exc).lower()
    needles = (
        "429",
        "rate limit",
        "ratelimit",
        "503",
        "502",
        "500",
        "timeout",
        "temporarily unavailable",
    )
    return any(n in msg for n in needles)


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff with full jitter (AWS-style)."""

    max_attempts: int = 4
    base_delay_s: float = 0.15
    max_delay_s: float = 2.5

    def sleep_before_retry(self, attempt_index: int) -> None:
        """``attempt_index`` is 0 after the first failure."""
        cap = min(self.max_delay_s, self.base_delay_s * (2**attempt_index))
        delay = random.uniform(0, cap)  # noqa: S311 — jitter for backoff
        time.sleep(delay)


@dataclass
class CircuitBreaker:
    """Counts consecutive failures; opens after ``threshold`` failures."""

    threshold: int = 5
    reset_timeout_s: float = 30.0
    _failures: int = 0
    _opened_at: float | None = field(default=None, repr=False)

    def _is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.reset_timeout_s:
            self._opened_at = None
            self._failures = 0
            return False
        return True

    def allow(self) -> bool:
        return not self._is_open()

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = time.monotonic()
            logger.warning("Circuit breaker opened after %s failures", self._failures)


def call_with_resilience(
    fn: Callable[[], T],
    *,
    retry: RetryPolicy | None = None,
    breaker: CircuitBreaker | None = None,
    retryable: Callable[[BaseException], bool] | None = None,
) -> T:
    """Run ``fn`` with optional circuit breaker + retries.

    Args:
        fn: Zero-argument callable (wrap lambdas around real SDK calls).
        retry: When ``None``, a single attempt is made (after breaker check).
        breaker: When set, ``record_failure`` / ``record_success`` are applied.
        retryable: Predicate overriding the default :func:`_is_retryable`.

    """
    is_retryable = retryable or _is_retryable
    attempts = retry.max_attempts if retry else 1
    last_exc: BaseException | None = None
    for attempt in range(attempts):
        if breaker is not None and not breaker.allow():
            msg = "Circuit breaker is open; refusing upstream call."
            raise RuntimeError(msg)
        try:
            out = fn()
        except BaseException as exc:
            last_exc = exc
            will_retry = (
                retry is not None and attempt < attempts - 1 and is_retryable(exc)
            )
            if will_retry:
                assert retry is not None
                retry.sleep_before_retry(attempt)
                continue
            if breaker is not None:
                breaker.record_failure()
            raise
        else:
            if breaker is not None:
                breaker.record_success()
            return out
    if last_exc is not None:  # pragma: no cover
        raise last_exc
    msg = "call_with_resilience exhausted attempts without result or exception"
    raise RuntimeError(msg)


@contextmanager
def idempotency_scope(key: str | None) -> Iterator[None]:
    """Bind an optional idempotency key for downstream tool dispatch.

    Providers may read :func:`current_idempotency_key` inside mutating tools.
    """

    token = _IDEMP_KEY.set(key)
    try:
        yield
    finally:
        _IDEMP_KEY.reset(token)


def current_idempotency_key() -> str | None:
    """Return the idempotency key for this task context, if any."""
    return _IDEMP_KEY.get()


class IdempotencyMemory:
    """In-process duplicate suppression for mutating tool calls."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str, str], object] = {}

    def remember(
        self, key: str, tool: str, args_fingerprint: str, value: object
    ) -> None:
        self._hits[(key, tool, args_fingerprint)] = value

    def lookup(self, key: str, tool: str, args_fingerprint: str) -> object | None:
        return self._hits.get((key, tool, args_fingerprint))
