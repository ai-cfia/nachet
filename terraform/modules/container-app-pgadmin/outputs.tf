output "pgadmin_url" {
  description = "Internal URL for PgAdmin (accessible from VNet only)"
  value       = "https://${azurerm_container_app.pgadmin.latest_revision_fqdn}"
}

output "pgadmin_container_app_name" {
  description = "PgAdmin Container App name"
  value       = azurerm_container_app.pgadmin.name
}
