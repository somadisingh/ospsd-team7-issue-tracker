# Issue Tracker Service

## Overview

`issue_tracker_service` is a FastAPI application that wraps the `trello_client_impl` behind REST endpoints with OAuth 1.0a session-based authentication. It is the main deployment unit for this project (**Google Cloud Run** — see repository **`README.md`** and **`infrastructure/terraform/`**).

## Purpose

- **HTTP API:** Exposes all `Client` operations as REST endpoints (boards, lists, issues, members).
- **OAuth 1.0a:** Provides `/auth/login` and `/auth/callback` endpoints for the Trello OAuth flow, issuing server-side session tokens.
- **Health check:** `GET /health` returns `200` with JSON status (and DB connectivity when configured).
- **Dependency injection:** Uses FastAPI's `Depends()` to inject an authenticated `TrelloClient` into every endpoint handler.

## Architecture

```
Browser/Client
    │
    ▼
┌──────────────────────────────┐
│  FastAPI Service              │
│  ├── /auth/login   (OAuth)   │
│  ├── /auth/callback (OAuth)  │
│  ├── /health                 │
│  ├── /boards, /boards/{id}   │
│  ├── /lists, /lists/{id}     │
│  ├── /issues, /issues/{id}   │
│  └── /issues/{id}/members    │
└──────────┬───────────────────┘
           │ uses
           ▼
     TrelloClient
     (trello_client_impl)
           │
           ▼
     Trello REST API
```

### Authentication flow

1. Client visits `GET /auth/login` — service fetches an OAuth request token from Trello and redirects the user to Trello's authorization page.
2. After the user authorizes, Trello redirects to `GET /auth/callback?oauth_token=...&oauth_verifier=...`.
3. The service exchanges the request token for an access token, persists the session in the database, and returns a `session_token`.
4. All subsequent API calls include `X-Session-Token: <session_token>` in the header.

> **Note:** Trello uses OAuth 1.0a (not OAuth 2.0). This implementation follows the provider's required protocol.

### Environment variables

| Variable              | Required | Description                                                            |
| --------------------- | -------- | ---------------------------------------------------------------------- |
| `TRELLO_API_KEY`      | Yes      | Trello API key                                                         |
| `TRELLO_API_SECRET`   | Yes      | Trello API secret (consumer secret)                                    |
| `DATABASE_URL`        | Yes      | SQLAlchemy URL (e.g. Postgres on Render, Supabase, or local SQLite/Postgres) |
| `TRELLO_CALLBACK_URL` | No       | OAuth callback URL. If unset, `/auth/login` derives it from the incoming request host (`https://<host>/auth/callback`). |

### Telemetry (Prometheus + optional OpenTelemetry)

The service always exposes Prometheus metrics at **`GET /metrics`** (disable with `PROMETHEUS_METRICS_ENABLED=false`) and can export **OTLP/HTTP** traces and metrics when endpoints and optional headers are set. See repository **`.env.example`**.

| Variable | Role |
| -------- | ---- |
| `PROMETHEUS_METRICS_ENABLED` | Enables `/metrics` scrape endpoint (default `true`). |
| `OTEL_SERVICE_NAME` | Logical service name in OTLP backend (default: `issue-tracker-service`). |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | Full URL to `.../v1/traces` (or set `OTEL_EXPORTER_OTLP_ENDPOINT` base; see `.env.example`). |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` | Full URL to `.../v1/metrics` (optional if derived from traces URL). |
| `OTEL_EXPORTER_OTLP_HEADERS` | Comma-separated `Key=Value` auth headers for your vendor. |
| `OTEL_SDK_DISABLED` | Set to `true` for local/CI when you are not sending data to a collector. |

**Prometheus metrics emitted (for dashboards):**

- `issue_tracker_http_request_duration_seconds` with labels `method`, `route`, `status`
- `issue_tracker_http_requests_total` with labels `method`, `route`, `status`
- `issue_tracker_http_request_outcomes_total` with labels `method`, `route`, `status`, `outcome`, `failure_kind`

`failure_kind` values are `domain` for 4xx and `infrastructure` for 5xx; success responses use `none`.

**OTel metrics (when OTLP is configured):** `http.server.request.duration`, `http.server.responses` with route/method/status attributes.

Prebuilt Grafana dashboard JSON is available at `infrastructure/monitoring/grafana/dashboards/issue-tracker-kpis.json`, with provisioning config in `infrastructure/monitoring/grafana/provisioning/`.

**Migrations:** On **Cloud Run**, **`docker-entrypoint.sh`** runs **`alembic upgrade head`** before **uvicorn** (override with **`SKIP_ALEMBIC=true`** only for debugging). On **Render**, use `preDeployCommand` when available, or run once via **Render Shell**. Locally, from repo root: `uv run alembic -c components/issue_tracker_service/alembic.ini upgrade head`.

## API Reference

### Authentication

| Method | Path             | Description                                    |
| ------ | ---------------- | ---------------------------------------------- |
| `GET`  | `/auth/login`    | Initiate OAuth flow (redirects to Trello)      |
| `GET`  | `/auth/callback` | Handle OAuth callback, returns `session_token` |

### Boards

| Method | Path                         | Description                                |
| ------ | ---------------------------- | ------------------------------------------ |
| `GET`  | `/boards`                    | List all boards for the authenticated user |
| `GET`  | `/boards/{board_id}`         | Get a single board                         |
| `POST` | `/boards`                    | Create a new board                         |
| `POST` | `/boards/{board_id}/members` | Add a member to a board                    |
| `GET`  | `/boards/{board_id}/lists`   | List all lists on a board                  |

### Lists

| Method   | Path                      | Description          |
| -------- | ------------------------- | -------------------- |
| `GET`    | `/lists/{list_id}`        | Get a single list    |
| `POST`   | `/lists`                  | Create a new list    |
| `PUT`    | `/lists/{list_id}`        | Rename a list        |
| `DELETE` | `/lists/{list_id}`        | Archive a list       |
| `GET`    | `/lists/{list_id}/issues` | Get issues in a list |

### Issues

| Method   | Path                         | Description                      |
| -------- | ---------------------------- | -------------------------------- |
| `GET`    | `/issues/{issue_id}`         | Get a single issue               |
| `POST`   | `/issues`                    | Create a new issue               |
| `PUT`    | `/issues/{issue_id}/status`  | Update issue status              |
| `DELETE` | `/issues/{issue_id}`         | Delete an issue                  |
| `GET`    | `/issues/{issue_id}/members` | Get members assigned to an issue |
| `POST`   | `/issues/{issue_id}/assign`  | Assign a member to an issue      |

### Health

| Method | Path      | Description                |
| ------ | --------- | -------------------------- |
| `GET`  | `/health` | Returns `{"status": "ok"}` |

## Deployment

Production hosting is modeled with **GCP Cloud Run + Terraform** at [`infrastructure/terraform/`](../../../infrastructure/terraform/) (Docker image builds from repo root; container runs Alembic then uvicorn). Details: [`../../../infrastructure/terraform/README.md`](../../../infrastructure/terraform/README.md).

| Setting            | Value                                                                       |
| ------------------ | --------------------------------------------------------------------------- |
| **Platform (GCP)** | [Google Cloud Run](https://cloud.google.com/run) + Terraform in-repo        |
| **Platform (alt)** | [Render](https://render.com) via root [`render.yaml`](../../../render.yaml) |
| **Example URLs**   | Cloud Run: `terraform output -raw service_url` · Render: team URL in root README |

On **`main`**, CircleCI **`deploy_gcp`** can **`gcloud builds submit`** and optionally **`terraform apply`** once you configure GCP env vars (**`infrastructure/terraform/README.md`** → *Automate deploys on `main`*).

Environment secrets for Cloud Run land in **Secret Manager** via Terraform (`database_url`, Trello credentials, optional OTLP/Anthropic). Use `terraform output trello_callback_hint` to align **`TRELLO_CALLBACK_URL`** with the Cloud Run hostname after the first revision.

## Running locally

Work in the **repository root** (so the root `.env` is loaded). `uv` resolves the package; you do not need to `cd` into `components/issue_tracker_service/`.

```bash
uv sync --all-extras
# copy .env.example to .env in the repo root, or export variables

uv run uvicorn issue_tracker_service.main:app --reload
uv run alembic -c components/issue_tracker_service/alembic.ini upgrade head
```

Open http://localhost:8000/docs for the interactive API.

## Testing

```bash
# Run service unit tests
uv run pytest components/issue_tracker_service/tests/ -v -m unit
```
