# Resource Group for Database
resource "azurerm_resource_group" "db" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# Get the existing VNet (assume it's in a different/shared RG)
data "azurerm_virtual_network" "existing" {
  name                = var.vnet_name
  resource_group_name = var.vnet_resource_group_name
}

# Get existing Route Table
data "azurerm_route_table" "existing" {
  name                = var.route_table_name
  resource_group_name = var.route_table_resource_group_name
}

# Subnet for PostgreSQL (must be in same RG as VNet)
resource "azurerm_subnet" "postgresql" {
  name                 = "${var.project_name}-postgresql-subnet-${var.environment}"
  resource_group_name  = var.vnet_resource_group_name  # Same RG as VNet
  virtual_network_name = data.azurerm_virtual_network.existing.name
  address_prefixes     = [var.postgresql_subnet_cidr]

  service_endpoints = ["Microsoft.Storage"]

  delegation {
    name = "fs"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Associate existing Route Table with Subnet
resource "azurerm_subnet_route_table_association" "postgresql" {
  subnet_id      = azurerm_subnet.postgresql.id
  route_table_id = data.azurerm_route_table.existing.id
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

  delegated_subnet_id = azurerm_subnet.postgresql.id
  public_network_access_enabled = false

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
