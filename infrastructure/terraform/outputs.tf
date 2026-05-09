locals {
  # Cloud Run can return multiple URL hostnames for the same service (e.g. *.region.run.app and *.a.run.app).
  issue_tracker_urls = (
    length(google_cloud_run_v2_service.issue_tracker) > 0
    ? google_cloud_run_v2_service.issue_tracker[0].urls
    : []
  )
  issue_tracker_primary_url = (
    length(local.issue_tracker_urls) == 0 ? null :
    length([for u in local.issue_tracker_urls : u if endswith(u, ".${var.region}.run.app")]) > 0
    ? [for u in local.issue_tracker_urls : u if endswith(u, ".${var.region}.run.app")][0]
    : element(sort(local.issue_tracker_urls), 0)
  )
}

output "service_url" {
  description = "Live HTTPS URL for the Cloud Run service (null while Cloud Run resource is omitted)."
  value       = local.issue_tracker_primary_url
}

output "trello_callback_hint" {
  description = "Set trello_callback_url to this value (then terraform apply again) after the first revision is live."
  value = (
    local.issue_tracker_primary_url != null ? "${local.issue_tracker_primary_url}/auth/callback" : ""
  )
}

output "artifact_registry_repository" {
  description = "Artifact Registry Docker repository path (project/location/repo)."
  value       = google_artifact_registry_repository.docker.name
}

output "artifact_image_base" {
  description = "Repository base for docker tag (without trailing tag)."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repository_id}/${var.image_name}"
}

output "secret_manager_database_url_id" {
  description = "Secret Manager id for DATABASE_URL payloads."
  value       = google_secret_manager_secret.database_url.secret_id
}

output "secret_manager_trello_api_key_id" {
  description = "Secret Manager id for TRELLO_API_KEY payloads."
  value       = google_secret_manager_secret.trello_api_key.secret_id
}

output "secret_manager_trello_api_secret_id" {
  description = "Secret Manager id for TRELLO_API_SECRET payloads."
  value       = google_secret_manager_secret.trello_api_secret.secret_id
}
