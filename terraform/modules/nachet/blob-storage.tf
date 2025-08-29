resource "azurerm_storage_account" "nachet" {
  name                     = "${replace(var.project_name, "-", "")}sa${var.environment}"
  resource_group_name      = azurerm_resource_group.nachet.name
  location                 = azurerm_resource_group.nachet.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  
  # Restrict to private access only
  public_network_access_enabled = false
  
  # Configure network rules to allow Container Apps subnet
  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = [azurerm_subnet.container_apps.id]
  }
  
  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }
  
  tags = var.tags
}

resource "azurerm_storage_container" "models" {
  name                  = "models"
  storage_account_id    = azurerm_storage_account.nachet.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "images" {
  name                  = "images"
  storage_account_id    = azurerm_storage_account.nachet.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "pipelines" {
  name                  = "pipelines"
  storage_account_id    = azurerm_storage_account.nachet.id
  container_access_type = "private"
}
