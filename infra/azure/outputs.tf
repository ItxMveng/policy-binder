output "api_url" {
  description = "URL publique de l'API (VITE_API_URL du front)."
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "azure_client_id" {
  description = "À enregistrer comme variable GitHub AZURE_CLIENT_ID (identifiant, pas un secret)."
  value       = azuread_application.github.client_id
}

output "azure_tenant_id" {
  description = "À enregistrer comme variable GitHub AZURE_TENANT_ID."
  value       = data.azurerm_client_config.current.tenant_id
}
