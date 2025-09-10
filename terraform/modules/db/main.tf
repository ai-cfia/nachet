# Resource Group for Database
resource "azurerm_resource_group" "db" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

data "azurerm_virtual_network" "existing" {
  name                = var.vnet_name
  resource_group_name = var.vnet_resource_group_name
}

data "azurerm_subnet" "postgresql" {
  name                 = var.postgresql_subnet_name
  virtual_network_name = var.vnet_name
  resource_group_name  = var.vnet_resource_group_name
}

# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "nachet" {
  name                         = "${var.project_name}-psql-${var.environment}"
  resource_group_name          = azurerm_resource_group.db.name
  location                     = azurerm_resource_group.db.location
  version                      = var.postgresql_version
  administrator_login          = var.postgresql_admin_username
  administrator_password       = var.postgresql_admin_password
  zone                         = "1"
  storage_mb                   = var.postgresql_storage_mb
  storage_tier                 = "P4"
  sku_name                     = var.postgresql_sku_name
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  auto_grow_enabled            = false

  delegated_subnet_id           = data.azurerm_subnet.postgresql.id
  public_network_access_enabled = var.public_network_access_enabled

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
