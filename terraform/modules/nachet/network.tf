# Subnet for Container Apps Environment
resource "azurerm_subnet" "container_apps" {
  name                 = "${var.project_name}-container-apps-subnet-${var.environment}"
  resource_group_name  = azurerm_resource_group.nachet.name
  virtual_network_name = var.vnet_name
  address_prefixes     = [var.container_apps_subnet_cidr]

  # Container Apps requires delegation
  delegation {
    name = "container-apps-delegation"
    service_delegation {
      name = "Microsoft.App/environments"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Subnet for PostgreSQL Flexible Server
resource "azurerm_subnet" "postgresql" {
  name                 = "${var.project_name}-postgresql-subnet-${var.environment}"
  resource_group_name  = azurerm_resource_group.nachet.name
  virtual_network_name = var.vnet_name
  address_prefixes     = [var.postgresql_subnet_cidr]

  # PostgreSQL requires delegation
  delegation {
    name = "postgresql-delegation"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }

  service_endpoints = ["Microsoft.Storage"]
}

# Subnet for Storage Account Private Endpoints (optional)
resource "azurerm_subnet" "storage" {
  count                = var.storage_subnet_cidr != "" ? 1 : 0
  name                 = "${var.project_name}-storage-subnet-${var.environment}"
  resource_group_name  = azurerm_resource_group.nachet.name
  virtual_network_name = var.vnet_name
  address_prefixes     = [var.storage_subnet_cidr]

  # Enable private endpoints on this subnet
  private_endpoint_network_policies = "Disabled"
}

# No Application Gateway subnet needed - using direct Container Apps access

# Associate existing NSGs with subnets (optional)
resource "azurerm_subnet_network_security_group_association" "container_apps" {
  count                     = var.container_apps_nsg_id != "" ? 1 : 0
  subnet_id                 = azurerm_subnet.container_apps.id
  network_security_group_id = var.container_apps_nsg_id
}

resource "azurerm_subnet_network_security_group_association" "postgresql" {
  count                     = var.postgresql_nsg_id != "" ? 1 : 0
  subnet_id                 = azurerm_subnet.postgresql.id
  network_security_group_id = var.postgresql_nsg_id
}

resource "azurerm_subnet_network_security_group_association" "storage" {
  count                     = var.storage_subnet_cidr != "" && var.storage_nsg_id != "" ? 1 : 0
  subnet_id                 = azurerm_subnet.storage[0].id
  network_security_group_id = var.storage_nsg_id
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgresql" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.nachet.name

  tags = var.tags
}

# Data source to get VNet ID from name
data "azurerm_virtual_network" "existing" {
  name                = var.vnet_name
  resource_group_name = azurerm_resource_group.nachet.name
}

# Link Private DNS Zone to VNet
resource "azurerm_private_dns_zone_virtual_network_link" "postgresql" {
  name                  = "${var.project_name}-postgresql-dns-link-${var.environment}"
  resource_group_name   = azurerm_resource_group.nachet.name
  private_dns_zone_name = azurerm_private_dns_zone.postgresql.name
  virtual_network_id    = data.azurerm_virtual_network.existing.id
  registration_enabled  = false

  tags = var.tags
}
