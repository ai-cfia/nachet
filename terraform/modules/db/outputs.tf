output "postgresql_server_fqdn" {
  value = azurerm_postgresql_flexible_server.nachet.fqdn
}

output "postgresql_server_id" {
  value = azurerm_postgresql_flexible_server.nachet.id
}

output "nachet_database_name" {
  value = azurerm_postgresql_flexible_server_database.nachet.name
}

output "nachet_connection_string" {
  value     = "postgresql://${var.postgresql_admin_username}:${var.postgresql_admin_password}@${azurerm_postgresql_flexible_server.nachet.fqdn}:5432/nachet_db?sslmode=require"
  sensitive = true
}
