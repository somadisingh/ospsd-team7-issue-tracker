variable "project_id" {
  description = "GCP project ID hosting Cloud Run and Secret Manager."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and Artifact Registry (e.g. us-central1)."
  type        = string
  default     = "us-central1"
}

variable "artifact_repository_id" {
  description = "Artifact Registry repository id (DOCKER format)."
  type        = string
  default     = "issue-tracker"
}

variable "image_name" {
  description = "Final path segment for the Artifact Registry Docker image."
  type        = string
  default     = "issue-tracker-service"
}

variable "image_tag" {
  description = "Image tag referenced by Cloud Run; bump or change after pushing a new digest."
  type        = string
  default     = "latest"
}

variable "cloud_run_service_name" {
  description = "Cloud Run service resource name."
  type        = string
  default     = "issue-tracker-service"
}

variable "secret_name_prefix" {
  description = "Prefix for Secret Manager secret ids inside this project."
  type        = string
  default     = "issue-tracker"
}

variable "manage_secret_versions_in_terraform" {
  description = <<-EOT
    When true, Terraform creates google_secret_manager_secret_version from database_url/trello/etc.
    When false, you add every payload with Console or `gcloud secrets versions add`; set deploy_cloud_run_service=false until versions exist (see README).
  EOT
  type        = bool
  default     = true
}

variable "deploy_cloud_run_service" {
  description = <<-EOT
    When false, Terraform skips the Cloud Run service (and public invoker) so you can add Secret Manager payloads first while manage_secret_versions_in_terraform=false.
  EOT
  type        = bool
  default     = true
}

variable "database_url" {
  description = "PostgreSQL SQLAlchemy URL — required only when manage_secret_versions_in_terraform is true."
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = !var.manage_secret_versions_in_terraform || length(trimspace(var.database_url)) > 0
    error_message = "database_url must be non-empty when manage_secret_versions_in_terraform is true."
  }
}

variable "trello_api_key" {
  description = "Trello API key — required only when manage_secret_versions_in_terraform is true."
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = !var.manage_secret_versions_in_terraform || length(trimspace(var.trello_api_key)) > 0
    error_message = "trello_api_key must be non-empty when manage_secret_versions_in_terraform is true."
  }
}

variable "trello_api_secret" {
  description = "Trello API secret — required only when manage_secret_versions_in_terraform is true."
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = !var.manage_secret_versions_in_terraform || length(trimspace(var.trello_api_secret)) > 0
    error_message = "trello_api_secret must be non-empty when manage_secret_versions_in_terraform is true."
  }
}

variable "trello_callback_url" {
  description = "HTTPS URL Trello redirects to after OAuth — must match Cloud Run hostname (often two applies: deploy once for URL, set this to `<service-url>/auth/callback`, apply again)."
  type        = string
  default     = ""
}

variable "cloud_run_plain_environment_variables" {
  description = <<-EOT
    Extra plaintext environment variables for the Cloud Run container (e.g. CORS_ALLOW_ORIGINS).
    Built-in keys (OTEL_*, AI_ALLOW_MUTATIONS, SKIP_ALEMBIC, TRELLO_CALLBACK_URL when set, etc.) win
    over duplicate keys in this map.
  EOT
  type        = map(string)
  default     = {}
}

variable "cloud_run_secret_environment_variables" {
  description = <<-EOT
    Map of env var name -> Secret Manager secret id (short id, e.g. issue-tracker-my-api-key).
    Secrets must already exist in the same GCP project. Terraform grants the Cloud Run runtime
    service account secretAccessor on each distinct secret id listed here (and on the core secrets).
  EOT
  type        = map(string)
  default     = {}
}

variable "anthropic_api_key" {
  description = "When manage_secret_versions_in_terraform is true and non-empty, creates secret + ANTHROPIC_API_KEY binding."
  type        = string
  sensitive   = true
  default     = ""
}

variable "provision_anthropic_secret_shell" {
  description = "When manage_secret_versions_in_terraform is false, set true to allocate the Anthropic secret shell (payload via GCP only)."
  type        = bool
  default     = false
}

variable "openai_api_key" {
  description = <<-EOT
    When manage_secret_versions_in_terraform is true and non-empty, creates secret + OPENAI_API_KEY binding
    (same as other AI keys).
    Mode A shell-only deployments use provision_openai_secret_shell + non-empty openai_api_key_secret_version after gcloud uploads the payload.
  EOT
  type        = string
  sensitive   = true
  default     = ""
}

variable "provision_openai_secret_shell" {
  description = "When manage_secret_versions_in_terraform is false, set true to allocate the OpenAI secret shell (payload via GCP only)."
  type        = bool
  default     = false
}

variable "openai_api_key_secret_version" {
  description = <<-EOT
    When manage_secret_versions_in_terraform is false: set non-empty Secret Manager version id after
    `gcloud secrets versions add …` so Cloud Run can mount OPENAI_API_KEY (GCP rejects referencing
    secrets with no versions). Use "latest" or a numeric id (e.g. "1"). Leave empty until a version exists.
    When manage_secret_versions_in_terraform is true with openai_api_key set, mounting uses "latest" and this variable is unused.
  EOT
  type        = string
  sensitive   = false
  default     = ""
}

variable "provision_otlp_headers_secret_shell" {
  description = "When manage_secret_versions_in_terraform is false, set true to allocate OTLP headers secret shell (payload via GCP only)."
  type        = bool
  default     = false
}

variable "otlp_headers_secret_version" {
  description = <<-EOT
    Secret Manager version id mounted as OTEL_EXPORTER_OTLP_HEADERS.
  EOT
  type        = string
  default     = ""
}

variable "otel_exporter_otlp_endpoint" {
  description = "If non-empty, set as plaintext OTEL_EXPORTER_OTLP_ENDPOINT on the revision."
  type        = string
  default     = ""
  sensitive   = false
}

variable "otel_exporter_otlp_headers" {
  description = "When manage_secret_versions_in_terraform is true and non-empty, creates OTLP headers secret binding."
  type        = string
  sensitive   = true
  default     = ""
}

variable "otel_service_name" {
  type    = string
  default = "issue-tracker-service"
}

variable "ai_allow_mutations" {
  description = "When true, sets AI_ALLOW_MUTATIONS=true in the runtime environment."
  type        = bool
  default     = true
}

variable "skip_alembic" {
  description = "Set SKIP_ALEMBIC=true in the container (not recommended for Postgres)."
  type        = bool
  default     = false
}

variable "cloud_run_deletion_protection" {
  description = "When true, Cloud Run blocks delete/replace until you set false and apply. Default false so Terraform can fix failed revisions (e.g. missing image → image push → replace)."
  type        = bool
  default     = false
}
