# Terraform Infrastructure (Render)

This directory defines the deployment infrastructure for this project using the official Render Terraform provider.

## Managed resources

- `render_postgres.issue_tracker_db`
- `render_web_service.issue_tracker_service`

## Required environment variables for Terraform

- `RENDER_API_KEY`
- `RENDER_OWNER_ID`

## Optional TF variables (recommended via CI secrets)

- `TF_VAR_trello_api_key`
- `TF_VAR_trello_api_secret`
- `TF_VAR_anthropic_api_key`
- `TF_VAR_otel_exporter_otlp_endpoint`
- `TF_VAR_otel_exporter_otlp_headers`

## Usage

```bash
cd infrastructure/terraform
terraform init
terraform fmt -check
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

## CircleCI behavior (free Render-safe default)

- `terraform fmt/validate/plan` always run.
- `terraform apply` runs only when `TF_AUTO_APPLY=true`.
- Recommended default on free Render: keep `TF_AUTO_APPLY` unset, and run apply manually when you explicitly want infra changes.

## Notes

- `DATABASE_URL` is wired from the managed `render_postgres` resource to the web service.
- Application telemetry exports to Grafana Cloud when OTLP variables are supplied.
