# Continuous Integration (CI/CD)

This project uses [CircleCI](https://circleci.com/) for continuous integration. The pipeline is defined in `.circleci/config.yml`.

## Pipeline Overview

On every push and pull request, three jobs run in parallel, followed by a deploy job:

| Job   | Purpose |
|-------|---------|
| **lint** | Static analysis and code quality checks (ruff, mypy) |
| **test** | Run the full test suite with coverage |
| **health_check** | Boots the FastAPI app and hits `/health` to verify startup |
| **deploy** | On success, POSTs to the Render deploy hook so Render rebuilds the service |

All four of `lint` / `test` / `health_check` / `deploy` must pass for the pipeline to be green.
The `deploy` job is a no-op if `RENDER_DEPLOY_HOOK_URL` is not configured in CircleCI project settings (useful for forks).

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

CircleCI only needs values the pipeline actually consumes. Everything runtime-only
(Anthropic key, CORS origins, OAuth callback URL) lives on Render — see
[Deployment](deployment.md) for the full matrix.

**Required in CircleCI project settings** (for the `test` and `deploy` jobs):

| Variable | Where it's used | Notes |
|---|---|---|
| `TRELLO_API_KEY` | `test` (e2e) | Your Trello API key. |
| `TRELLO_TOKEN` | `test` (e2e) | Trello OAuth token for the e2e fixture account. |
| `TRELLO_BOARD_ID` | `test` (e2e, optional) | Board ID to target in e2e tests. |
| `RENDER_DEPLOY_HOOK_URL` | `deploy` | Paste from Render → *Settings → Deploy Hook URL*. If empty, the deploy step is skipped. |

If the Trello vars are not set, e2e tests auto-skip.

**NOT needed in CircleCI**: `ANTHROPIC_API_KEY`, `AI_*`, `CORS_ALLOW_ORIGINS`,
`TRELLO_CALLBACK_URL`. The AI test suite uses a stub Anthropic client, and the
runtime values are consumed only by the Render-hosted process.

---

## Deploy Job

The `deploy` job is a thin wrapper around the Render deploy hook:

```yaml
- run:
    name: Trigger Render deploy
    command: |
      if [ -z "$RENDER_DEPLOY_HOOK_URL" ]; then
        echo "RENDER_DEPLOY_HOOK_URL not set; skipping deploy"; exit 0
      fi
      curl -X POST -f -s -o /dev/null -w "%{http_code}" "$RENDER_DEPLOY_HOOK_URL" \
        | grep -qE '^2[0-9]{2}$'
```

Render then pulls the latest commit on the configured branch, runs
`uv sync --all-extras`, and restarts the process with the environment variables
set in the Render dashboard. There is currently **no branch filter** on this
job — every green build on every branch redeploys. See
[Deployment → Optional hardening](deployment.md#52-gate-production-deploys-to-main)
for how to gate it to `main`.

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
