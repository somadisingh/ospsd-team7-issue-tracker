# Grafana KPI Runbook (Prometheus + Grafana)

## Purpose

Define a concrete procedure to prove telemetry rubric KPIs:

- Latency
- Success rate
- Failure rate
- Domain vs infrastructure failure split

## Metrics Source

Service endpoint:

- `GET /metrics`

Prometheus metrics emitted by `telemetry.py`:

- `issue_tracker_http_request_duration_seconds` (histogram)
- `issue_tracker_http_requests_total` (counter)
- `issue_tracker_http_request_outcomes_total` (counter)

Labels:

- `method`
- `route`
- `status`
- `outcome` (`success` or `failure`)
- `failure_kind` (`none`, `domain`, `infrastructure`)

## Local Stack (Auto-Provisioned)

From repo root:

1. Start app locally (or use deployed URL behind accessible network).
2. Start monitoring stack:
   - `cd infrastructure/monitoring`
   - `docker compose up -d`
3. Open Prometheus at `http://localhost:9090`.
4. Open Grafana at `http://localhost:3000` (`admin` / `admin` default in compose).
5. Open dashboard folder **Issue Tracker** and load **Issue Tracker KPI Dashboard**.

What is auto-provisioned by Docker setup:

- Prometheus datasource (`uid: prometheus`)
- Dashboard provider for JSON dashboards
- Prebuilt dashboard JSON at `infrastructure/monitoring/grafana/dashboards/issue-tracker-kpis.json`

Default scrape targets in `prometheus.yml`:

- Cloud Run: `https://issue-tracker-service-688420327904.us-central1.run.app/metrics`
- Local app: `http://host.docker.internal:8000/metrics`

If your service URL differs, update the Cloud Run target in `prometheus.yml`.

## Grafana Panel Queries

### 1) p95 Latency

```promql
histogram_quantile(
  0.95,
  sum(rate(issue_tracker_http_request_duration_seconds_bucket[5m])) by (le, route, method)
)
```

### 2) Success Rate (%)

```promql
100 *
sum(rate(issue_tracker_http_request_outcomes_total{outcome="success"}[5m]))
/
sum(rate(issue_tracker_http_request_outcomes_total[5m]))
```

### 3) Failure Rate (%)

```promql
100 *
sum(rate(issue_tracker_http_request_outcomes_total{outcome="failure"}[5m]))
/
sum(rate(issue_tracker_http_request_outcomes_total[5m]))
```

### 4) Failure Breakdown (Domain vs Infrastructure)

```promql
sum(rate(issue_tracker_http_request_outcomes_total{outcome="failure"}[5m])) by (failure_kind)
```

## Verification Procedure

1. Generate successful traffic (`/health`, valid API calls).
2. Generate domain failures (invalid request causing 4xx).
3. Generate infrastructure failures (forced upstream failure or temporary dependency outage producing 5xx).
4. Confirm Grafana panels update within one scrape interval.
5. Capture screenshots showing:
   - dashboard time range
   - panel values
   - data source and query configuration
6. Capture the deployed health proof:
   - `curl -i https://issue-tracker-service-688420327904.us-central1.run.app/health`
   - ensure HTTP 200 is visible in your evidence.

## Troubleshooting

No data in Prometheus:

1. Verify app serves `/metrics` (`curl -sf <base_url>/metrics`).
2. Verify target health in Prometheus UI (`Status -> Targets`).
3. Verify `PROMETHEUS_METRICS_ENABLED` is not disabled.

No data in Grafana:

1. Verify Prometheus data source connectivity.
2. Run same query in Prometheus expression browser.
3. Confirm dashboard time range includes recent traffic.

OTLP path required instead of scrape:

1. Keep Prometheus metrics for rubric evidence.
2. Optionally configure OTLP variables (`OTEL_EXPORTER_OTLP_*`) for Grafana Cloud traces/metrics export.
