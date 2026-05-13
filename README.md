# Issue Tracker Client: A Component-Based Trello Integration

[![CircleCI](https://dl.circleci.com/status-badge/img/circleci/H1UyoZTBnANBFPJu9yXQrw/RtX7q9iZYQCkKP2LcEeNrY/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/circleci/H1UyoZTBnANBFPJu9yXQrw/RtX7q9iZYQCkKP2LcEeNrY/tree/main)
<!-- [![Coverage](https://codecov.io/gh/riddhixraina/ospsd-team-07/branch/hw1/graph/badge.svg)](https://codecov.io/gh/riddhixraina/ospsd-team-07) -->
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

This repository provides a professional-grade, component-based Python system for issue tracking. It demonstrates a robust architecture by building an abstract interface, a concrete implementation backed by the [Trello REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/), a FastAPI service layer with OAuth 1.0a, an auto-generated HTTP client, and an adapter that provides location transparency.

The project emphasizes strict separation of concerns, dependency injection, and a comprehensive toolchain to enforce code quality and best practices.

**API changes:** See [`CHANGELOG.md`](CHANGELOG.md) for breaking changes when upgrading from older HW1/HW2 clients (shared vertical alignment: e.g. `Board.name` → `board_name` on the HTTP contract).

## Team Members

- **Somaditya Singh** (`ss20288`)
- **Saakshi Narayan** (`sn4230`)
- **Mingjian Li** (`ml8347`)
- **Joshua Leeman** (`jl17087`)
- **Riddhi Prasad** (`rrp4822`)

## Architectural Philosophy

This project is built on the principle of "programming integrated over time." The architecture is designed to combat complexity and ensure the system is maintainable and evolvable.

- **Component-Based Design:** The system is broken down into five distinct, self-contained components. Each component has a single responsibility and can be reused or replaced with minimal effort.
- **Interface-Implementation Separation:** Every piece of functionality is defined by an abstract **contract** implemented as an ABC (the "what") and fulfilled by a concrete **implementation** (the "how"). This decouples business logic from specific technologies (like Trello).
- **Dependency Injection:** Implementations are "injected" into the abstract contracts at import time. Consumers of the API only ever depend on the stable interface, not the volatile implementation details.
- **Location Transparency:** The adapter pattern allows consumers to use the same `Client` interface regardless of whether the implementation communicates with Trello directly or through the deployed FastAPI service.

## Core Components

The project is a `uv` workspace; primary packages include:

1. **`issue_tracker_client_api`**: Defines the abstract `Client` base class (ABC). This is the contract for what actions an issue tracker client can perform (e.g., `get_issues_in_list`, `get_board`, `get_boards`, `get_members_on_issue`).
2. **`trello_client_impl`**: Provides the `TrelloClient` class, a concrete implementation that uses the Trello API directly.
3. **`issue_tracker_service`**: A FastAPI application that wraps the Trello client behind REST endpoints with OAuth 1.0a authentication. Production deploy is **Google Cloud Run** via Terraform (**`terraform output service_url`** for the HTTPS URL — see Deployment).
4. **`issue_tracker_service_api_client`**: An auto-generated Python HTTP client created from the FastAPI service's OpenAPI specification using `openapi-python-client`.
5. **`issue_tracker_adapter`**: A service client adapter that implements the `Client` ABC by delegating to the auto-generated HTTP client, achieving location transparency.
6. **`chat_client_impl`**: A local in-memory chat client implementation that uses the shared `chat-client-api` contract from GitHub.
7. **`ai_client_api`**, **`claude_ai_client_impl`**, **`openai_ai_client_impl`** *(HW3)*: Provider-agnostic `AIClient` ABC and two concrete LLM stacks with typed tool calling to Trello and chat.

**Issue tracker vs AI wiring:** The adapter registers **`issue_tracker_client_api.get_client`** for library use. The **`/ai/*`** routes instead use FastAPI **`Depends(get_ai_client)`** to build a **request-scoped** `ClaudeAIClient` or `OpenAIAIClient` (see **`docs/ai-integration.md`**). The optional **`ai_client_api.register_client` / `get_client()`** pair is for non-FastAPI callers (scripts, tests).

## Project Structure

```
ospsd-team-07/
├── components/                              # Source packages (uv workspace members)
│   ├── issue_tracker_client_api/            # Abstract client base class (ABC)
│   ├── trello_client_impl/                  # Direct Trello implementation
│   ├── issue_tracker_service/               # FastAPI service (OAuth + REST)
│   ├── issue_tracker_service_api_client/    # Auto-generated HTTP client
│   ├── issue_tracker_adapter/               # Service client adapter
│   ├── ai_client_api/                       # HW3: AIClient ABC + types
│   ├── claude_ai_client_impl/               # HW3: Anthropic implementation
│   ├── openai_ai_client_impl/               # HW3: OpenAI implementation
│   └── chat_client_impl/                    # Local chat client implementation
├── tests/                                   # Integration and E2E tests
│   ├── integration/                         # Component integration tests
│   └── e2e/                                 # End-to-end tests (real Trello API)
├── docs/                                    # Documentation source files
├── .circleci/                               # CircleCI configuration
├── pyproject.toml                           # Project configuration (dependencies, tools)
└── uv.lock                                  # Locked dependency versions
```

## Project Setup

### 1. Prerequisites

- Python 3.12 or higher
- `uv` – A fast, all-in-one Python package manager

### 2. Initial Setup

1. **Install `uv`:**
    ```bash
    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Windows (PowerShell)
    irm https://astral.sh/uv/install.ps1 | iex
    ```

2. **Clone the Repository:**
    ```bash
    git clone https://github.com/riddhixraina/ospsd-team-07.git
    cd ospsd-team-07
    ```

3. **Set Up Trello Credentials (for E2E tests):**
    - Obtain your [Trello API Key](https://trello.com/app-key) and [Token](https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&name=ospsd-team-07&key=YOUR_API_KEY).
    - For local development, either:
      - Set environment variables:
        ```bash
        export TRELLO_API_KEY="your_api_key"
        export TRELLO_TOKEN="your_token"
        export TRELLO_BOARD_ID="your_board_id"  # Optional, for e2e tests
        ```
      - Or create `token.json` in the project root with `{"token": "your_token"}` and set `TRELLO_API_KEY`.
    - **Important:** Credential files contain secrets and are ignored by `.gitignore`.
    - For CI/CD: Set `TRELLO_API_KEY`, `TRELLO_TOKEN`, and `TRELLO_BOARD_ID` in CircleCI Project Settings.

4. **Create and Sync the Virtual Environment:**
    ```bash
    uv sync --all-extras
    ```
    This creates a `.venv` folder and installs all packages (including workspace members and development tools) defined in `uv.lock`.

5. **Activate the Virtual Environment:**
    ```bash
    # macOS / Linux
    source .venv/bin/activate
    # Windows (PowerShell)
    .venv\Scripts\Activate.ps1
    ```

## Development Workflow

All commands should be run from the project root with the virtual environment activated.

### Running the Toolchain

- **Linting & Formatting (Ruff):**
    The project uses Ruff with comprehensive rules configured in `pyproject.toml`.
    ```bash
    # Check for issues
    uv run ruff check .
    # Automatically fix issues
    uv run ruff check . --fix
    # Check formatting
    uv run ruff format --check .
    # Apply formatting
    uv run ruff format .
    ```

- **Static Type Checking (Mypy):**
    ```bash
    uv run mypy components/issue_tracker_client_api/src components/trello_client_impl/src components/issue_tracker_adapter/src components/issue_tracker_service/src
    ```

- **Testing (Pytest):**
    ```bash
    # Run all tests (unit, integration, e2e)
    uv run pytest

    # Run only unit tests (fast, no external dependencies)
    uv run pytest -m unit

    # Run only integration tests (mocked dependencies)
    uv run pytest -m integration

    # Run only end-to-end tests (requires Trello credentials; skips if missing)
    uv run pytest -m e2e

    # Run tests with coverage reporting
    uv run pytest --cov=components --cov-report=term-missing --cov-report=html:htmlcov
    ```

### Viewing Documentation

This project uses MkDocs for documentation.
```bash
# Start the live-reloading documentation server
uv run mkdocs serve
```
Open your browser to `http://127.0.0.1:8000` to view the site.

## Testing Infrastructure

The project implements a testing strategy designed for both local development and CI/CD environments:

### Test Categories

- **Unit Tests** (`components/*/tests/`): Fast, isolated tests with mocked dependencies
- **Integration Tests** (`tests/integration/`): Tests that verify component interactions and dependency injection
- **End-to-End Tests** (`tests/e2e/`): Full workflow tests against the real Trello API

### Test Markers

The project uses pytest markers to categorize tests:
```python
@pytest.mark.unit          # Fast unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.e2e          # End-to-end tests (skipped if credentials missing)
```

### Authentication in Tests

- **Local Development:** Set `TRELLO_API_KEY`, `TRELLO_TOKEN`, and optionally `TRELLO_BOARD_ID` in the environment, or use `token.json`.
- **CI/CD Environment:** Set the same variables in CircleCI Project Settings.
- **Missing Credentials:** E2E tests are skipped with a clear message; unit and integration tests run normally.

## Continuous Integration

The project includes a CircleCI configuration (`.circleci/config.yml`) with:

- **Lint Job:** Ruff (check + format) and Mypy
- **Test Job:** Unit, integration, and e2e tests with coverage; JUnit results and HTML coverage stored as artifacts

See [docs/ci-cd.md](docs/ci-cd.md) for detailed CI/CD setup instructions.

## Quick Start

1. **Install dependencies:** `uv sync --all-extras`
2. **Run tests:** `uv run pytest -v` or `uv run pytest -m "unit or integration" -v` (skip e2e if no credentials)
3. **Check code quality:** `uv run ruff check . && uv run ruff format --check .`
4. **Fix formatting:** `uv run ruff format .`
5. **View documentation:** `uv run mkdocs serve`

### Best Practices

- Run unit tests (`uv run pytest -m unit`) during development for fast feedback
- Use integration tests (`uv run pytest -m integration`) to verify dependency injection and component interactions
- Run full test suite (`uv run pytest`) before pushing to ensure CI compatibility
- The CircleCI pipeline provides automated validation on every push

## Deployment

### Google Cloud Run (primary — Infrastructure as Code)

Production-style hosting is modeled in Terraform under **`infrastructure/terraform/`**: Artifact Registry, Secret Manager-backed env vars, IAM, and Cloud Run ([runbook](infrastructure/terraform/README.md)).

- **`/health`:** Deployed instances expose **`GET /health`** (JSON). Verify with **`curl -sf "$(terraform output -raw service_url 2>/dev/null)/health"`** from **`infrastructure/terraform`** after apply, or use the URL below.
- **HTTPS URL:** After **`terraform apply`**, run **`terraform output -raw service_url`** for the authoritative Cloud Run URL (also shown in the GCP console under Cloud Run → your service).
- **Team GCP URL (document for graders / video):** [`https://issue-tracker-service-688420327904.us-central1.run.app`](https://issue-tracker-service-688420327904.us-central1.run.app) — yours may differ; always confirm with **`terraform output -raw service_url`**.
- Build the image from repo root (`Dockerfile`); the container runs **`alembic upgrade head` then uvicorn**, so Postgres/Supabase schemas stay aligned at startup (same behavior as **`docker-entrypoint.sh`** describes).
- Populate a gitignored **`secrets.tfvars`** (see `terraform.tfvars.example`). **Push the first Docker image**, then **`terraform apply`** once from your laptop to create wiring. Routine app updates: **[CircleCI `deploy_gcp`](infrastructure/terraform/README.md)** builds the image and **`gcloud run services update`** rolls the service. **Terraform stays off CI** — run **`terraform apply`** locally whenever infrastructure (not the app image) changes.
- `DATABASE_URL` remains your **Supabase** (or Cloud SQL, etc.) DSN—the database is independent of GCP unless you relocate it later.
- Trello OAuth: Cloud Run assigns the hostname on first revision. Run **`terraform output trello_callback_hint`** after the initial deploy and set **`trello_callback_url`** to that URL on the next apply.

### Database Migrations

Database schema changes are managed by **Alembic**. On Cloud Run and in the Docker image, **`docker-entrypoint.sh`** runs migrations before **uvicorn** starts.

**Running migrations locally:**

```bash
cd components/issue_tracker_service
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/issue_tracker"
uv run alembic upgrade head
```

**Creating a new migration:**

```bash
cd components/issue_tracker_service
uv run alembic revision --autogenerate -m "describe your change"
```

### Database Migrations (Cloud Run / Docker image)

Schema changes live in **`components/issue_tracker_service/alembic/`**. Docker and Cloud Run run Alembic at container startup (**`docker-entrypoint.sh`**).

```bash
# Local (cwd: components/issue_tracker_service)
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/issue_tracker"
uv run alembic -c alembic.ini upgrade head

# Root (same ini path as CI/production image)
uv run alembic -c components/issue_tracker_service/alembic.ini upgrade head
```

**Create a revision (same as above):**

```bash
cd components/issue_tracker_service
uv run alembic revision --autogenerate -m "describe your change"
```

### Rollback Procedure

**Cloud Run:** Move traffic back to an earlier revision in the console or via `gcloud run services update-traffic`.

> **Note:** Database migrations are not automatically rolled back. If a migration needs to be reverted, run `alembic downgrade -1` manually against the database.

### Monitoring & Observability

The service is instrumented with **OpenTelemetry** (FastAPI + `requests`) and exposes **Prometheus** metrics at **`GET /metrics`**.

**Prometheus (scrape from Cloud Run or local):**

- `issue_tracker_http_request_duration_seconds` (histogram)
- `issue_tracker_http_requests_total` (counter)
- `issue_tracker_http_request_outcomes_total` (counter with `outcome` and `failure_kind`)

**OTel (optional OTLP export):** histogram `http.server.request.duration`, counter `http.server.responses`, plus trace spans. On **GCP**, set OTLP via Terraform / Cloud Run env. Telemetry export is skipped when `OTEL_SDK_DISABLED=true` (CI / local).

For local dashboards, use `infrastructure/monitoring/docker-compose.yml` and `infrastructure/monitoring/prometheus.yml` (Grafana provisions **Issue Tracker KPI Dashboard**).

```bash
cd infrastructure/monitoring
docker compose up -d
```

### E2E Testing

Use the URL of the environment you are testing:

**Cloud Run:**

```bash
export SERVICE_BASE_URL="$(cd infrastructure/terraform && terraform output -raw service_url)"
```

See `tests/e2e/conftest.py` for the full list of required environment variables (`SERVICE_BASE_URL`, `SERVICE_SESSION_TOKEN`, etc.).

### Environment variables (GCP Secret Manager / local)

**GCP:** Production values for **`DATABASE_URL`**, **`TRELLO_*`**, Anthropic, CORS, and optional OTLP headers are modeled in **GCP Secret Manager** by Terraform. **Local dev:** copy **[`.env.example`](.env.example)** to `.env`.

| Variable | Description |
|---|---|
| `TRELLO_CALLBACK_URL` | Must match **`https://<cloud-run-host>/auth/callback`** (`terraform output trello_callback_hint`). |
| `AI_PROVIDER` | `claude` (default) or `openai` — selects the LLM stack (`issue_tracker_service.ai_deps`). |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Required when using OpenAI; model defaults to `gpt-4o-mini`. |
| `AI_STRUCTURED_OUTPUT` | When `true`, final model output must validate as structured JSON (HTTP 422 on failure). |
| `AI_HTTP_MAX_ATTEMPTS`, `AI_HTTP_RETRY_BASE_S`, `AI_HTTP_RETRY_MAX_S` | Retry/backoff around upstream LLM HTTP calls. |

### CI/CD pipeline

Every push triggers the following CircleCI workflow (see [`.circleci/config.yml`](.circleci/config.yml)):

1. **`lint`** — Ruff (check + format) and Mypy
2. **`test`** — Unit, integration, and E2E tests with coverage reporting
3. **`health_check`** — Starts the service locally and verifies `GET /health` returns 200
4. **`validate_infra`** — Validates Terraform (`terraform fmt`/validate with `-backend=false`)
5. **`deploy_gcp`** (**`main`** / **`hw3`**, after `validate_infra`) — Cloud Build pushes the image, then **Cloud Run** is updated to the new immutable tag (**no Terraform in CI**). Infra: **[`infrastructure/terraform/README.md`](infrastructure/terraform/README.md)** (CircleCI app deploy + laptop Terraform).

### A note on OAuth

Trello's API uses **OAuth 1.0a** (not OAuth 2.0). Our implementation follows the provider's required protocol. The service exposes `/auth/login` (initiate) and `/auth/callback` (exchange tokens) endpoints that handle the full OAuth 1.0a three-legged flow, issuing server-side session tokens for subsequent API calls.

For more details, see [docs/ci-cd.md](docs/ci-cd.md).

## Troubleshooting

### Database connection failure

**Symptom:** Service fails to start with a database connection error, or health check returns `503` with `"database": "unavailable"`.

**Possible causes:**

- `DATABASE_URL` is not set or has an invalid format (locally `.env`; on **Cloud Run**, Secret **`issue-tracker-database-url`**)
- Postgres not provisioned yet, unreachable, or paused
- Network / SSL / firewall between the service and the database

**Fix:**

1. **GCP:** in **Secret Manager**, confirm **`issue-tracker-database-url`** has an enabled **`latest`** version; read **Cloud Run** logs for Alembic/connection errors during startup.
2. Confirm your DB allows connections from Cloud Run (public IP vs VPC connector).

### Missing environment variables

**Symptom:** Service fails to start or features don't work (OAuth fails, AI features disabled).

**Fix:**

1. Compare [`.env.example`](.env.example) with **GCP Secret Manager** / Terraform outputs (`secret_manager_*_id`).
2. Ensure required secrets exist (**`latest`** versions on GCP).
3. Check **Cloud Run** revision logs for missing-variable errors.

### Migration failures

**Symptom:** Deploy fails during **Cloud Run** container startup (**Alembic** in **`docker-entrypoint.sh`**) before traffic is healthy.

**Possible causes:**

- A migration script has a syntax error or references a missing column/table
- The database is in an inconsistent state (e.g. a previous migration partially applied)

**Fix:**

1. Read deploy / revision logs for the Alembic error.
2. Inspect **`alembic_version`** in the database if needed.
3. Fix migrations and redeploy; trigger **`deploy_gcp`** (or **`gcloud run services update --image=…`**) with a new image. Use **`terraform apply`** only when infra definitions change. **`SKIP_ALEMBIC=true`** is only for emergency debugging (avoid on production Postgres).

### OpenTelemetry export issues

**Symptom:** No traces or metrics appear in your observability backend, but the service is running normally.

**Possible causes:**
- `OTEL_EXPORTER_OTLP_ENDPOINT` or `OTEL_EXPORTER_OTLP_HEADERS` are not set or incorrect
- `OTEL_SDK_DISABLED` is set to `true`
- The observability backend is rejecting requests (auth failure, quota exceeded)

**Fix:**

1. Verify `OTEL_SDK_DISABLED` is not `true` (Terraform / Cloud Run or local `.env`).
2. Confirm **`OTEL_EXPORTER_OTLP_*`** endpoints and headers match your vendor (URL-encoded headers where required).
3. Check **Cloud Run** logs for export warnings — the app keeps running if export fails.

## License

[MIT License](LICENSE)