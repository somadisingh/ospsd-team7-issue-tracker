# Continuous Integration (CI/CD)

This project uses [CircleCI](https://circleci.com/) for continuous integration. The pipeline is defined in `.circleci/config.yml`.

## Pipeline Overview

On every push and pull request, two jobs run in parallel:

| Job   | Purpose |
|-------|---------|
| **lint** | Static analysis and code quality checks |
| **test** | Run the full test suite with coverage |

Both jobs must pass for the build to succeed.

---

## Lint Job

Runs the same checks you can run locally:

| Step | Command |
|------|---------|
| Ruff (linting) | `uv run ruff check .` |
| Ruff (format) | `uv run ruff format --check .` |
| Mypy | `uv run mypy components/issue_tracker_client_api/src components/trello_client_impl/src` |

If any step fails, the build fails. Fix locally with:

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy components/issue_tracker_client_api/src components/trello_client_impl/src
```

---

## Test Job

Runs the full test suite:

```bash
uv run pytest -m "unit or integration or e2e" \
  --junitxml=test-results/junit.xml \
  --cov=components \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  -v
```

### Artifacts

- **Test results**: JUnit XML stored for test result reporting in the CircleCI UI.
- **Coverage report**: HTML coverage report stored as an artifact (download from the job page).

### Environment Variables

For e2e tests that hit the real Trello API, set these in **CircleCI Project Settings → Environment Variables**:

- `TRELLO_API_KEY` – Your Trello API key
- `TRELLO_TOKEN` – Your Trello token
- `TRELLO_BOARD_ID` – (Optional) Board ID for e2e tests

If these are not set, e2e tests are skipped.

---

## Local Parity

To reproduce the CI pipeline locally:

```bash
# Lint (same as CI)
uv run ruff check .
uv run ruff format --check .
uv run mypy components/issue_tracker_client_api/src components/trello_client_impl/src

# Test (same as CI)
uv run pytest -m "unit or integration or e2e" --cov=components -v
```
