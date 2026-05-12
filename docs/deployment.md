# Deployment

The FastAPI service runs on **Google Cloud Run**, with infrastructure and secrets modeled in **Terraform** under `infrastructure/terraform/`. **CircleCI** runs lint, tests, health checks, Terraform **validation only** (`fmt`/`validate` with no remote backend), and (on configured branches) **GCP app deploy**: Cloud Build plus **`gcloud run services update`**. **Terraform `apply` never runs in CI** — use your laptop (or another dedicated infra process) for **`terraform plan`/`apply`**. Production **environment variables** for the API live in **GCP Secret Manager** (wired into Cloud Run by Terraform), not in CircleCI.

**CircleCI** only needs variables the pipeline consumes (for example Trello credentials for e2e tests in the `test` job).

!!! tip "Who owns which env var?"
    - **GCP Secret Manager / Cloud Run** — production runtime secrets (`DATABASE_URL`, Trello, Anthropic, CORS, optional OTLP).
    - **CircleCI project settings** — values the `test` job needs (e.g. `TRELLO_API_KEY` for e2e tests).
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
              ┌──────────────┐
              │validate_infra│   Terraform fmt / validate (-backend=false)
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ deploy_gcp   │   Cloud Build + Cloud Run image rollout (no Terraform)
              └──────────────┘
```

Source: `.circleci/config.yml`. See **`infrastructure/terraform/README.md`** for GCP and CircleCI variable setup.

---

## 2. GCP Cloud Run — one-time setup

Provision Artifact Registry, secrets, IAM, and Cloud Run with Terraform (see **`infrastructure/terraform/README.md`**). After the first revision exists, set **`trello_callback_url`** to the value from **`terraform output trello_callback_hint`** and apply again so OAuth matches the live hostname.

### 2.1 Required secrets (typical)

| Key | Notes |
| --- | --- |
| `TRELLO_API_KEY` / `TRELLO_API_SECRET` | Same pair used for HW2; stored as Secret Manager secrets referenced by Terraform. |
| `TRELLO_CALLBACK_URL` | Must be **`https://<cloud-run-host>/auth/callback`** (see `trello_callback_hint`). |
| `DATABASE_URL` | Postgres DSN (e.g. Supabase); Secret Manager secret `issue-tracker-database-url` (name may vary per module). |
| `ANTHROPIC_API_KEY` | Without it `/ai/health` can report unconfigured. |
| `CORS_ALLOW_ORIGINS` | Comma-separated; include every frontend origin that calls the API. |

### 2.2 Optional tuning

| Key | Default |
| --- | --- |
| `CLAUDE_MODEL` | `claude-sonnet-4-5` |
| `AI_MAX_TOOL_HOPS` | `6` |
| `AI_MAX_TOKENS` | `1024` |
| `AI_ALLOW_MUTATIONS` | `false` |

---

## 3. Trello Power-Up — one-time setup

Visit `https://trello.com/power-ups/admin`, open your team's Power-Up, and ensure **Allowed Origins** contains:

- Your **Cloud Run** API origin (from **`terraform output -raw service_url`**, no trailing slash on the host you allow-list — follow Trello’s format rules).
- `https://<your-vercel-domain>.vercel.app` *(optional; only if any frontend code talks to Trello directly)*

Without this, Trello rejects the callback with `"Invalid return_url. The return URL should match the application's allowed origins."`

---

## 4. Vercel (frontend) — one-time setup

In the Vercel project for the frontend:

| Key | Value |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Your Cloud Run HTTPS URL (same as `SERVICE_BASE_URL` / `terraform output -raw service_url`). |

Set it for **Production** (and **Preview** if preview URLs should hit prod). `NEXT_PUBLIC_*` is *build-time*, so redeploy the frontend after changing it.

---

## 5. CircleCI — pipeline notes

**Functionally**, pushes run **`lint`**, **`test`**, **`health_check`**, and **`validate_infra`** in parallel for the first three plus infra validation. **`deploy_gcp`** runs after those succeed on branches **`main`** and **`hw3`** when GCP env vars are set (`GCP_CI_DEPLOY`, service account JSON, project id, etc.) — see **`infrastructure/terraform/README.md`**.

### 5.1 Extend the mypy step

The `lint` job's mypy invocation may omit newer components. For CI parity, extend `.circleci/config.yml` to include `components/ai_client_api/src` and `components/claude_ai_client_impl/src` if not already listed.

### 5.2 `ANTHROPIC_API_KEY` in CI?

The AI test suite uses a **stub Anthropic client**, so CI does **not** need the production key unless you add live-integration tests.

---

## 6. Verifying a deploy

Use the URL from Terraform (or the GCP console):

```bash
BASE="$(cd infrastructure/terraform && terraform output -raw service_url)"

curl -sf "$BASE/health"
# → {"status": "ok"}

curl -sf "$BASE/ai/health" | jq
# → status, model, allow_mutations, api_key_loaded, ...

open "$BASE/docs"
```

If `/ai/health` returns `"unconfigured"`, the Cloud Run service does not have **`ANTHROPIC_API_KEY`** configured in Secret Manager / env wiring.

---

## 7. Infrastructure-as-code and observability

| Area | Direction |
| --- | --- |
| IaC | Terraform in **`infrastructure/terraform/`** (Cloud Run, secrets, IAM). |
| Metrics | Prometheus at **`GET /metrics`**; optional OTLP via Terraform / env. |
| Dashboards | Local stack under **`infrastructure/monitoring/`** (Grafana + Prometheus). |

| Requirement       | Status                               | Plan                                                  |
| ----------------- | ------------------------------------ | ----------------------------------------------------- |
| IaC               | Terraform-managed Cloud Run + Secret Manager in `infrastructure/terraform/`. | Keep Terraform as the single source of truth; avoid parallel manual platform configs. |
| Request latency   | Prometheus histogram + OTel in `issue_tracker_service/telemetry.py`. | Scrape `/metrics` or export OTLP; visualize in Grafana (see `infrastructure/monitoring/`). |
| Success / failure | Counters with route / method / status and domain vs infra `failure_kind`. | Same dashboards as above. |
| Dashboards        | JSON dashboard under `infrastructure/monitoring/grafana/dashboards/`. | Import into Grafana Cloud or local docker-compose stack. |

CircleCI also runs **`validate_infra`** (Terraform fmt/validate) and can run **`deploy_gcp`** on `main` / `hw3` when GCP credentials are configured (see `infrastructure/terraform/README.md`).
