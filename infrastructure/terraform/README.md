# GCP Cloud Run — Terraform reference

This document describes **what Terraform manages in GCP** and **how Cloud Run gets plaintext vs Secret Manager–backed environment variables**. For CI/CD notes see repo **`docs/deployment.md`** and **`.circleci/config.yml`**.

---

## GCP resources (`main.tf`)

| Area | Behavior |
|------|----------|
| **Project APIs** | Enables Cloud Run, Artifact Registry, Secret Manager, IAM (`google_project_service`). |
| **Runtime identity** | Service account **`issue-tracker-run`** (`google_service_account.issue_tracker`). Cloud Run revisions run as this SA. |
| **Artifact Registry** | Docker repository (`google_artifact_registry_repository.docker`), default id **`issue-tracker`**. |
| **Secret Manager — secrets** | Always created: **`{prefix}-database-url`**, **`{prefix}-trello-api-key`**, **`{prefix}-trello-api-secret`**. Optionally created when AI/OTLP wiring is enabled: **`{prefix}-anthropic-api-key`**, **`{prefix}-openai-api-key`**, **`{prefix}-otlp-headers`** (`google_secret_manager_secret`, some with `count`). |
| **Secret Manager — versions** | Terraform may create **`google_secret_manager_secret_version`** for payloads supplied via Terraform variables (`manage_secret_versions_in_terraform`). Where versions exist in Terraform, **`lifecycle.ignore_changes = [secret_data]`** stops later applies from overwriting payloads rotated in GCP. |
| **Secret IAM** | One **`roles/secretmanager.secretAccessor`** binding per distinct secret id the runtime needs (`google_secret_manager_secret_iam_member.run_accessor`): core secrets, optional shells above, plus every **`cloud_run_secret_environment_variables`** value. |
| **Cloud Run v2** | Service **`google_cloud_run_v2_service`** (optional via **`deploy_cloud_run_service`**): image digest from **`region-docker.pkg.dev/project/repo/image:tag`**, port **8080**, **`/health`** startup probe, scaling 0–5, 1 CPU / 512Mi. |
| **Invoker IAM** | **`google_cloud_run_v2_service_iam_member`** grants **`roles/run.invoker`** to **`allUsers`** (public HTTP). Remove this resource if your org requires authenticated ingress only. |

**Container image.** Terraform sets **`template.containers[0].image`** from variables, then **`lifecycle.ignore_changes`** on **`image`** so routine app deploys (e.g. **`gcloud run services update`** from CircleCI) can change the image without Terraform reverting it on the next apply.

---

## Plaintext environment variables

Terraform builds **`plain_env_pairs`** and emits one **`dynamic "env"`** block per entry as normal **`value`** strings on Cloud Run.

**Merge rule.** `merge(var.cloud_run_plain_environment_variables, { …built-ins… })` — keys defined **later** win. Terraform adds built-ins **after** your map, so **built-ins override duplicate keys** in **`cloud_run_plain_environment_variables`**.

**Built-ins** (always or when non-empty):

| Variable(s) | Source |
|-------------|--------|
| **`OTEL_SERVICE_NAME`** | **`otel_service_name`** |
| **`OTEL_SDK_DISABLED`** | **`false`** |
| **`AI_ALLOW_MUTATIONS`** | **`ai_allow_mutations`** → **`"true"`** / **`"false"`** |
| **`SKIP_ALEMBIC`** | **`skip_alembic`** → **`"true"`** / **`"false"`** |
| **`OTEL_EXPORTER_OTLP_ENDPOINT`**, **`OTEL_EXPORTER_OTLP_PROTOCOL`** | Set when **`otel_exporter_otlp_endpoint`** is non-empty (**`http/protobuf`**). |
| **`TRELLO_CALLBACK_URL`** | When **`trello_callback_url`** is non-empty (trimmed). |

**Extensions.** **`cloud_run_plain_environment_variables`** is an arbitrary **`map(string)`** merged into the same block (keys above still win on collision).

---

## Secret-backed environment variables

Terraform builds **`secret_env_bindings`** and emits **`env` + `value_source.secret_key_ref`** so Cloud Run reads **Secret Manager** at runtime (secret id + version id/`latest`).

### Core bindings (always present when Cloud Run is deployed)

| Env var | Secret id (default **`prefix` = `issue-tracker`) | Version |
|---------|-----------------------------------------------|---------|
| **`DATABASE_URL`** | **`{prefix}-database-url`** | **`latest`** |
| **`TRELLO_API_KEY`** | **`{prefix}-trello-api-key`** | **`latest`** |
| **`TRELLO_API_SECRET`** | **`{prefix}-trello-api-secret`** | **`latest`** |

### Optional bindings (expression-gated in **`main.tf`**)

| Env var | Secret id | Mounting / version notes |
|---------|-----------|--------------------------|
| **`ANTHROPIC_API_KEY`** | **`{prefix}-anthropic-api-key`** | Included when Anthropic shell or Terraform-supplied key path is enabled. **`latest`**. |
| **`OPENAI_API_KEY`** | **`{prefix}-openai-api-key`** | Included when OpenAI is enabled **and** Cloud Run is allowed to reference a version: with Terraform-managed OpenAI payloads, **`latest`**; otherwise **`openai_api_key_secret_version`** must be set (e.g. **`latest`** or a numeric version) so GCP never mounts an empty secret. |
| **`OTEL_EXPORTER_OTLP_HEADERS`** | **`{prefix}-otlp-headers`** | Included only when OTLP headers mounting is enabled; version is **`latest`** if Terraform manages OTLP payload text, otherwise **`otlp_headers_secret_version`** (explicit version string). |

### Extension map — **`cloud_run_secret_environment_variables`**

**Type:** **`map(string)`** — env name → **existing** Secret Manager **secret id** (short id, same GCP project).

**Effects:**

1. Each pair becomes another **`secret_key_ref`** entry with **`version = latest`**.
2. Each distinct secret id is included in **`accessor_secret_ids`** so **`issue-tracker-run`** receives **`secretAccessor`** on that secret.

Secrets **must already exist** (and normally have at least one **enabled** version) before Cloud Run can start with those refs.

---

## Duplicate env names

Do not reuse the same container env name across built-in plaintext, **`cloud_run_plain_environment_variables`**, **`secret_env_bindings`**, and **`cloud_run_secret_environment_variables`**. Terraform reduces secret bindings with **`for b in secret_env_bindings : b.name => b`**, which requires **unique names**.

---

## Relation to CI / routine deploys

Application releases typically **push a new image** and **`gcloud run services update`** the service **without** running Terraform. Terraform continues to own **service shape**, **IAM**, **Secret Manager resources/bindings**, and **non-image** container configuration unless you change **`main.tf`** / variables and **`terraform apply`** again.
