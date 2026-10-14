output "api_url" {
  description = "URL publique de l'API (à donner au front dans VITE_API_URL)."
  value       = google_cloud_run_v2_service.api.uri
}
