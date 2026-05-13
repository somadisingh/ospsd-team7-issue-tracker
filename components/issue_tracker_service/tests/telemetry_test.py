"""Unit tests for telemetry middleware and Prometheus endpoint."""

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from issue_tracker_service.telemetry import (
    _classify_outcome,
    _is_sdk_disabled,
    _metrics_endpoint,
    _parse_headers,
    _prometheus_enabled,
    _resolve_failure_kind,
    _route_template_for_metrics,
    _traces_endpoint,
    setup_telemetry,
)


@pytest.mark.unit
def test_metrics_endpoint_exposes_expected_metrics(raw_client: TestClient) -> None:
    raw_client.get("/health")
    metrics = raw_client.get("/metrics")

    assert metrics.status_code == 200
    body = metrics.text
    assert "issue_tracker_http_request_duration_seconds" in body
    assert "issue_tracker_http_requests_total" in body
    assert "issue_tracker_http_request_outcomes_total" in body
    assert 'route="/health"' in body
    assert 'method="GET"' in body
    assert 'status="200"' in body


@pytest.mark.unit
def test_domain_failures_are_labeled_in_outcome_metric(raw_client: TestClient) -> None:
    raw_client.get("/missing-route-for-404")
    metrics = raw_client.get("/metrics")

    assert metrics.status_code == 200
    assert 'outcome="failure"' in metrics.text
    assert 'failure_kind="domain"' in metrics.text


@pytest.mark.unit
def test_classify_outcome_splits_domain_vs_infrastructure() -> None:
    assert _classify_outcome(200) == ("success", "none")
    assert _classify_outcome(404) == ("failure", "domain")
    assert _classify_outcome(500) == ("failure", "infrastructure")


@pytest.mark.unit
def test_resolve_failure_kind_prefers_explicit_kind_for_failures() -> None:
    assert _resolve_failure_kind(500, "domain") == ("failure", "domain")
    assert _resolve_failure_kind(404, "infrastructure") == ("failure", "infrastructure")
    assert _resolve_failure_kind(404, None) == ("failure", "domain")
    assert _resolve_failure_kind(200, "infrastructure") == ("success", "none")


@pytest.mark.unit
def test_parse_headers_splits_commas() -> None:
    assert _parse_headers("a=b, c=d") == {"a": "b", "c": "d"}
    assert _parse_headers("") == {}
    assert _parse_headers("noequals") == {}


@pytest.mark.unit
def test_traces_endpoint_prefers_explicit_then_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert _traces_endpoint() is None
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "https://x/v1/traces")
    assert _traces_endpoint() == "https://x/v1/traces"
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://gw/otlp")
    assert _traces_endpoint() == "https://gw/otlp/v1/traces"
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://gw/otlp/v1/traces")
    assert _traces_endpoint() == "https://gw/otlp/v1/traces"


@pytest.mark.unit
def test_metrics_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "https://m/v1/metrics")
    assert _metrics_endpoint() == "https://m/v1/metrics"


@pytest.mark.unit
def test_is_sdk_disabled_and_prometheus_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "TRUE")
    assert _is_sdk_disabled() is True
    monkeypatch.setenv("PROMETHEUS_METRICS_ENABLED", "false")
    assert _prometheus_enabled() is False


@pytest.mark.unit
def test_route_template_rewrites_id_like_segments() -> None:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/boards/68f3abc123def4567890123456789ab",
        "raw_path": b"/boards/68f3abc123def4567890123456789ab",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1),
        "server": ("test", 80),
    }
    req = Request(scope)
    assert _route_template_for_metrics(req) == "/boards/{id}"


@pytest.mark.unit
def test_setup_telemetry_idempotent() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    setup_telemetry(app)
    setup_telemetry(app)
    assert getattr(app.state, "otel_instrumented", False) is True


@pytest.mark.unit
def test_metrics_endpoint_derives_from_traces_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`` is unset but the traces
    endpoint is known, we rewrite ``/v1/traces`` → ``/v1/metrics``."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://gw/otlp")
    assert _metrics_endpoint() == "https://gw/otlp/v1/metrics"


@pytest.mark.unit
def test_metrics_endpoint_returns_none_when_nothing_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert _metrics_endpoint() is None


@pytest.mark.unit
def test_route_template_returns_root_for_root_path() -> None:
    """``/`` is short-circuited before the segment-rewriting loop."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1),
        "server": ("test", 80),
    }
    req = Request(scope)
    assert _route_template_for_metrics(req) == "/"


@pytest.mark.unit
def test_route_template_keeps_non_id_segments_and_leaves_short_hex() -> None:
    """Numeric segments and long hex-like ids become ``{id}``; short alpha
    segments are kept verbatim. Pure-numeric segment uses the ``isdigit``
    branch separately from the ``_ID_LIKE`` regex branch."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/boards/42/issues/abc",
        "raw_path": b"/boards/42/issues/abc",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1),
        "server": ("test", 80),
    }
    req = Request(scope)
    out = _route_template_for_metrics(req)
    assert out == "/boards/{id}/issues/abc"


@pytest.mark.unit
def test_setup_telemetry_skips_prometheus_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``PROMETHEUS_METRICS_ENABLED`` is false at setup time, the
    ``/metrics`` endpoint is *not* registered on a fresh app."""
    from fastapi import FastAPI

    monkeypatch.setenv("PROMETHEUS_METRICS_ENABLED", "false")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    app = FastAPI()
    setup_telemetry(app)
    routes = {getattr(r, "path", None) for r in app.routes}
    assert "/metrics" not in routes


@pytest.mark.unit
def test_setup_telemetry_runs_full_sdk_path_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end exercise of the OTel-enabled branch on a fresh FastAPI
    instance: traces+metrics endpoints, instrumentors, and the middleware
    body where ``request_duration`` / ``response_counter`` are non-None.

    The OTLP exporters are replaced with ``MagicMock`` so no network calls
    happen — we only want to walk the setup + middleware code paths. The
    global tracer / meter providers are swapped at module-init time via
    ``set_tracer_provider`` / ``set_meter_provider``; we accept this dirty
    global as a test-only side effect (exporters are mocks, so they will
    silently no-op for the rest of the session).
    """
    from unittest.mock import MagicMock

    from fastapi import FastAPI

    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel.invalid/v1/traces")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Bearer test")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "telemetry-test")
    monkeypatch.setenv("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "healthz")

    monkeypatch.setattr(
        "issue_tracker_service.telemetry.OTLPSpanExporter",
        lambda **_kwargs: MagicMock(),
    )
    monkeypatch.setattr(
        "issue_tracker_service.telemetry.OTLPMetricExporter",
        lambda **_kwargs: MagicMock(),
    )

    app = FastAPI()

    @app.get("/ok")
    async def _ok() -> dict[str, str]:
        return {"ok": "yes"}

    setup_telemetry(app)
    client = TestClient(app)
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"ok": "yes"}


@pytest.mark.unit
def test_setup_telemetry_logs_when_otel_endpoints_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the OTel SDK is enabled but no exporter endpoint is configured,
    setup logs and silently skips trace + metric provider wiring (covers
    the ``else`` branches of both endpoint blocks)."""
    from unittest.mock import MagicMock

    from fastapi import FastAPI

    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", raising=False)
    monkeypatch.setattr(
        "issue_tracker_service.telemetry.OTLPSpanExporter",
        lambda **_kwargs: MagicMock(),
    )
    monkeypatch.setattr(
        "issue_tracker_service.telemetry.OTLPMetricExporter",
        lambda **_kwargs: MagicMock(),
    )

    app = FastAPI()
    setup_telemetry(app)
    assert getattr(app.state, "otel_instrumented", False) is True
