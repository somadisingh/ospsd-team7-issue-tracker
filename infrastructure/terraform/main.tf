locals {
  base_env_vars = {
    DATABASE_URL = {
      value = render_postgres.issue_tracker_db.connection_info.internal_connection_string
    }
    OTEL_SERVICE_NAME = {
      value = var.otel_service_name
    }
    TRELLO_CALLBACK_URL = {
      value = var.trello_callback_url
    }
    AI_ALLOW_MUTATIONS = {
      value = tostring(var.ai_allow_mutations)
    }
    OTEL_SDK_DISABLED = {
      value = tostring(var.otel_sdk_disabled)
    }
  }

  optional_env_vars = merge(
    var.trello_api_key != null ? { TRELLO_API_KEY = { value = var.trello_api_key } } : {},
    var.trello_api_secret != null ? { TRELLO_API_SECRET = { value = var.trello_api_secret } } : {},
    var.anthropic_api_key != null ? { ANTHROPIC_API_KEY = { value = var.anthropic_api_key } } : {},
    var.otel_exporter_otlp_endpoint != null ? { OTEL_EXPORTER_OTLP_ENDPOINT = { value = var.otel_exporter_otlp_endpoint } } : {},
    var.otel_exporter_otlp_headers != null ? { OTEL_EXPORTER_OTLP_HEADERS = { value = var.otel_exporter_otlp_headers } } : {}
  )
}

resource "render_postgres" "issue_tracker_db" {
  name         = var.database_name
  plan         = var.postgres_plan
  region       = var.region
  version      = var.postgres_version
  disk_size_gb = var.postgres_disk_size_gb
}

resource "render_web_service" "issue_tracker_service" {
  name              = var.service_name
  plan              = var.service_plan
  region            = var.region
  health_check_path = "/health"
  start_command     = "uv run uvicorn issue_tracker_service.main:app --host 0.0.0.0 --port $PORT"

  runtime_source = {
    native_runtime = {
      runtime       = "python"
      repo_url      = var.repo_url
      branch        = var.git_branch
      auto_deploy   = true
      build_command = "pip install uv && uv sync --all-extras"
    }
  }

  env_vars = merge(local.base_env_vars, local.optional_env_vars)
}
