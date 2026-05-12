# Deployment

This service is deployed as a FastAPI app on [Render](https://render.com). The
**CircleCI pipeline** (`.circleci/config.yml`) is responsible for running
lint / test / health-check and, on success, **triggering a Render deploy hook**.
Render itself is where the production process runs and where production
**environment variables live** — CircleCI only needs env vars consumed by the
test suite.

!!! tip "Who owns which env var?"
    - **Render dashboard** — production runtime secrets (Anthropic, Trello, CORS).
    - **CircleCI project settings** — only values the `test` job needs (e.g. `TRELLO_API_KEY` for e2e tests).
    - **Vercel project settings** — frontend build-time env (`NEXT_PUBLIC_API_BASE_URL`).
    - **Trello Power-Up admin** — allowed origins + callback URL allow-list.

---

## 1. Pipeline shape

```
   git push
      │
      ▼
┌─────────────┐  ┌────────┐  ┌──────────────┐
│    lint     │  │  test  │  │ health_check │      (run in parallel)
└──────┬──────┘  └────┬───┘  └──────┬───────┘
       └─────────────┬┴─────────────┘
                     ▼
              ┌─────────────┐
              │   deploy    │   curl -X POST $RENDER_DEPLOY_HOOK_URL
              └──────┬──────┘
                     ▼
              ┌─────────────┐
              │   Render    │   rebuilds + restarts with latest code + env
              └─────────────┘
```

Source: `.circleci/config.yml`. Branch filters depend on your CircleCI workflow
(see **§5.2** in this doc for gating deploys to `main`).

---

## 2. Render — one-time setup

In the Render service dashboard → **Environment** add these variables.
All values are redacted / replaced by your real secrets.

### 2.1 Required

| Key                       | Example                                                     | Notes |
| ------------------------- | ----------------------------------------------------------- | ----- |
| `TRELLO_API_KEY`          | `f6edc179…`                                                 | Same pair your team already used for HW2. |
| `TRELLO_API_SECRET`       | `581e7c6f…`                                                 | Mark as **Secret** in Render. |
| `TRELLO_CALLBACK_URL`     | `https://ospsd-team7-issue-tracker.onrender.com/auth/callback` | Must point at Render, NOT `localhost`. |
| `ANTHROPIC_API_KEY`       | `sk-ant-…`                                                  | Mark as **Secret**. Without it `/ai/health` returns `unconfigured`. |
| `CORS_ALLOW_ORIGINS`      | `https://<project>.vercel.app,https://<custom-domain>`      | Comma-separated. Include every frontend origin that calls the API. |

### 2.2 Optional (defaults shown in parentheses)

| Key                      | Example                  | Default            |
| ------------------------ | ------------------------ | ------------------ |
| `CLAUDE_MODEL`           | `claude-sonnet-4-5`      | `claude-sonnet-4-5` |
| `AI_MAX_TOOL_HOPS`       | `6`                      | `6`                |
| `AI_MAX_TOKENS`          | `1024`                   | `1024`             |
| `AI_ALLOW_MUTATIONS`     | `true` or `false`        | `false`            |

### 2.3 Deploy hook

Render → **Settings** → *Deploy Hook URL*. Copy the URL into CircleCI as
`RENDER_DEPLOY_HOOK_URL` under **Project Settings → Environment Variables**.
This is how the `deploy` job triggers a redeploy.

---

## 3. Trello Power-Up — one-time setup

Visit `https://trello.com/power-ups/admin`, open your team's Power-Up, and
ensure **Allowed Origins** contains:

- `https://ospsd-team7-issue-tracker.onrender.com`  *(the Render backend — needed for the OAuth callback redirect)*
- `https://<your-vercel-domain>.vercel.app`  *(optional; only if any frontend code talks to Trello directly)*

Without this, Trello rejects the callback with
`"Invalid return_url. The return URL should match the application's allowed
origins."`

---

## 4. Vercel (frontend) — one-time setup

In the Vercel project for `ospsd-team7-issue-tracker-front`:

| Key                        | Value                                                           |
| -------------------------- | --------------------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | `https://ospsd-team7-issue-tracker.onrender.com`                |

Set it for **Production** (and **Preview** if you want preview URLs to hit
prod). `NEXT_PUBLIC_*` is *build-time*, so you must redeploy the frontend
after changing it.

---

## 5. CircleCI — do you need to change the pipeline?

**Functionally, no.** The existing pipeline (`lint` → `test` → `health_check`
→ `deploy`) picks up the new AI code automatically because `uv sync --all-extras`
resolves the new workspace members.

Two *optional* cleanups:

### 5.1 Extend the mypy step

The `lint` job's mypy invocation was written pre-HW3 and doesn't cover the
new AI components. `pyproject.toml`'s `mypy_path` already lists them, so
locally `uv run mypy .` works. For CI parity, update `.circleci/config.yml`:

```yaml
- run:
    name: Mypy (static type checking)
    command: |
      uv run mypy \
        components/issue_tracker_client_api/src \
        components/trello_client_impl/src \
        components/issue_tracker_adapter/src \
        components/issue_tracker_service/src \
        components/ai_client_api/src \
        components/claude_ai_client_impl/src
```

### 5.2 Gate production deploys to `main`

Currently every green branch triggers a redeploy. To restrict to `main`:

```yaml
workflows:
  ci:
    jobs:
      - lint
      - test
      - health_check
      - deploy:
          requires: [lint, test, health_check]
          filters:
            branches:
              only: main
```

### 5.3 `ANTHROPIC_API_KEY` in CI?

The AI test suite uses a **stub Anthropic client**, so CI does **not** need
the key. Only add it to CircleCI if you later write a live-integration e2e
test against real Claude.

---

## 6. Verifying a deploy

After the `deploy` job reports success:

```bash
# 1. The service is up
curl -s https://ospsd-team7-issue-tracker.onrender.com/health
# → {"status": "ok"}

# 2. The AI stack is configured
curl -s https://ospsd-team7-issue-tracker.onrender.com/ai/health | jq
# → {"status":"ok","model":"claude-sonnet-4-5","allow_mutations":false,"api_key_loaded":true}

# 3. The OpenAPI docs render
open https://ospsd-team7-issue-tracker.onrender.com/docs
```

If `/ai/health` returns `"unconfigured"`, Render doesn't have
`ANTHROPIC_API_KEY`; if it returns `"api_key_loaded": true` but chat calls
502, that's an upstream Anthropic issue (rate limit, quota, wrong model).

---

## 7. Infrastructure-as-Code & observability (HW3 follow-ups)

HW3 requires (1) IaC and (2) telemetry for latency / success / failure.
Current state and next steps:

| Requirement       | Status                               | Plan                                                  |
| ----------------- | ------------------------------------ | ----------------------------------------------------- |
| IaC               | Terraform-managed Cloud Run + Secret Manager in `infrastructure/terraform/`. | Keep Terraform as the single source of truth; avoid parallel manual platform configs. |
| Request latency   | Prometheus histogram + OTel in `issue_tracker_service/telemetry.py`. | Scrape `/metrics` or export OTLP; visualize in Grafana (see `infrastructure/monitoring/`). |
| Success / failure | Counters with route / method / status and domain vs infra `failure_kind`. | Same dashboards as above. |
| Dashboards        | JSON dashboard under `infrastructure/monitoring/grafana/dashboards/`. | Import into Grafana Cloud or local docker-compose stack. |

CircleCI also runs **`validate_infra`** (Terraform fmt/validate) and can run **`deploy_gcp`** on `main` / `hw3` when GCP credentials are configured (see `infrastructure/terraform/README.md`).
