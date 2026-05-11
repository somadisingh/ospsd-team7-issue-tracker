#!/usr/bin/env bash
#
# GCP deploy from CircleCI: Cloud Build push + optional Terraform apply.
#
# CircleCI env (Project Settings → Environment Variables):
#   GCP_CI_DEPLOY=1                               — enable (otherwise exits 0)
#   GCP_SA_KEY_JSON_B64                           — base64(service account JSON)
#   GCP_PROJECT_ID                                — e.g. issue-tracker-495500
# Optional:
#   GCP_REGION (default us-central1)
#   GCP_ARTIFACT_REPOSITORY_ID (default issue-tracker)
#   GCP_CLOUD_RUN_IMAGE_NAME (default issue-tracker-service)
#   GCP_TERRAFORM_STATE_BUCKET                    — enables terraform apply via GCS backend
#   GCP_TERRAFORM_STATE_PREFIX (default ospsd-team-07/terraform)
#   TRELLO_CALLBACK_URL                           — terraform -var when non-empty (Mode A)
#
set -euo pipefail

if [[ "${GCP_CI_DEPLOY:-}" != "1" ]]; then
  echo "GCP_CI_DEPLOY is not set to 1; skipping GCP deploy."
  exit 0
fi

if [[ -z "${GCP_SA_KEY_JSON_B64:-}" ]]; then
  echo "GCP_SA_KEY_JSON_B64 must be set (base64-encoded service account JSON key)."
  exit 1
fi

if [[ -z "${GCP_PROJECT_ID:-}" ]]; then
  echo "GCP_PROJECT_ID must be set."
  exit 1
fi

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT_DIR}"

REGION="${GCP_REGION:-us-central1}"
REPO="${GCP_ARTIFACT_REPOSITORY_ID:-issue-tracker}"
IMAGE_NAME="${GCP_CLOUD_RUN_IMAGE_NAME:-issue-tracker-service}"
SHORT_SHA="$(echo "${CIRCLE_SHA1}" | cut -c1-12)"
BASE_URI="${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/${IMAGE_NAME}"

key_dir="$(mktemp -d)"
tf_dl=""
cleanup() {
  rm -rf "${key_dir:?}"
  if [[ -n "${tf_dl}" ]]; then
    rm -rf "${tf_dl:?}"
  fi
}
trap cleanup EXIT

echo "${GCP_SA_KEY_JSON_B64}" | base64 -d >"${key_dir}/sa.json"
chmod 600 "${key_dir}/sa.json"

export GOOGLE_APPLICATION_CREDENTIALS="${key_dir}/sa.json"

gcloud auth activate-service-account --key-file="${GOOGLE_APPLICATION_CREDENTIALS}" --quiet
gcloud config set project "${GCP_PROJECT_ID}" --quiet
gcloud config set run/region "${REGION}" --quiet

echo "Building and pushing ${BASE_URI}:${SHORT_SHA} and :latest"
gcloud builds submit \
  --verbosity=warning \
  --tag="${BASE_URI}:${SHORT_SHA}" \
  --tag="${BASE_URI}:latest" \
  .

if [[ -z "${GCP_TERRAFORM_STATE_BUCKET:-}" ]]; then
  echo "GCP_TERRAFORM_STATE_BUCKET unset — skipping Terraform apply."
  echo "After migrating state to GCS, set the bucket variable to roll out new image tags automatically."
  exit 0
fi

PREFIX="${GCP_TERRAFORM_STATE_PREFIX:-ospsd-team-07/terraform}"

tf_dl="$(mktemp -d)"

TVER="${TERRAFORM_VERSION:-1.10.5}"
curl -sSfL -o "${tf_dl}/terraform.zip" \
  "https://releases.hashicorp.com/terraform/${TVER}/terraform_${TVER}_linux_amd64.zip"
unzip -oq "${tf_dl}/terraform.zip" -d "${tf_dl}"
chmod +x "${tf_dl}/terraform"
TF_BIN="${tf_dl}/terraform"

cd "${ROOT_DIR}/infrastructure/terraform"
${TF_BIN} init -upgrade -input=false \
  -backend-config="bucket=${GCP_TERRAFORM_STATE_BUCKET}" \
  -backend-config="prefix=${PREFIX}"

EXTRA_VARS=(
  "-var=project_id=${GCP_PROJECT_ID}"
  "-var=manage_secret_versions_in_terraform=false"
  "-var=deploy_cloud_run_service=true"
  "-var=image_tag=${SHORT_SHA}"
)

if [[ -n "${TRELLO_CALLBACK_URL:-}" ]]; then
  EXTRA_VARS+=("-var=trello_callback_url=${TRELLO_CALLBACK_URL}")
fi

${TF_BIN} plan -input=false -lock-timeout=5m "${EXTRA_VARS[@]}"
${TF_BIN} apply -auto-approve -input=false -lock-timeout=5m "${EXTRA_VARS[@]}"
