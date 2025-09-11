# Data sources for VNet and Container Apps subnet
data "azurerm_virtual_network" "existing" {
  name                = var.vnet_name
  resource_group_name = var.vnet_resource_group_name
}

data "azurerm_subnet" "container_apps" {
  name                 = var.container_apps_subnet_name
  virtual_network_name = var.vnet_name
  resource_group_name  = var.vnet_resource_group_name
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "nachet" {
  name                = "${var.project_name}-law-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# Container App Environment
resource "azurerm_container_app_environment" "nachet" {
  name                               = "${var.project_name}-cae-${var.environment}"
  location                           = var.location
  resource_group_name                = var.resource_group_name
  log_analytics_workspace_id         = azurerm_log_analytics_workspace.nachet.id
  infrastructure_subnet_id           = data.azurerm_subnet.container_apps.id
  # infrastructure_resource_group_name = var.infrastructure_resource_group_name
  internal_load_balancer_enabled     = true # Container apps with ingress.enabled = true will get a private IP from the subnet (same subnet as infrastructure_subnet_id)
  tags                               = var.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
    maximum_count         = 10
    minimum_count         = 0
  }
}

# Private Endpoint for Container App Environment
resource "azurerm_private_endpoint" "container_app_environment" {
  name                = "${var.project_name}-cae-pe-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = data.azurerm_subnet.container_apps.id

  private_service_connection {
    name                           = "${var.project_name}-cae-connection-${var.environment}"
    is_manual_connection           = false
    private_connection_resource_id = azurerm_container_app_environment.nachet.id
    subresource_names              = ["managedEnvironments"]
  }

  tags = var.tags
}