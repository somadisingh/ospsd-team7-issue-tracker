# IaC and Telemetry Design

## Design Intent

Use Terraform as the authoritative deployment definition for GCP Cloud Run, and instrument the FastAPI runtime so Prometheus + Grafana can directly compute the rubric KPIs.

## End-to-End Architecture

```mermaid
flowchart TD
  devCommit[Developer Commit] --> circleci[CircleCI]
  circleci --> quality[Lint + Tests + Health]
  circleci --> infra[Terraform Validate / Apply]
  infra --> gcp[GCP Cloud Run + Secret Manager + Artifact Registry]
  gcp --> service[FastAPI issue_tracker_service]
  service --> metrics[/metrics Prometheus endpoint]
  metrics --> prom[Prometheus]
  prom --> grafana[Grafana Dashboards]
  service --> otlp[Optional OTLP Export]
  otlp --> grafanaCloud[Grafana Cloud / OTLP backend]
```

## Infrastructure Design

Terraform (`infrastructure/terraform/`) manages:

- Cloud Run service (public invoker for assignment demo visibility)
- Secret Manager shells/bindings for runtime secrets
- Artifact Registry repository for service images
- Service account and IAM grants
- Outputs that provide public URL (`service_url`) and callback hints

This satisfies "infrastructure as code" expectations better than UI-only deployment definitions.

## Telemetry Design

Application instrumentation (`telemetry.py`) uses middleware to derive low-cardinality route templates and emit:

- **Latency histogram:** `issue_tracker_http_request_duration_seconds`
  - labels: `method`, `route`, `status`
- **Request counter:** `issue_tracker_http_requests_total`
  - labels: `method`, `route`, `status`
- **Outcome counter:** `issue_tracker_http_request_outcomes_total`
  - labels: `method`, `route`, `status`, `outcome`, `failure_kind`

Failure classification logic:

- `2xx/3xx` => `outcome=success`, `failure_kind=none`
- `4xx` => `outcome=failure`, `failure_kind=domain`
- `5xx` => `outcome=failure`, `failure_kind=infrastructure`

Optional OTLP exporters remain available for traces/metrics vendor integrations.

## KPI Mapping Strategy

- **Latency KPI:** p95 over `issue_tracker_http_request_duration_seconds_bucket`
- **Success rate KPI:** successful outcomes / all outcomes
- **Failure rate KPI:** failed outcomes / all outcomes
- **Domain vs infra breakdown:** filter/group by `failure_kind`

## Deployment and Ops Design Notes

- `/health` is used for liveness checks and assignment evidence.
- `/metrics` is intentionally unauthenticated by default for simple scraping in controlled environments; production hardening can add network controls if needed.
- Monitoring bootstrap config is committed under `infrastructure/monitoring/` to keep setup reproducible.
