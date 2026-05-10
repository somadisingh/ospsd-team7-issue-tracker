# Issue Tracker Client: A Component-Based Trello Integration

[![CircleCI](https://dl.circleci.com/status-badge/img/circleci/H1UyoZTBnANBFPJu9yXQrw/RtX7q9iZYQCkKP2LcEeNrY/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/circleci/H1UyoZTBnANBFPJu9yXQrw/RtX7q9iZYQCkKP2LcEeNrY/tree/main)
<!-- [![Coverage](https://codecov.io/gh/riddhixraina/ospsd-team-07/branch/hw1/graph/badge.svg)](https://codecov.io/gh/riddhixraina/ospsd-team-07) -->
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

This repository provides a professional-grade, component-based Python system for issue tracking. It demonstrates a robust architecture by building an abstract interface, a concrete implementation backed by the [Trello REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/), a FastAPI service layer with OAuth 1.0a, an auto-generated HTTP client, and an adapter that provides location transparency.

The project emphasizes strict separation of concerns, dependency injection, and a comprehensive toolchain to enforce code quality and best practices.

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

The project is a `uv` workspace containing five packages:

1. **`issue_tracker_client_api`**: Defines the abstract `Client` base class (ABC). This is the contract for what actions an issue tracker client can perform (e.g., `get_issues_in_list`, `get_board`, `get_boards`, `get_members_on_issue`).
2. **`trello_client_impl`**: Provides the `TrelloClient` class, a concrete implementation that uses the Trello API directly.
3. **`issue_tracker_service`**: A FastAPI application that wraps the Trello client behind REST endpoints with OAuth 1.0a authentication. Deployed on [Render](https://ospsd-team7-issue-tracker.onrender.com).
4. **`issue_tracker_service_api_client`**: An auto-generated Python HTTP client created from the FastAPI service's OpenAPI specification using `openapi-python-client`.
5. **`issue_tracker_adapter`**: A service client adapter that implements the `Client` ABC by delegating to the auto-generated HTTP client, achieving location transparency.
6. **`chat_client_impl`**: A local in-memory chat client implementation that uses the shared `chat-client-api` contract from GitHub.

## Project Structure

```
ospsd-team-07/
├── components/                              # Source packages (uv workspace members)
│   ├── issue_tracker_client_api/            # Abstract client base class (ABC)
│   ├── trello_client_impl/                  # Direct Trello implementation
│   ├── issue_tracker_service/               # FastAPI service (OAuth + REST)
│   ├── issue_tracker_service_api_client/    # Auto-generated HTTP client
│   ├── issue_tracker_adapter/               # Service client adapter
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

The FastAPI service is deployed on [Render](https://ospsd-team7-issue-tracker.onrender.com) with continuous deployment via CircleCI.

| Setting | Value |
|---|---|
| **Platform** | [Render](https://render.com) (Web Service) |
| **Live URL** | `https://ospsd-team7-issue-tracker.onrender.com` |
| **Health check** | `https://ospsd-team7-issue-tracker.onrender.com/health` |
| **Build command** | `pip install uv && uv sync --all-extras` |
| **Start command** | `uv run uvicorn issue_tracker_service.main:app --host 0.0.0.0 --port $PORT` |

### Deployment with Render Blueprint

The project uses a **Render Blueprint** ([`render.yaml`](render.yaml)) to define all infrastructure as code. When the repository is connected to Render, the platform reads `render.yaml` and automatically provisions and configures the declared resources.

**How it works:**

1. `render.yaml` lives in the repository root and declares the web service, database, and environment variables.
2. When you connect the repo to Render (Dashboard → New → Blueprint → select this GitHub repo), Render syncs infrastructure state with the blueprint definition.
3. On every push to the `main` branch, Render pulls the latest code, runs the build, executes pre-deploy commands (migrations), and starts the service.

**What `render.yaml` defines:**

| Resource | Configuration |
|---|---|
| **Web Service** | `issue-tracker-service` — Python runtime, starter plan, health check at `/health` |
| **Database** | `issue-tracker-db` — PostgreSQL (`issue_tracker` database), starter plan |
| **Build** | `pip install uv && uv sync --all-extras` |
| **Start** | `uv run uvicorn issue_tracker_service.main:app --host 0.0.0.0 --port $PORT` |
| **Pre-deploy** | Installs dependencies and runs Alembic migrations before each deploy |

#### DATABASE_URL provisioning

The `DATABASE_URL` environment variable is **automatically provisioned** by Render. In `render.yaml`, it is mapped from the blueprint database definition:

```yaml
- key: DATABASE_URL
  fromDatabase:
    name: issue-tracker-db
    property: connectionString
```

Render creates the PostgreSQL instance and injects the connection string into the web service at runtime. No manual configuration is needed for the database URL.

#### Setting secrets in the Render dashboard

Several environment variables contain sensitive values and are marked with `sync: false` in `render.yaml`. This means they are **not** stored in version control — you must set them manually in the Render dashboard.

**Steps:** Render Dashboard → select `issue-tracker-service` → Environment → add each variable.

| Variable | Description | Where to get it |
|---|---|---|
| `TRELLO_API_KEY` | Trello API key for OAuth | [Trello Power-Up Admin](https://trello.com/power-ups/admin) |
| `TRELLO_API_SECRET` | Trello API secret (consumer secret) | Same Trello Power-Up Admin page |
| `ANTHROPIC_API_KEY` | Anthropic API key for AI features | [Anthropic Console](https://console.anthropic.com/) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint URL (e.g. Grafana, Honeycomb) | Your observability backend account |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth headers for OTLP export (e.g. `Authorization=Basic%20...`) | Your observability backend account |

**Non-secret variables** (set automatically from `render.yaml`):

| Variable | Value |
|---|---|
| `OTEL_SERVICE_NAME` | `issue-tracker-service` |
| `TRELLO_CALLBACK_URL` | `https://ospsd-team7-issue-tracker.onrender.com/auth/callback` |
| `AI_ALLOW_MUTATIONS` | `true` |
| `OTEL_SDK_DISABLED` | `false` |

### Database Migrations

Database schema changes are managed by **Alembic**. Migrations run automatically on every deploy via the `preDeployCommand` in `render.yaml`:

```
pip install uv && uv sync --all-extras && cd components/issue_tracker_service && uv run alembic upgrade head
```

This ensures the database schema is always up-to-date before the new version of the service starts accepting traffic.

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

### Rollback Procedure

If a deployment introduces a problem, you can roll back to a previous version:

1. Go to the **Render Dashboard** → select `issue-tracker-service` → **Events** tab.
2. Find the last known good deploy in the deploy history.
3. Click on that deploy and select **Manual Deploy** (or "Redeploy").
4. Render will rebuild and deploy from that commit.

Render keeps the previous version running if a deploy fails its health check, so the service remains available during failed deployments.

> **Note:** Database migrations are not automatically rolled back. If a migration needs to be reverted, run `uv run alembic downgrade -1` manually against the database.

### Monitoring & Observability

The service is instrumented with **OpenTelemetry** for distributed tracing and HTTP metrics. The `telemetry.py` module auto-instruments FastAPI endpoints and the `requests` library (used for Trello API calls).

**What is collected:**

- Request duration histograms (`http.server.duration`) with route and status code attributes
- Trace spans for all HTTP requests (including outbound Trello API calls)
- Custom HTTP metrics middleware for success/failure rate tracking

**To enable telemetry export in production:**

Set the following environment variables in the Render dashboard (see "Setting secrets" above):

- `OTEL_EXPORTER_OTLP_ENDPOINT` — your OTLP-compatible backend URL
- `OTEL_EXPORTER_OTLP_HEADERS` — authentication headers for the backend

Telemetry is disabled when `OTEL_SDK_DISABLED=true` (used in CI and local development).

### E2E Testing

The stable base URL for end-to-end tests against the deployed service is:

```
https://ospsd-team7-issue-tracker.onrender.com
```

Set this in your environment or CI configuration:

```bash
export SERVICE_BASE_URL="https://ospsd-team7-issue-tracker.onrender.com"
```

See `tests/e2e/conftest.py` for the full list of required environment variables (`SERVICE_BASE_URL`, `SERVICE_SESSION_TOKEN`, etc.).

### Environment variables (configured in Render dashboard)

| Variable | Description |
|---|---|
| `TRELLO_API_KEY` | Trello API key |
| `TRELLO_API_SECRET` | Trello API secret (consumer secret for OAuth) |
| `TRELLO_CALLBACK_URL` | OAuth callback URL (e.g. `https://ospsd-team7-issue-tracker.onrender.com/auth/callback`) |

### CI/CD pipeline

Every push triggers the following CircleCI workflow (see [`.circleci/config.yml`](.circleci/config.yml)):

1. **`lint`** — Ruff (check + format) and Mypy
2. **`test`** — Unit, integration, and E2E tests with coverage reporting
3. **`health_check`** — Starts the service locally and verifies `GET /health` returns 200
4. **`validate_infra`** — Validates `render.yaml` YAML syntax
5. **`deploy`** — Triggers a Render deploy hook (runs only after all jobs above pass)

### A note on OAuth

Trello's API uses **OAuth 1.0a** (not OAuth 2.0). Our implementation follows the provider's required protocol. The service exposes `/auth/login` (initiate) and `/auth/callback` (exchange tokens) endpoints that handle the full OAuth 1.0a three-legged flow, issuing server-side session tokens for subsequent API calls.

For more details, see [docs/ci-cd.md](docs/ci-cd.md).

## Troubleshooting

### Database connection failure

**Symptom:** Service fails to start with a database connection error, or health check returns `503` with `"database": "unavailable"`.

**Possible causes:**
- `DATABASE_URL` is not set or has an invalid format
- The PostgreSQL instance is not yet provisioned (check Render dashboard → Databases)
- Network connectivity issue between the web service and database

**Fix:**
1. Verify the database is running in the Render dashboard.
2. Check that `DATABASE_URL` is correctly linked in the service's environment variables (it should show as "From issue-tracker-db").
3. If the database was recently created, wait a few minutes for provisioning to complete.

### Missing environment variables

**Symptom:** Service fails to start or features don't work (OAuth fails, AI features disabled).

**Fix:**
1. Compare the variables in your Render service environment against the list in [`.env.example`](.env.example).
2. Ensure all `sync: false` secrets are set in the Render dashboard (see "Setting secrets" section above).
3. Check the service logs in Render for specific "missing variable" error messages.

### Migration failures

**Symptom:** Deploy fails during the pre-deploy command with an Alembic error.

**Possible causes:**
- A migration script has a syntax error or references a non-existent column/table
- The database is in an inconsistent state (e.g., a previous migration was partially applied)

**Fix:**
1. Check the deploy logs in Render for the specific Alembic error message.
2. If a migration was partially applied, connect to the database and inspect the `alembic_version` table.
3. Fix the migration script, commit, and push to trigger a new deploy.
4. As a last resort, manually run `uv run alembic downgrade -1` and then re-deploy.

### OpenTelemetry export issues

**Symptom:** No traces or metrics appear in your observability backend, but the service is running normally.

**Possible causes:**
- `OTEL_EXPORTER_OTLP_ENDPOINT` or `OTEL_EXPORTER_OTLP_HEADERS` are not set or incorrect
- `OTEL_SDK_DISABLED` is set to `true`
- The observability backend is rejecting requests (auth failure, quota exceeded)

**Fix:**
1. Verify `OTEL_SDK_DISABLED` is `false` in the Render environment.
2. Check that `OTEL_EXPORTER_OTLP_ENDPOINT` points to a valid OTLP endpoint.
3. Verify the auth headers in `OTEL_EXPORTER_OTLP_HEADERS` are correct and URL-encoded.
4. Check the service logs for OTel export warnings — the service continues running even if export fails.

## License

[MIT License](LICENSE)