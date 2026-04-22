"""OpenTelemetry: OTLP traces, OTLP HTTP metrics (latency, response counts by status)."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

# Best-effort: avoid high-cardinality path segments in metric attributes
_ID_LIKE = re.compile(r"^[\da-f-]{6,}$", re.IGNORECASE)
_requests_instrumented = False


def _is_sdk_disabled() -> bool:
    v = os.environ.get("OTEL_SDK_DISABLED", "").lower().strip()
    return v in ("1", "true", "yes", "on")


def _parse_headers(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    out: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" in part:
            k, s, val = part.partition("=")
            if s:
                out[k.strip()] = val.strip()
    return out


def _traces_endpoint() -> str | None:
    if ep := (os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or "").strip():
        return ep
    if ep := (os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip():
        if "/v1/" in ep:
            return ep if "traces" in ep else f"{ep.rstrip('/')}/v1/traces"
        return f"{ep.rstrip('/')}/v1/traces"
    return None


def _metrics_endpoint() -> str | None:
    if ep := (os.environ.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT") or "").strip():
        return ep
    te = _traces_endpoint()
    if te and "traces" in te:
        return te.replace("/v1/traces", "/v1/metrics")
    return None


def _route_template_for_metrics(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and hasattr(route, "path"):
        return str(getattr(route, "path", "/"))
    path = request.url.path.split("?")[0]
    if not path or path == "/":
        return path
    segs: list[str] = []
    for s in path.strip("/").split("/"):
        if s.isdigit() or _ID_LIKE.match(s):
            segs.append("{id}")
        else:
            segs.append(s)
    return "/" + "/".join(segs) if segs else "/"


def setup_telemetry(app: FastAPI) -> None:
    """Set up global OTel providers, FastAPI + ``requests`` tracing, and HTTP request metrics."""
    if _is_sdk_disabled():
        return
    if getattr(app.state, "otel_instrumented", False):
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", "issue-tracker-service").strip() or "issue-tracker-service"
    headers = _parse_headers(os.environ.get("OTEL_EXPORTER_OTLP_HEADERS"))
    resource = Resource.create({"service.name": service_name})

    trace_ep = _traces_endpoint()
    if trace_ep:
        t_provider = TracerProvider(resource=resource)
        t_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=trace_ep, headers=headers)),  # type: ignore[abstract]
        )
        trace.set_tracer_provider(t_provider)
    else:
        logger.info("OTel traces: no OTLP endpoint; spans are not exported (set OTEL_EXPORTER_OTLP_* or disable SDK).")

    metrics_ep = _metrics_endpoint()
    if metrics_ep:
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=metrics_ep, headers=headers),  # type: ignore[abstract]
            export_interval_millis=10_000,
        )
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    else:
        logger.info(
            "OTel metrics: no OTLP endpoint; metrics are not exported (set OTEL_EXPORTER_OTLP_* or disable SDK)."
        )

    meter = metrics.get_meter(__name__)
    request_duration = meter.create_histogram(
        name="http.server.request.duration",
        unit="s",
        description="HTTP request handler duration in seconds (assignment: latency).",
    )
    response_counter = meter.create_counter(
        name="http.server.responses",
        unit="1",
        description="HTTP response count by route and status class (assignment: success vs error rate).",
    )

    @app.middleware("http")
    async def _http_metrics_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        sc = response.status_code
        status_class = f"{(sc // 100) * 100}" if 100 <= sc < 600 else "other"
        route = _route_template_for_metrics(request)
        attrs = {
            "http.method": request.method,
            "http.route": route,
            "status.class": status_class,
        }
        request_duration.record(elapsed, attrs)
        response_counter.add(1, attrs)
        return response

    exclude = (os.environ.get("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS") or "").strip() or None
    FastAPIInstrumentor().instrument_app(app, excluded_urls=exclude)  # type: ignore[union-attr]

    global _requests_instrumented
    if not _requests_instrumented:
        RequestsInstrumentor().instrument()
        _requests_instrumented = True

    app.state.otel_instrumented = True
