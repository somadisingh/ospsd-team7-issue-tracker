# GCP Cloud Run IaC

Terraform provisions:

- Artifact Registry Docker repository (`artifact_repository_id`, default `issue-tracker`).
- **Secret Manager** secret *resources* (`google_secret_manager_secret`) for credentials; **optional** Terraform-managed *versions* controlled by `manage_secret_versions_in_terraform`.
- Per-secret `lifecycle.ignore_changes` on **payload fields** when Terraform *does* manage versions, so later rotations in GCP are not reverted.
- Dedicated Cloud Run runtime service account with `roles/secretmanager.secretAccessor`.
- Cloud Run v2 service (skippable via `deploy_cloud_run_service` for phased rollout) with public `roles/run.invoker` unless you remove that IAM block.

If your org **blocks unauthenticated ingress**, remove `google_cloud_run_v2_service_iam_member.public_invoker` and tighten IAM (Identity-Aware Proxy, etc.).

The application image (`Dockerfile` at repo root) runs **Alembic then uvicorn**, so Postgres / Supabase schema stays current on each revision startup.

---

## Mode A — GCP-only secret payloads (nothing sensitive in Terraform)

Use this when **`manage_secret_versions_in_terraform = false`**. Terraform creates **empty secret shells** (`issue-tracker-database-url`, `…-trello-api-key`, `…-trello-api-secret`) and IAM **only**; credentials never pass through `TF_VAR_*` / tfvars.

Optional extra shells (no Terraform versions): set `provision_anthropic_secret_shell = true` or `provision_otlp_headers_secret_shell = true`.

Phased apply:

1. **First apply:** set `deploy_cloud_run_service = false` so Cloud Run is not created yet.

   ```bash
   terraform apply \
     -var="project_id=YOUR_PROJECT" \
     -var="manage_secret_versions_in_terraform=false" \
     -var="deploy_cloud_run_service=false"
   ```

2. **Add every required version in GCP** — at minimum the three core secrets. Use outputs (`terraform output secret_manager_database_url_id`, etc.)

   ```bash
   printf '%s' 'postgresql+psycopg://...' | gcloud secrets versions add issue-tracker-database-url --project=YOUR_PROJECT --data-file=-
   # repeat for trello-api-key and trello-api-secret
   ```

3. **Second apply:** enable Cloud Run (image must already exist in Artifact Registry):

   ```bash
   terraform apply \
     -var="project_id=YOUR_PROJECT" \
     -var="manage_secret_versions_in_terraform=false" \
     -var="deploy_cloud_run_service=true"
   ```

If Cloud Run references `ANTHROPIC` or `OTLP_HEADERS` envs, allocate shells with the `provision_*` flags **before** step 2 and add those versions too—otherwise omit the flags and those env blocks are not mounted.

---

## Mode B — Terraform seeds first versions (then GCP owns rotation)

1. **First successful `terraform apply`** with `manage_secret_versions_in_terraform = true` still supplies `database_url` / Trello once (`TF_VAR_*` or ephemeral tfvars from your machine)—Terraform writes initial **versions**.
2. After that, **`ignore_changes` on `secret_data`** means **rotations stay in GCP**; Terraform will not overwrite payload text on later applies (unless you `-replace` the version resource).
3. To **force** Terraform to rewrite a payload from vars again:  
   `terraform apply -replace='google_secret_manager_secret_version.database_url[0]'` (and similar for `[0]` counted trello versions).

**Stable secret ids** (default prefix `issue-tracker`):

| Variable / purpose             | Secret id (default naming)                         |
|-------------------------------|----------------------------------------------------|
| `DATABASE_URL`                | `{prefix}-database-url`                            |
| `TRELLO_API_KEY`             | `{prefix}-trello-api-key`                           |
| `TRELLO_API_SECRET`           | `{prefix}-trello-api-secret`                       |
| `ANTHROPIC_API_KEY`           | `{prefix}-anthropic-api-key` (if configured)       |
| `OTEL_EXPORTER_OTLP_HEADERS`  | `{prefix}-otlp-headers` (if configured)          |

Outputs `secret_manager_*_id` expose the exact ids for copy/paste after apply.

### Rotate via `gcloud` (example: database URL)

```bash
PROJECT=issue-tracker-495500
printf '%s' 'postgresql+psycopg://...' \
  | gcloud secrets versions add issue-tracker-database-url --project="$PROJECT" --data-file=-
```

Then **redeploy** Cloud Run so new revisions resolve `latest`, or rely on your rollout policy.

---

## Supplying values to Terraform

**Mode A (GCP-only payloads):** pass **`project_id`**, **`region`**, image knobs, **`manage_secret_versions_in_terraform = false`**, and phased **`deploy_cloud_run_service`** only.

**Mode B:** pass masked **`TF_VAR_database_url`**, **`TF_VAR_trello_api_key`**, **`TF_VAR_trello_api_secret`** (plus optional OTLP / Anthropic) or a **temporary gitignored** `secrets.tfvars` from `terraform.tfvars.example`.

---

## Prerequisite: image in Artifact Registry

Cloud Run needs a pullable digest. Either local Docker Desktop or Cloud Build; host:

`REGION-docker.pkg.dev/PROJECT/issue-tracker/issue-tracker-service:TAG`.

If **push** fails with “repository not found”, enable **Artifact Registry** and create repo `issue-tracker` (`gcloud artifacts repositories create …`) or rely on Terraform to create it, then push after the repo exists.

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth configure-docker "${REGION}-docker.pkg.dev"

cd /path/to/ospsd-team-07
IMAGE="${REGION}-docker.pkg.dev/YOUR_PROJECT_ID/issue-tracker/issue-tracker-service:latest"
docker build -t "$IMAGE" .   # or: gcloud builds submit --tag "$IMAGE" .

docker push "$IMAGE"
```

Then:

```bash
cd infrastructure/terraform
terraform init -backend=false
# omit -backend=false when using GCS: add -backend-config="bucket=BUCKET" -backend-config="prefix=PREFIX"
terraform apply   # follow Mode A or B inputs above
```

Optional `trello_callback_url`: leave blank until first revision; run `terraform output trello_callback_hint`, set via `TF_VAR_` / tfvars, apply again.

### Extension env vars (plain + Secret Manager)

Without editing `main.tf`, you can add:

| Variable | Purpose |
| -------- | ------- |
| **`cloud_run_plain_environment_variables`** | `map(string)` — plaintext env (e.g. `CORS_ALLOW_ORIGINS`). Merged first; built-in keys override duplicates in this map. |
| **`cloud_run_secret_environment_variables`** | `map(string)` — env name → **Secret Manager secret id** (short id, e.g. `issue-tracker-foo`). Secret **resources** must already exist in the project (create in Console or `gcloud`); Terraform adds **`secretAccessor`** for the Cloud Run runtime SA on each listed id and mounts `version = latest`. |

Do not use the same env var name twice across built-ins, the plain map, and the secret map (Terraform will reject duplicate keys in the secret `for_each` map).

**Example (`terraform.tfvars`):**

```hcl
cloud_run_plain_environment_variables = {
  CORS_ALLOW_ORIGINS = "https://my-app.vercel.app"
}

cloud_run_secret_environment_variables = {
  STRIPE_WEBHOOK_SECRET = "issue-tracker-stripe-webhook"
}
```

Add the secret payload in GCP (`gcloud secrets versions add ...`) before the new revision can start.

### OpenTelemetry → Grafana (plain URL + secret headers, Mode A)

| Kind | Terraform / where |
|------|-------------------|
| **Plain** | `otel_exporter_otlp_endpoint` — sets `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` on Cloud Run. Safe in `terraform.tfvars`. |
| **Secret shell** | `provision_otlp_headers_secret_shell = true` — Terraform creates the `{prefix}-otlp-headers` **secret resource** and IAM; it does **not** put your Grafana credentials in state. |
| **Mount on Cloud Run** | Set **`otlp_headers_secret_version`** to the Secret Manager **version number** (e.g. `"1"`) **after** you add the payload in GCP. Leave **`""`** until then — Terraform will **not** mount `OTEL_EXPORTER_OTLP_HEADERS` until this is set, so deploys do not reference a missing `latest`. Mode B still uses Terraform-managed versions and `"latest"`. |

**Typical flow (Mode A):**

1. `terraform apply` — secret `issue-tracker-otlp-headers` exists; Cloud Run has no OTLP headers env yet if `otlp_headers_secret_version` is empty.
2. Add the header line in GCP (never in git):

   ```bash
   PROJECT=your-project-id
   printf '%s' 'Authorization=Basic YOUR_BASE64_HERE' \
     | gcloud secrets versions add issue-tracker-otlp-headers --project="$PROJECT" --data-file=-
   ```

3. Note the new version id (often `1`) from Console or `gcloud secrets versions list`.
4. Set `otlp_headers_secret_version = "1"` in `terraform.tfvars` and **`terraform apply`** again so Cloud Run mounts that version.

After you rotate the secret with a **new** version, bump `otlp_headers_secret_version` (or switch to the new id) and apply.

---

## Subsequent deploys

**Application (routine):** merge to **`main`** / **`hw3`** with **`deploy_gcp`** enabled — CircleCI runs **`gcloud builds submit`**, then **`gcloud run services update`** so Cloud Run serves the new **immutable git-SHA** image tag. No Terraform required for each release.

**Infrastructure (occasional):** when you change **`main.tf`**, variables, IAM, secrets wiring, etc., run **`terraform apply`** from a machine with the right **`-backend-config`** and vars (same Mode A / B conventions as above). The Cloud Run resource uses **`lifecycle.ignore_changes`** on the container **image** so Terraform does not revert **CircleCI** image rollouts.

Under **Mode B**, rotated payloads can drift from stale tfvars because of `ignore_changes`. **Mode A** keeps credentials out of Terraform entirely.

### CircleCI — app deploy only (no Terraform in CI)

**Goal.** Each merge to **`main`** / **`hw3`** runs lint/tests, then **`deploy_gcp`** builds/pushes the image and **`gcloud run services update`** rolls Cloud Run. **Terraform is never executed in CircleCI**; run **`terraform plan`/`apply`** from a trusted machine when infrastructure changes.

**Prerequisite.** The Cloud Run service and Artifact Registry repo already exist (**initial `terraform apply`** from a laptop, or equivalent).

**1 — Create a CI service account.**

```bash
export PROJECT_ID=your-project-id
gcloud iam service-accounts create circleci-gcp-deploy \
  --project="$PROJECT_ID" --display-name="CircleCI GCP deploy"
export CI_SA="circleci-gcp-deploy@${PROJECT_ID}.iam.gserviceaccount.com"
```

**2 — Grant IAM (app deploy).**  
The SA must be able to **submit Cloud Build**, **push/read Artifact Registry**, and **update Cloud Run**. **`roles/editor`** is the blunt option for class projects:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CI_SA}" --role="roles/editor"
```

Tighter setups: combine **`roles/cloudbuild.builds.editor`**, **`roles/artifactregistry.writer`**, **`roles/run.developer`**, and whatever Cloud Build’s service account needs for your project’s default bucket.

**3 — Download a JSON key, base64 for CircleCI.**

```bash
gcloud iam service-accounts keys create ci-gcp-deploy.json \
  --project="$PROJECT_ID" --iam-account="$CI_SA"
base64 -w0 ci-gcp-deploy.json > ci-gcp-deploy.b64.txt   # macOS: base64 < ci-gcp-deploy.json | tr -d '\n' > …
rm ci-gcp-deploy.json
```

**4 — CircleCI environment variables.**

| Variable | Purpose |
|-----------|---------|
| **`GCP_CI_DEPLOY`**=`1` | Enables **`deploy_gcp`**. |
| **`GCP_PROJECT_ID`** | GCP project id (same as Terraform **`project_id`**). |
| **`GCP_SA_KEY_JSON_B64`** | Base64-encoded CI service account JSON (**masked** in CircleCI). |
| **`GCP_CLOUD_RUN_SERVICE_NAME`** (optional) | Default **`issue-tracker-service`** — must match Terraform **`cloud_run_service_name`**. |
| **`GCP_REGION`** (optional) | Default **`us-central1`**. |
| **`GCP_ARTIFACT_REPOSITORY_ID`** (optional) | Default **`issue-tracker`**. |
| **`GCP_CLOUD_RUN_IMAGE_NAME`** (optional) | Default **`issue-tracker-service`**. |

**5 — Merge.**  
Inspect logs for Cloud Build and **`gcloud run services update`**.

---

### Terraform remote state (laptop / infra pipeline only)

Terraform **never runs in CircleCI**. For team-shared state, create a GCS bucket and **migrate once** from the machine that owns **`terraform.tfstate`**:

```bash
export TF_BUCKET="${PROJECT_ID}-tf-state"
export TF_REGION=us-central1
gsutil mb -p "$PROJECT_ID" -l "$TF_REGION" "gs://${TF_BUCKET}" || true

cd infrastructure/terraform
terraform init \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="prefix=ospsd-team-07/terraform" \
  -migrate-state \
  -input=false
```

After migrate, run **`terraform apply`** only when you change **`infrastructure/terraform/**`** or need to reconcile infra — not on every app merge.

**Backend.** Terraform declares **`backend "gcs" {}`**. **`validate_infra`** in CircleCI uses **`terraform init -backend=false`** (fmt/validate only; no GCP credentials required for that job).

---

## Troubleshooting

### `cannot destroy service without setting deletion_protection=false` (tainted replace)

A **tainted** Cloud Run service triggers **destroy → create**. GCP still has **deletion protection on the old service**, so destroy runs **before** Terraform can attach the new `deletion_protection = false` definition.

1. **Prefer:** clear the taint so the next apply is an **in-place update** (PATCH) that turns deletion protection off:

   ```bash
   terraform untaint 'google_cloud_run_v2_service.issue_tracker[0]'
   terraform apply \
     -var="project_id=YOUR_PROJECT" \
     -var="manage_secret_versions_in_terraform=false" \
     -var="deploy_cloud_run_service=true"
   ```

   After the service is healthy, avoid unnecessary `-replace`; keep `cloud_run_deletion_protection = false` in config for dev/class projects.

2. **Or:** in [Cloud Console](https://console.cloud.google.com/run) → your service → **Edit** → **Security** → turn **Deletion protection** off → save → run `terraform apply` again.

3. Only **after** protection is off in GCP should you intentionally use **`terraform apply -replace='google_cloud_run_v2_service.issue_tracker[0]'`**.

### `Image '...PKG.../issue-tracker/issue-tracker-service:latest' not found`

Terraform pointed Cloud Run at a tag that **has never been pushed** (or wrong project/repo/name). Push from **this repo root** (`Dockerfile` lives there), matching `region`, `artifact_repository_id`, `image_name`, and `image_tag`:

```bash
REGION=us-central1   # same as Terraform var.region
gcloud config set project YOUR_PROJECT_ID

cd /path/to/ospsd-team-07
IMAGE="${REGION}-docker.pkg.dev/YOUR_PROJECT_ID/issue-tracker/issue-tracker-service:latest"
gcloud builds submit --tag "$IMAGE" .
```

Then `terraform apply` again. See **Prerequisite: image in Artifact Registry** above for local `docker build` / `docker push`.

### `Secret ... secrets/issue-tracker-.../versions/latest was not found`

With **`manage_secret_versions_in_terraform = false`**, Terraform only creates **secret names** (and IAM). Cloud Run binds `version = latest`; if **no version** has ever been enabled, the revision stays `not ready`.

Add at least one version for **each** secret the service mounts (defaults with `secret_name_prefix = "issue-tracker"`):

```bash
PROJECT=YOUR_PROJECT_ID

printf '%s' 'YOUR_POSTGRES_SQLALCHEMY_URL' \
  | gcloud secrets versions add issue-tracker-database-url --project="$PROJECT" --data-file=-
printf '%s' 'YOUR_TRELLO_API_KEY' \
  | gcloud secrets versions add issue-tracker-trello-api-key --project="$PROJECT" --data-file=-
printf '%s' 'YOUR_TRELLO_API_SECRET' \
  | gcloud secrets versions add issue-tracker-trello-api-secret --project="$PROJECT" --data-file=-
```

Or use [Secret Manager](https://console.cloud.google.com/security/secret-manager) → each secret → **New version**. Then run **`terraform apply`** again (or deploy a new revision) so Cloud Run picks up `latest`.

Phased bootstrap is in **Mode A** above (`deploy_cloud_run_service = false` until versions exist).

**Still seeing `versions/latest was not found` after “adding values”?**

1. **Wrong project.** Cloud Run resolves secrets in **`issue-tracker-495500`** (error shows numeric id `projects/688420327904/` — verify with `gcloud projects describe issue-tracker-495500 --format='value(projectNumber)'`). If `gcloud`’s core project differs, **`gcloud secrets versions add`** without `--project=` wrote versions somewhere else.

   ```bash
   PROJECT=issue-tracker-495500   # same as terraform -var project_id
   for s in issue-tracker-database-url issue-tracker-trello-api-key issue-tracker-trello-api-secret; do
     echo "--- $s"
     gcloud secrets versions list "$s" --project="$PROJECT" --limit=5
   done
   ```

   Expect at least one row with **`STATE` = enabled**. Empty output means no versions in **this** project (add them again with `--project="$PROJECT"`).

2. **Verify `latest` is readable:**

   ```bash
   PROJECT=issue-tracker-495500
   gcloud secrets versions access latest --secret=issue-tracker-database-url --project="$PROJECT"
   ```

   If access fails here, Cloud Run cannot resolve `latest` either.

3. **Console selector:** Confirm the project dropdown is **`issue-tracker-495500`**, not a personal/other project whose Secret Manager lists similarly named secrets.

---

## Rollback

Cloud Console revisions or `gcloud run services update-traffic`. Alembic downgrades stay manual against Postgres (`alembic downgrade`).
