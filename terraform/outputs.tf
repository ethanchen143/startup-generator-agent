output "service_url" {
  value       = google_cloud_run_v2_service.agent_service.uri
  description = "The public URL of the deployed multi-agent Cloud Run service"
}

output "google_api_key_secret_id" {
  value       = google_secret_manager_secret.google_api_key.id
  description = "Secret Manager Secret ID for GOOGLE_API_KEY"
}
