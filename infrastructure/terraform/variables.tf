variable "service_name" {
  description = "Render web service name."
  type        = string
  default     = "issue-tracker-service"
}

variable "database_name" {
  description = "Render Postgres service name."
  type        = string
  default     = "issue-tracker-db"
}

variable "region" {
  description = "Render region."
  type        = string
  default     = "oregon"
}

variable "repo_url" {
  description = "Git repository URL for Render native runtime source."
  type        = string
  default     = "https://github.com/somaditya/ospsd-team-07"
}

variable "git_branch" {
  description = "Git branch Render deploys from."
  type        = string
  default     = "hw3"
}

variable "service_plan" {
  description = "Render plan for web service."
  type        = string
  default     = "starter"
}

variable "postgres_plan" {
  description = "Render plan for Postgres."
  type        = string
  default     = "basic_256mb"
}

variable "postgres_version" {
  description = "Postgres major version."
  type        = string
  default     = "16"
}

variable "postgres_disk_size_gb" {
  description = "Disk size for Render Postgres."
  type        = number
  default     = 10
}

variable "trello_callback_url" {
  description = "OAuth callback URL served by the web service."
  type        = string
  default     = "https://ospsd-team7-issue-tracker.onrender.com/auth/callback"
}

variable "otel_service_name" {
  description = "OpenTelemetry service.name."
  type        = string
  default     = "issue-tracker-service"
}

variable "ai_allow_mutations" {
  description = "Whether AI write operations are enabled."
  type        = bool
  default     = true
}

variable "otel_sdk_disabled" {
  description = "Disable OpenTelemetry SDK at runtime."
  type        = bool
  default     = false
}

variable "trello_api_key" {
  description = "Trello API key."
  type        = string
  sensitive   = true
  default     = null
  nullable    = true
}

variable "trello_api_secret" {
  description = "Trello API secret."
  type        = string
  sensitive   = true
  default     = null
  nullable    = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key."
  type        = string
  sensitive   = true
  default     = null
  nullable    = true
}

variable "otel_exporter_otlp_endpoint" {
  description = "OTLP endpoint URL for Grafana Cloud."
  type        = string
  sensitive   = true
  default     = null
  nullable    = true
}

variable "otel_exporter_otlp_headers" {
  description = "OTLP auth headers for Grafana Cloud."
  type        = string
  sensitive   = true
  default     = null
  nullable    = true
}
