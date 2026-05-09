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

1. **First successful `terraform apply`** with `manage_secret_versions_in_terraform = true` still supplies `database_url` / Trello once (CI `TF_VAR_*` or ephemeral tfvars)—Terraform writes initial **versions**.
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

---

## Subsequent deploys

1. Build and push a **new immutable tag**; set **`image_tag`** (or `:latest` with forced redeploy).
2. `terraform apply` with the same **`manage_secret_versions_in_terraform`** / **`deploy_cloud_run_service`** conventions plus any infra tweaks.

Under **Mode B**, rotated payloads can drift from stale tfvars because of `ignore_changes`. **Mode A** keeps credentials out of Terraform entirely.

### Automate deploys on `main` (step-by-step)

**Goal.** Each merge to **`main`** runs lint/tests, then **`gcloud builds submit`** pushes images, then (if configured) **`terraform apply`** points Cloud Run at the **immutable git-SHA tag**—no laptop for routine releases.

**Prerequisite.** You already have real GCP resources that match **`terraform.tfstate`** (you applied successfully at least once). Automation **reads that same truth** after you copy state into **GCS** (step 5). Do **not** point CI at an empty bucket before **`terraform init … -migrate-state`**.

**1 — Create a CI service account.**  
Separate from your login; revocable keys; least blast radius.

```bash
export PROJECT_ID=your-project-id
gcloud iam service-accounts create circleci-gcp-deploy \
  --project="$PROJECT_ID" --display-name="CircleCI GCP deploy"
export CI_SA="circleci-gcp-deploy@${PROJECT_ID}.iam.gserviceaccount.com"
```

**2 — Grant IAM.**  
**Class/simple:** **`roles/editor`** on the project (covers Cloud Build uploads, Artifact Registry, Run, Secrets metadata, IAM Terraform touches):

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CI_SA}" --role="roles/editor"
```

Stricter orgs: start with **`roles/cloudbuild.builds.editor`** + Terraform-oriented roles (**`roles/run.admin`**, AR reader, SA user, Secret Manager reader, etc.) and fix **`storage`/Cloud Build bucket 403s** like local troubleshooting.

**3 — Download a JSON key, base64 for CircleCI.**

```bash
gcloud iam service-accounts keys create ci-gcp-deploy.json \
  --project="$PROJECT_ID" --iam-account="$CI_SA"
base64 -w0 ci-gcp-deploy.json > ci-gcp-deploy.b64.txt   # macOS: base64 < ci-gcp-deploy.json | tr -d '\n' > …
rm ci-gcp-deploy.json   # keep only CircleCI secret + shred if paranoid
```

**4 — Create a Terraform state bucket (once).**  
Bucket name **globally unique** (example uses project id suffix):

```bash
export TF_BUCKET="${PROJECT_ID}-tf-state"
export TF_REGION=us-central1
gsutil mb -p "$PROJECT_ID" -l "$TF_REGION" "gs://${TF_BUCKET}" || true
```

Grant the CI SA **`roles/storage.admin`** **or** **Object Admin** on **only this bucket** if you did **not** use project **Editor**.

**5 — Migrate laptop state → GCS (once).**  
On the machine whose **`terraform.tfstate`** matches production:

```bash
cd infrastructure/terraform

terraform init \
  -backend-config="bucket=${TF_BUCKET}" \
  -backend-config="prefix=ospsd-team-07/terraform" \
  -migrate-state \
  -input=false

terraform plan \
  -input=false \
  -var="project_id=${PROJECT_ID}" \
  -var="manage_secret_versions_in_terraform=false" \
  -var="deploy_cloud_run_service=true"
# Expect no surprises; optional: terraform apply with same -var=
```

Use your real Mode A vars; **purpose** here is verifying shared state loads and **diff is empty-ish** before CI drives applies.

After migrate, collaborators run **`terraform init`** with the same **`-backend-config`** (omit **`-migrate-state`**) before any manual plan.

**6 — CircleCI environment variables.**

| Variable | Purpose |
|-----------|---------|
| **`GCP_CI_DEPLOY`**=`1` | Enables **`deploy_gcp`** (omit on forks/unused repos). |
| **`GCP_PROJECT_ID`** | Matches **`project_id`**. |
| **`GCP_SA_KEY_JSON_B64`** | Paste **`ci-gcp-deploy.b64.txt`** (**masked**, restricted context). |
| **`GCP_TERRAFORM_STATE_BUCKET`** | **`TF_BUCKET`** — enables **`terraform apply`** in CI; leave unset for **push-only** automation. |
| **`GCP_TERRAFORM_STATE_PREFIX`** | Defaults to **`ospsd-team-07/terraform`**; must match migrate **prefix**. |
| **`TRELLO_CALLBACK_URL`** (optional) | Stable OAuth callback **`https://<host>/auth/callback`** for recurring applies. |

**7 — Merge to `main`.**  
**`deploy_gcp`** filters **`main`** only and depends on **`validate_infra`**. Inspect logs for Cloud Build IDs and **`terraform apply`**.

---

### Circle CI — reference (`deploy_gcp` on `main`)

The **`deploy_gcp`** job builds from repo root (`gcloud builds submit`) and pushes **two tags**: `:latest` and **`:git_sha` truncated to 12 hex chars**.

| Variable | Meaning |
|-----------|---------|
| `GCP_CI_DEPLOY` | Set to **`1`** to enable the job path (unset or other value ⇒ job exits successfully without work). |
| `GCP_SA_KEY_JSON_B64` | **`base64` of the JSON key with no wrapping newlines** (e.g. `base64 -w0 < sa.json` on Linux). Store as a protected masked variable in CircleCI. |
| `GCP_PROJECT_ID` | e.g. `issue-tracker-495500`. |
| `GCP_TERRAFORM_STATE_BUCKET` | **Optional.** If unset, Circle CI pushes the image **only**. If set, **`terraform apply`** runs — **only after** you migrate existing state into this bucket with **`terraform init … -migrate-state`** once from a laptop; otherwise CI would start from an empty state and conflict with live resources. |
| `GCP_REGION` | Default `us-central1`. |
| `GCP_ARTIFACT_REPOSITORY_ID` | Default `issue-tracker`. |
| `GCP_CLOUD_RUN_IMAGE_NAME` | Default `issue-tracker-service`. |
| `GCP_TERRAFORM_STATE_PREFIX` | Default `ospsd-team-07/terraform`. |
| `TRELLO_CALLBACK_URL` | Optional terraform `-var`; set when OAuth callback is fixed after first revision. |

**Backend.** Terraform declares **`backend "gcs" {}`**. **`validate_infra`** uses **`terraform init -backend=false`** so CI need not authenticate to GCP for fmt/validate. Local-only edits without remote state:** **`terraform init -backend=false`**. Migrate and CircleCI buckets are covered in **Automate deploys on `main`** above.

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
