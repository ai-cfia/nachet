# Data sources for VNet and private endpoints subnet
data "azurerm_virtual_network" "existing" {
  name                = var.vnet_name
  resource_group_name = var.vnet_resource_group_name
}

resource "azurerm_container_registry" "main" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Premium"
  admin_enabled       = true

  public_network_access_enabled = true

  network_rule_set {
    default_action = "Deny"

    ip_rule {
      action   = "Allow"
      ip_range = "${var.allowed_ip_1}/32"
    }

    ip_rule {
      action   = "Allow"
      ip_range = "${var.allowed_ip_2}/32"
    }
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "container_registry" {
  name                = "${var.name}-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.name}-connection"
    is_manual_connection           = false
    private_connection_resource_id = azurerm_container_registry.main.id
    subresource_names              = ["registry"]
  }

  tags = var.tags
}