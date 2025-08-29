output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.nachet.name
}

output "postgresql_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = azurerm_postgresql_flexible_server.nachet.fqdn
}

output "backend_fqdn" {
  description = "Backend Container App FQDN"
  value       = azurerm_container_app.backend.latest_revision_fqdn
}

output "backend_url" {
  description = "Backend Container App URL"
  value       = "https://${azurerm_container_app.backend.latest_revision_fqdn}"
}


output "swin_classifier_fqdns" {
  description = "Swin Classifier Container Apps FQDNs"
  value = {
    swin_base   = azurerm_container_app.swin_classifier.latest_revision_fqdn
    swin_22_spp = azurerm_container_app.swin_22_spp.latest_revision_fqdn
    swin_27_spp = azurerm_container_app.swin_27_spp.latest_revision_fqdn
  }
}

output "container_app_environment_id" {
  description = "Container App Environment ID"
  value       = azurerm_container_app_environment.nachet.id
}

output "storage_account_name" {
  description = "Storage Account name"
  value       = azurerm_storage_account.nachet.name
}

output "storage_account_primary_key" {
  description = "Storage Account primary key"
  value       = azurerm_storage_account.nachet.primary_access_key
  sensitive   = true
}

output "storage_account_connection_string" {
  description = "Storage Account connection string"
  value       = azurerm_storage_account.nachet.primary_connection_string
  sensitive   = true
}

output "nachet_app_url" {
  description = "Nachet application URL (restricted to allowed IPs)"
  value       = var.enable_public_access ? "https://${azurerm_container_app.backend.latest_revision_fqdn}" : "Container App is private - no public URL"
}

output "nachet_app_fqdn" {
  description = "Nachet application FQDN"
  value       = azurerm_container_app.backend.latest_revision_fqdn
}

# Observability Stack Outputs
output "grafana_url" {
  description = "Grafana dashboard URL (restricted to your IP)"
  value       = var.enable_observability_stack && var.enable_public_access ? "https://${azurerm_container_app.grafana[0].latest_revision_fqdn}" : "Grafana not accessible or disabled"
}

output "alloy_dashboard_url" {
  description = "Alloy dashboard URL (restricted to your IP)"
  value       = var.enable_observability_stack && var.enable_public_access ? "http://${azurerm_container_app.alloy[0].latest_revision_fqdn}:12345" : "Alloy not accessible or disabled"
}

output "loki_endpoint" {
  description = "Loki logs endpoint (internal)"
  value       = var.enable_observability_stack ? "http://${azurerm_container_app.loki[0].name}:3100" : "Loki disabled"
}

output "observability_stack_enabled" {
  description = "Whether observability stack is enabled"
  value       = var.enable_observability_stack
}
