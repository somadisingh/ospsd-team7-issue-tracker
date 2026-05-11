"""Unit tests for telemetry middleware and Prometheus endpoint."""

import pytest
from fastapi.testclient import TestClient

from issue_tracker_service.telemetry import _classify_outcome, _resolve_failure_kind


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
