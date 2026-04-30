output "web_service_id" {
  description = "Render web service ID."
  value       = render_web_service.issue_tracker_service.id
}

output "web_service_url" {
  description = "Render web service URL."
  value       = render_web_service.issue_tracker_service.url
}

output "database_id" {
  description = "Render Postgres ID."
  value       = render_postgres.issue_tracker_db.id
}

output "database_internal_connection_string" {
  description = "Internal connection string for the Render database."
  value       = render_postgres.issue_tracker_db.connection_info.internal_connection_string
  sensitive   = true
}
