resource "azurerm_resource_group" "nachet" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_log_analytics_workspace" "nachet" {
  name                = "${var.project_name}-law-${var.environment}"
  location            = azurerm_resource_group.nachet.location
  resource_group_name = azurerm_resource_group.nachet.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}
