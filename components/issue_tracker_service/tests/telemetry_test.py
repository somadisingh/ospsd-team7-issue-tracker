"""Unit tests for telemetry helpers and setup."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import issue_tracker_service.telemetry as telemetry


@pytest.mark.unit
class TestTelemetryHelpers:
    def test_parse_headers_ignores_invalid_parts(self) -> None:
        headers = telemetry._parse_headers("k1=v1, invalid, k2=v2, k3 = v3 ")
        assert headers == {"k1": "v1", "k2": "v2", "k3": "v3"}

    def test_traces_endpoint_uses_generic_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
        assert telemetry._traces_endpoint() == "http://otel-collector:4318/v1/traces"

    def test_metrics_endpoint_rewrites_traces_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", raising=False)
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "http://otel-collector:4318/v1/traces",
        )
        assert telemetry._metrics_endpoint() == "http://otel-collector:4318/v1/metrics"


@pytest.mark.unit
class TestTelemetrySetup:
    def test_setup_telemetry_noops_when_sdk_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        app = FastAPI()
        telemetry.setup_telemetry(app)
        assert getattr(app.state, "otel_instrumented", False) is False

    def test_setup_telemetry_instruments_once_and_records_metrics(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OTEL_SERVICE_NAME", "service-under-test")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
        monkeypatch.setenv("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "/health")
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.setattr(telemetry, "_requests_instrumented", False)

        tracer_provider = MagicMock()
        trace_set_provider = MagicMock()
        metric_set_provider = MagicMock()
        meter = MagicMock()
        duration_histogram = MagicMock()
        response_counter = MagicMock()
        meter.create_histogram.return_value = duration_histogram
        meter.create_counter.return_value = response_counter

        fastapi_instrumentor = MagicMock()
        requests_instrumentor = MagicMock()

        monkeypatch.setattr(telemetry, "TracerProvider", MagicMock(return_value=tracer_provider))
        monkeypatch.setattr(telemetry, "BatchSpanProcessor", MagicMock())
        monkeypatch.setattr(telemetry, "OTLPSpanExporter", MagicMock())
        monkeypatch.setattr(telemetry.trace, "set_tracer_provider", trace_set_provider)
        monkeypatch.setattr(telemetry, "PeriodicExportingMetricReader", MagicMock())
        monkeypatch.setattr(telemetry, "OTLPMetricExporter", MagicMock())
        monkeypatch.setattr(telemetry, "MeterProvider", MagicMock())
        monkeypatch.setattr(telemetry.metrics, "set_meter_provider", metric_set_provider)
        monkeypatch.setattr(telemetry.metrics, "get_meter", MagicMock(return_value=meter))
        monkeypatch.setattr(
            telemetry,
            "FastAPIInstrumentor",
            MagicMock(return_value=fastapi_instrumentor),
        )
        monkeypatch.setattr(
            telemetry,
            "RequestsInstrumentor",
            MagicMock(return_value=requests_instrumentor),
        )

        app = FastAPI()

        @app.get("/boards/{board_id}")
        async def read_board(board_id: str) -> dict[str, str]:
            return {"id": board_id}

        telemetry.setup_telemetry(app)
        telemetry.setup_telemetry(app)

        with TestClient(app) as client:
            response = client.get("/boards/123456")
        assert response.status_code == 200

        assert getattr(app.state, "otel_instrumented", False) is True
        fastapi_instrumentor.instrument_app.assert_called_once_with(app, excluded_urls="/health")
        requests_instrumentor.instrument.assert_called_once()

        duration_histogram.record.assert_called_once()
        response_counter.add.assert_called_once()
        attrs = duration_histogram.record.call_args.args[1]
        assert attrs["http.route"] == "/boards/{board_id}"
        assert attrs["http.method"] == "GET"
        assert attrs["status.class"] == "200"
