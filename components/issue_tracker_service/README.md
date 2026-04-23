# Issue Tracker Service

## Overview

`issue_tracker_service` is a FastAPI application that wraps the `trello_client_impl` behind REST endpoints with OAuth 1.0a session-based authentication. It is the main deployment unit for this project, deployed on [Render](https://ospsd-team7-issue-tracker.onrender.com).

## Purpose

- **HTTP API:** Exposes all `Client` operations as REST endpoints (boards, lists, issues, members).
- **OAuth 1.0a:** Provides `/auth/login` and `/auth/callback` endpoints for the Trello OAuth flow, issuing server-side session tokens.
- **Health check:** `GET /health` returns `{"status": "ok"}` for liveness probes.
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
| `DATABASE_URL`        | Yes      | SQLAlchemy URL (e.g. Postgres on Render or local)                      |
| `TRELLO_CALLBACK_URL` | No       | OAuth callback URL (defaults to `http://localhost:8000/auth/callback`) |

### OpenTelemetry (course: latency, success vs failure)

The service exports **OTLP/HTTP** traces and **HTTP metrics** when endpoints and optional headers are set. See repository **`.env.example`**.

| Variable | Role |
| -------- | ---- |
| `OTEL_SERVICE_NAME` | Logical service name in the backend (default: `issue-tracker-service`). |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | Full URL to `.../v1/traces` (or set `OTEL_EXPORTER_OTLP_ENDPOINT` base; see `.env.example`). |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` | Full URL to `.../v1/metrics` (optional if derived from traces URL). |
| `OTEL_EXPORTER_OTLP_HEADERS` | Comma-separated `Key=Value` auth headers for your vendor. |
| `OTEL_SDK_DISABLED` | Set to `true` for local/CI when you are not sending data to a collector. |

**Metrics emitted (for dashboards):** `http.server.request.duration` (seconds), `http.server.responses` (count) with labels `http.method`, `http.route` (template/low-cardinality), and `status.class` (`200`, `400`, `500`, …) for success vs error rate.

Run **database migrations** before first deploy traffic (from **repository root** so `.env` loads): `uv run alembic -c components/issue_tracker_service/alembic.ini upgrade head` — on **paid** Render with `preDeployCommand`, that can run automatically; on **Render free** web services, pre-deploy is unavailable, so run migrations once via **Render Shell** (same command, with `DATABASE_URL` set) after the first deploy or schema change.

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

The service is deployed on [Render](https://ospsd-team7-issue-tracker.onrender.com) as a web service.

| Setting            | Value                                                                       |
| ------------------ | --------------------------------------------------------------------------- |
| **Platform**       | [Render](https://render.com)                                                |
| **URL**            | `https://ospsd-team7-issue-tracker.onrender.com`                            |
| **Build command**  | `pip install uv && uv sync --all-extras`                                    |
| **Start command**  | `uv run uvicorn issue_tracker_service.main:app --host 0.0.0.0 --port $PORT` |
| **Python version** | 3.12                                                                        |

Environment variables (`TRELLO_API_KEY`, `TRELLO_API_SECRET`, `TRELLO_CALLBACK_URL`) are configured in the Render dashboard under **Environment > Secret Files / Environment Variables**.

CircleCI triggers a Render deploy hook after all lint, test, and health check jobs pass. See `.circleci/config.yml` for details.

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
