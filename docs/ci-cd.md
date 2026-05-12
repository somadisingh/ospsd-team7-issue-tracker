# Continuous Integration (CI/CD)

This project uses [CircleCI](https://circleci.com/) for continuous integration. The pipeline is defined in `.circleci/config.yml`.

## Pipeline Overview

On every push and pull request, **`lint`**, **`test`**, and **`health_check`** run in parallel, along with **`validate_infra`** (Terraform fmt/validate with `-backend=false`).

| Job   | Purpose |
|-------|---------|
| **lint** | Static analysis and code quality checks (ruff, mypy) |
| **test** | Run the full test suite with coverage |
| **health_check** | Boots the FastAPI app and hits `/health` to verify startup |
| **validate_infra** | Terraform `fmt -check` and `validate` under `infrastructure/terraform` |

**`deploy_gcp`** runs only after **`lint`**, **`test`**, **`health_check`**, and **`validate_infra`** succeed, and only on branches **`main`** and **`hw3`**. It is enabled when GCP-related project variables are set — see **`infrastructure/terraform/README.md`** (*CircleCI — app deploy only*).

---

## Lint Job

Runs the same checks you can run locally:

| Step | Command |
|------|---------|
| Ruff (linting) | `uv run ruff check .` |
| Ruff (format) | `uv run ruff format --check .` |
| Mypy | `uv run mypy components/issue_tracker_client_api/src components/trello_client_impl/src components/issue_tracker_adapter/src components/issue_tracker_service/src` |

If any step fails, the build fails. Fix locally with:

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy components/issue_tracker_client_api/src components/trello_client_impl/src components/issue_tracker_adapter/src components/issue_tracker_service/src
```

!!! note "HW3 — extending mypy to new components"
    `pyproject.toml`'s `mypy_path` already includes `ai_client_api` and
    `claude_ai_client_impl`, so `uv run mypy .` works locally. For full CI
    parity, extend the `Mypy` step in `.circleci/config.yml` to also type-check
    `components/ai_client_api/src` and `components/claude_ai_client_impl/src`.

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

CircleCI only needs values the pipeline actually consumes. Production runtime secrets (Anthropic, CORS, OAuth callback URL, database URL) are configured for **Cloud Run** via **GCP Secret Manager** and Terraform — see [Deployment](deployment.md).

**Required in CircleCI project settings** (for the `test` job when running e2e):

| Variable | Where it's used | Notes |
|---|---|---|
| `TRELLO_API_KEY` | `test` (e2e) | Your Trello API key. |
| `TRELLO_TOKEN` | `test` (e2e) | Trello OAuth token for the e2e fixture account. |
| `TRELLO_BOARD_ID` | `test` (e2e, optional) | Board ID to target in e2e tests. |

If the Trello vars are not set, e2e tests auto-skip.

**NOT needed in CircleCI** for normal CI: `ANTHROPIC_API_KEY`, `AI_*`, `CORS_ALLOW_ORIGINS`, `TRELLO_CALLBACK_URL`. The AI test suite uses a stub Anthropic client; runtime values are consumed by the deployed Cloud Run service.

---

## GCP deploy on `main` / `hw3`

When **lint**, **test**, **health_check**, and **validate_infra** succeed on **`main`** or **`hw3`**, CircleCI runs **`deploy_gcp`**. Enable it with **`GCP_CI_DEPLOY=1`**, **`GCP_SA_KEY_JSON_B64`**, and **`GCP_PROJECT_ID`**. That job **builds and pushes** the container image and **updates Cloud Run** to the new tag. **Terraform is not executed in CircleCI**; run **`terraform apply`** from your laptop when infrastructure changes. Setup: **`infrastructure/terraform/README.md`** (CircleCI app deploy).

---

## Local Parity

To reproduce the CI pipeline locally:

```bash
# Lint (same as CI)
uv run ruff check .
uv run ruff format --check .
uv run mypy components/issue_tracker_client_api/src components/trello_client_impl/src components/issue_tracker_adapter/src components/issue_tracker_service/src

# Test (same as CI)
uv run pytest -m "unit or integration or e2e" --cov=components -v
```
