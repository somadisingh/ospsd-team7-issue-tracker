#!/usr/bin/env bash
#
# GCP app deploy from CircleCI only (no Terraform). Infra is applied from your laptop.
#
# CircleCI env (Project Settings → Environment Variables):
#   GCP_CI_DEPLOY=1                               — enable (otherwise exits 0)
#   GCP_SA_KEY_JSON_B64                           — base64(service account JSON)
#   GCP_PROJECT_ID                                — e.g. issue-tracker-495500
# Optional:
#   GCP_REGION (default us-central1)
#   GCP_ARTIFACT_REPOSITORY_ID (default issue-tracker)
#   GCP_CLOUD_RUN_IMAGE_NAME (default issue-tracker-service)
#   GCP_CLOUD_RUN_SERVICE_NAME (default issue-tracker-service) — must match Terraform cloud_run_service_name
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
CLOUD_RUN_SERVICE="${GCP_CLOUD_RUN_SERVICE_NAME:-issue-tracker-service}"
SHORT_SHA="$(echo "${CIRCLE_SHA1}" | cut -c1-12)"
BASE_URI="${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/${IMAGE_NAME}"

key_dir="$(mktemp -d)"
cleanup() {
  rm -rf "${key_dir:?}"
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

# Cloud Build often ends up with only :latest in the registry when multiple
# --tag flags are used; rollouts use the immutable :SHORT_SHA tag.
if ! gcloud artifacts docker images describe "${BASE_URI}:${SHORT_SHA}" --quiet >/dev/null 2>&1; then
  echo "Tag ${SHORT_SHA} missing after build; aliasing from :latest digest"
  src_ref="$(
    gcloud artifacts docker images describe "${BASE_URI}:latest" \
      --format='value(image_summary.fully_qualified_digest)' 2>/dev/null || true
  )"
  if [[ -z "${src_ref}" ]]; then
    dig="$(
      gcloud artifacts docker images describe "${BASE_URI}:latest" \
        --format='value(image_summary.digest)' 2>/dev/null || true
    )"
    if [[ -n "${dig}" ]]; then
      src_ref="${BASE_URI}@${dig}"
    fi
  fi
  if [[ -z "${src_ref}" ]]; then
    echo "Could not resolve digest for ${BASE_URI}:latest (need image_summary from gcloud describe)"
    exit 1
  fi
  gcloud artifacts docker tags add "${src_ref}" "${BASE_URI}:${SHORT_SHA}"
fi

echo "App deploy: updating Cloud Run service \"${CLOUD_RUN_SERVICE}\" to ${BASE_URI}:${SHORT_SHA}"
gcloud run services update "${CLOUD_RUN_SERVICE}" \
  --region="${REGION}" \
  --image="${BASE_URI}:${SHORT_SHA}" \
  --quiet

echo "Done. Apply Terraform from your laptop when infrastructure (not app image) changes."
