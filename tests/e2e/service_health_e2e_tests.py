"""Black-box checks against a deployed service base URL (optional).

Set ``E2E_DEPLOYED_HEALTH=1`` to enable. Uses ``SERVICE_BASE_URL`` if set;
otherwise skips (no implicit default — avoids surprise network calls in CI).

Verifies ``GET /health`` returns HTTP 200, satisfying the HW3 rubric e2e
story for a public deployment probe without Trello or session tokens.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pytest


@pytest.fixture
def _e2e_skip_deployed_health_unless_enabled() -> None:
    if os.getenv("E2E_DEPLOYED_HEALTH", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        pytest.skip(
            "Set E2E_DEPLOYED_HEALTH=1 and SERVICE_BASE_URL to run deployed /health e2e"
        )
    base = os.getenv("SERVICE_BASE_URL", "").strip().rstrip("/")
    if not base:
        pytest.skip("SERVICE_BASE_URL is required for deployed /health e2e")
    scheme = urllib.parse.urlparse(base).scheme
    if scheme not in ("http", "https"):
        pytest.skip(f"SERVICE_BASE_URL must be http(s), got scheme={scheme!r}")


@pytest.mark.e2e
@pytest.mark.usefixtures("_e2e_skip_deployed_health_unless_enabled")
def test_deployed_service_health_returns_200() -> None:
    base = os.environ["SERVICE_BASE_URL"].strip().rstrip("/")
    url = f"{base}/health"
    req = urllib.request.Request(url, method="GET")  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            assert resp.status == 200
            body = resp.read()
    except urllib.error.HTTPError as exc:
        pytest.fail(f"GET {url} failed: HTTP {exc.code}")
    except urllib.error.URLError as exc:
        pytest.fail(f"GET {url} failed: {exc.reason!r}")

    data = json.loads(body.decode())
    assert data.get("status") == "ok"
