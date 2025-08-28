resource "azurerm_postgresql_flexible_server" "nachet" {
  name                          = "${var.project_name}-psql-${var.environment}"
  resource_group_name           = azurerm_resource_group.nachet.name
  location                      = azurerm_resource_group.nachet.location
  version                       = var.postgresql_version
  administrator_login           = var.postgresql_admin_username
  administrator_password        = var.postgresql_admin_password
  zone                          = "1"
  storage_mb                    = var.postgresql_storage_mb
  storage_tier                  = "P4"
  sku_name                      = var.postgresql_sku_name
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  auto_grow_enabled             = true
  public_network_access_enabled = true
  
  authentication {
    active_directory_auth_enabled = false
    password_auth_enabled         = true
  }
  
  tags = var.tags
}

resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.nachet.id
  value     = "PGCRYPTO,UUID-OSSP"
}

resource "azurerm_postgresql_flexible_server_database" "nachet" {
  name      = "nachet_db"
  server_id = azurerm_postgresql_flexible_server.nachet.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_postgresql_flexible_server_database" "fertiscan" {
  name      = "fertiscan_db"
  server_id = azurerm_postgresql_flexible_server.nachet.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.nachet.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
