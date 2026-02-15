# Storage account and resource group outputs removed - managed externally

# Log Analytics workspace output removed - now managed in dev/main.tf

# Container App Environment outputs removed - now managed in dev/main.tf

output "nachet_app_name" {
  description = "Nachet Container App name"
  value       = azurerm_container_app.nachet.name
}

output "nachet_fqdn" {
  description = "Nachet Container App FQDN"
  value       = azurerm_container_app.nachet.latest_revision_fqdn
}

output "nachet_url" {
  description = "Nachet Container App URL"
  value       = "https://${azurerm_container_app.nachet.latest_revision_fqdn}"
}

output "nachet_app_url" {
  description = "Nachet application URL (restricted to allowed IPs)"
  value       = "https://${azurerm_container_app.nachet.latest_revision_fqdn}"
}
