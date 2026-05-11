locals {
  manage_tf = var.manage_secret_versions_in_terraform

  image_digest = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repository_id}/${var.image_name}:${var.image_tag}"

  use_anthropic = local.manage_tf ? (trimspace(var.anthropic_api_key) != "") : var.provision_anthropic_secret_shell

  use_otlp_headers = local.manage_tf ? (trimspace(var.otel_exporter_otlp_headers) != "") : var.provision_otlp_headers_secret_shell

  version_database = local.manage_tf ? 1 : 0
  version_trello   = local.manage_tf ? 1 : 0

  version_anthropic = (local.manage_tf && local.use_anthropic) ? 1 : 0

  version_otlp = (local.manage_tf && local.use_otlp_headers) ? 1 : 0

  plain_env_pairs = merge(
    {
      OTEL_SERVICE_NAME  = var.otel_service_name
      OTEL_SDK_DISABLED  = "false"
      AI_ALLOW_MUTATIONS = var.ai_allow_mutations ? "true" : "false"
      SKIP_ALEMBIC       = var.skip_alembic ? "true" : "false"
    },
    var.otel_exporter_otlp_endpoint != "" ? {
      OTEL_EXPORTER_OTLP_ENDPOINT = var.otel_exporter_otlp_endpoint
      OTEL_EXPORTER_OTLP_PROTOCOL = "http/protobuf"
    } : {},
    trimspace(var.trello_callback_url) != "" ? {
      TRELLO_CALLBACK_URL = trimspace(var.trello_callback_url)
    } : {},
  )

  secret_env_bindings = concat(
    [
      { name = "DATABASE_URL", secret = "${var.secret_name_prefix}-database-url" },
      { name = "TRELLO_API_KEY", secret = "${var.secret_name_prefix}-trello-api-key" },
      { name = "TRELLO_API_SECRET", secret = "${var.secret_name_prefix}-trello-api-secret" },
    ],
    local.use_anthropic ? [{
      name   = "ANTHROPIC_API_KEY"
      secret = "${var.secret_name_prefix}-anthropic-api-key"
    }] : [],
    local.use_otlp_headers ? [{
      name   = "OTEL_EXPORTER_OTLP_HEADERS"
      secret = "${var.secret_name_prefix}-otlp-headers"
    }] : [],
  )

  # Static secret ids (same strings as google_secret_manager_secret.*.secret_id) so for_each is
  # known during import/refresh. Optional entries use nonsensitive(length(...)) in Mode B so the
  # set keys are not marked sensitive.
  _accessor_include_anthropic = (
    var.manage_secret_versions_in_terraform
    ? nonsensitive(length(trimspace(var.anthropic_api_key)) > 0)
    : var.provision_anthropic_secret_shell
  )
  _accessor_include_otlp = (
    var.manage_secret_versions_in_terraform
    ? nonsensitive(length(trimspace(var.otel_exporter_otlp_headers)) > 0)
    : var.provision_otlp_headers_secret_shell
  )

  accessor_secret_ids = toset(concat(
    [
      "${var.secret_name_prefix}-database-url",
      "${var.secret_name_prefix}-trello-api-key",
      "${var.secret_name_prefix}-trello-api-secret",
    ],
    local._accessor_include_anthropic ? ["${var.secret_name_prefix}-anthropic-api-key"] : [],
    local._accessor_include_otlp ? ["${var.secret_name_prefix}-otlp-headers"] : [],
  ))
}

locals {
  enable_apis = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
  ]
}

resource "google_project_service" "enabled" {
  for_each = toset(local.enable_apis)

  project                    = var.project_id
  service                    = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_service_account" "issue_tracker" {
  account_id   = "issue-tracker-run"
  display_name = "Issue tracker Cloud Run"
  depends_on   = [google_project_service.enabled]
}

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_repository_id
  description   = "Issue tracker Docker images"
  format        = "DOCKER"
  depends_on    = [google_project_service.enabled]
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "${var.secret_name_prefix}-database-url"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "database_url" {
  count = local.version_database

  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "trello_api_key" {
  secret_id = "${var.secret_name_prefix}-trello-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "trello_api_key" {
  count = local.version_trello

  secret      = google_secret_manager_secret.trello_api_key.id
  secret_data = var.trello_api_key

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "trello_api_secret" {
  secret_id = "${var.secret_name_prefix}-trello-api-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "trello_api_secret" {
  count = local.version_trello

  secret      = google_secret_manager_secret.trello_api_secret.id
  secret_data = var.trello_api_secret

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "anthropic" {
  count     = local.use_anthropic ? 1 : 0
  secret_id = "${var.secret_name_prefix}-anthropic-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "anthropic" {
  count = local.version_anthropic

  secret      = google_secret_manager_secret.anthropic[count.index].id
  secret_data = var.anthropic_api_key

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "otlp_headers" {
  count     = local.use_otlp_headers ? 1 : 0
  secret_id = "${var.secret_name_prefix}-otlp-headers"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "otlp_headers" {
  count = local.version_otlp

  secret      = google_secret_manager_secret.otlp_headers[count.index].id
  secret_data = var.otel_exporter_otlp_headers

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret_iam_member" "run_accessor" {
  for_each = local.accessor_secret_ids

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.issue_tracker.email}"
}

resource "google_cloud_run_v2_service" "issue_tracker" {
  count = var.deploy_cloud_run_service ? 1 : 0

  name                = var.cloud_run_service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = var.cloud_run_deletion_protection

  template {
    service_account                  = google_service_account.issue_tracker.email
    timeout                          = "600s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = local.image_digest

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        failure_threshold     = 12
        initial_delay_seconds = 15
        period_seconds        = 10
        timeout_seconds       = 3

        http_get {
          path = "/health"
          port = 8080
        }
      }

      dynamic "env" {
        for_each = local.plain_env_pairs
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = { for b in local.secret_env_bindings : b.name => b.secret }
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_artifact_registry_repository.docker,
    google_secret_manager_secret_iam_member.run_accessor,
  ]

  # App releases update the container image via CI (`gcloud run services update`).
  # Terraform continues to own the rest of the service definition without reverting the image.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.deploy_cloud_run_service ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.issue_tracker[0].location
  name     = google_cloud_run_v2_service.issue_tracker[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"

  depends_on = [google_cloud_run_v2_service.issue_tracker]
}
