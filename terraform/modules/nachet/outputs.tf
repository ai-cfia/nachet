output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.nachet.name
}

output "resource_group_location" {
  description = "Resource group location"
  value       = azurerm_resource_group.nachet.location
}

output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.nachet.name
}

output "storage_account_primary_connection_string" {
  description = "Storage account primary connection string"
  value       = azurerm_storage_account.nachet.primary_connection_string
  sensitive   = true
}

output "storage_account_primary_access_key" {
  description = "Storage account primary access key"
  value       = azurerm_storage_account.nachet.primary_access_key
  sensitive   = true
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.nachet.id
}

output "container_app_environment_id" {
  description = "Container App Environment ID"
  value       = azurerm_container_app_environment.nachet.id
}

output "container_app_environment_default_domain" {
  description = "Container App Environment default domain"
  value       = azurerm_container_app_environment.nachet.default_domain
}

output "backend_app_name" {
  description = "Backend Container App name"
  value       = azurerm_container_app.backend.name
}

output "backend_fqdn" {
  description = "Backend Container App FQDN"
  value       = azurerm_container_app.backend.latest_revision_fqdn
}

output "backend_url" {
  description = "Backend Container App URL"
  value       = "https://${azurerm_container_app.backend.latest_revision_fqdn}"
}

output "nachet_app_url" {
  description = "Nachet application URL (restricted to allowed IPs)"
  value       = var.enable_public_access ? "https://${azurerm_container_app.backend.latest_revision_fqdn}" : "Container App is private - no public URL"
}
