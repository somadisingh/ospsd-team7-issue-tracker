# Issue Tracker Client: A Component-Based Trello Integration

[![CircleCI](https://dl.circleci.com/status-badge/img/circleci/H1UyoZTBnANBFPJu9yXQrw/RtX7q9iZYQCkKP2LcEeNrY/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/circleci/H1UyoZTBnANBFPJu9yXQrw/RtX7q9iZYQCkKP2LcEeNrY/tree/main)
<!-- [![Coverage](https://codecov.io/gh/riddhixraina/ospsd-team-07/branch/hw1/graph/badge.svg)](https://codecov.io/gh/riddhixraina/ospsd-team-07) -->
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

This repository provides a professional-grade, component-based Python client for issue tracking. It demonstrates a robust architecture by building an abstract interface and a concrete implementation backed by the [Trello REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/).

The project emphasizes strict separation of concerns, dependency injection, and a comprehensive toolchain to enforce code quality and best practices.

## Team Members

- **Somaditya Singh** (`ss20288`)
- **Saakshi Narayan** (`sn4230`)
- **Mingjian Li** (`ml8347`)
- **Joshua Leeman** (`jl17087`)
- **Riddhi Prasad** (`rrp4822`)

## Architectural Philosophy

This project is built on the principle of "programming integrated over time." The architecture is designed to combat complexity and ensure the system is maintainable and evolvable.

- **Component-Based Design:** The system is broken down into two distinct, self-contained components. Each component has a single responsibility and can be reused or replaced with minimal effort.
- **Interface-Implementation Separation:** Every piece of functionality is defined by an abstract **contract** implemented as an ABC (the "what") and fulfilled by a concrete **implementation** (the "how"). This decouples business logic from specific technologies (like Trello).
- **Dependency Injection:** Implementations are "injected" into the abstract contracts at import time. Consumers of the API only ever depend on the stable interface, not the volatile implementation details.

## Core Components

The project is a `uv` workspace containing two primary packages:

1. **`issue_tracker_client_api`**: Defines the abstract `Client` base class (ABC). This is the contract for what actions an issue tracker client can perform (e.g., `get_issues_in_list`, `get_board`, `get_boards`, `get_members_on_issue`).
2. **`trello_client_impl`**: Provides the `TrelloClient` class, a concrete implementation that uses the Trello API to perform the actions defined in the `Client` abstraction.

## Project Structure

```
ospsd-team-07/
├── components/                      # Source packages (uv workspace members)
│   ├── issue_tracker_client_api/    # Abstract client base class (ABC)
│   └── trello_client_impl/         # Trello-specific client implementation
├── tests/                          # Integration and E2E tests
│   ├── integration/                # Component integration tests
│   └── e2e/                        # End-to-end tests (real Trello API)
├── docs/                            # Documentation source files
├── .circleci/                      # CircleCI configuration
├── conftest.py                     # Pytest fixtures
├── pyproject.toml                  # Project configuration (dependencies, tools)
└── uv.lock                         # Locked dependency versions
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
    uv run mypy components/issue_tracker_client_api/src components/trello_client_impl/src
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

## License

[MIT License](LICENSE)
* **Somaditya Singh** (`ss20288`)
* **Saakshi Narayan** (`sn4230`)
* **Mingjian Li** (`ml8347`)
* **Joshua Leeman** (`jl17087`)
* **Riddhi Prasad** (`rrp4822`)

## Project Description
Welcome to the repository for Team 7! This project focuses on developing an interface and implementation for Trello. Our goal is to collaborate effectively to deliver a robust and scalable solution using the best software development practices.

## Setup Instructions
1. **Clone the repository:**
   ```bash
   git clone https://github.com/somadisingh/ospsd-team7-issue-tracker.git
   
## LICENSE
[MIT LICENSE] - see the [LICENSE](LICENSE) file for details.

## Deployment

Deployment for this project is already set up for both Render and CircleCI.

### How Deployment is Handled

- **Render:**  
  The codebase is configured for easy deployment on [Render](https://render.com) as a web service. Once you link your GitHub repository to Render and provide the required environment variables (`TRELLO_API_KEY`, `TRELLO_API_SECRET`, etc.), Render automatically installs dependencies, performs the initial database migration if necessary, and launches the service using Gunicorn and Uvicorn.  
  You can find the recommended build and start commands, as well as environment configuration tips, in the deployment instructions above.

- **CircleCI:**  
  We use [CircleCI](https://circleci.com) for continuous integration. On every push to the repository, CircleCI runs all linting, formatting, type checking, and testing jobs (unit, integration, and e2e, if credentials are present). CI is configured in the [`.circleci/config.yml`](.circleci/config.yml) file.  
  For continuous deployment, CircleCI can notify Render to trigger a redeploy via a [Render Deploy Hook](https://render.com/docs/deploy-hooks) after successful checks. This is achieved with a simple `curl` command step in the CircleCI pipeline that calls the Render deploy hook URL.

**In summary:**
- Push code → CircleCI runs checks/tests → (Optional) CircleCI notifies Render to deploy → Render automatically builds and serves the app.

For more details, review `docs/ci-cd.md` and the [project README deployment instructions](#deployment).

If you wish to modify or extend deployment, refer to the configuration in `.circleci/config.yml` and your Render dashboard settings.