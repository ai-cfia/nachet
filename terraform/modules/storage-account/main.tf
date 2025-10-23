resource "azurerm_storage_account" "main" {
  name                     = var.name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = var.account_tier
  account_replication_type = var.account_replication_type

  public_network_access_enabled = var.public_network_access_enabled

  blob_properties {
    delete_retention_policy {
      days = var.blob_delete_retention_days
    }

    container_delete_retention_policy {
      days = var.container_delete_retention_days
    }

    versioning_enabled  = var.blob_versioning_enabled
    change_feed_enabled = var.blob_change_feed_enabled
  }

  network_rules {
    default_action = "Deny"
    ip_rules       = var.allowed_ips
    bypass         = ["AzureServices"]
  }

  tags = var.tags
}

# Microsoft Defender for Storage (malware scanning)
resource "azurerm_security_center_storage_defender" "storage" {
  storage_account_id                          = azurerm_storage_account.main.id
  malware_scanning_on_upload_enabled          = var.malware_scanning_enabled
  malware_scanning_on_upload_cap_gb_per_month = var.malware_scanning_cap_gb_per_month
  sensitive_data_discovery_enabled            = var.sensitive_data_discovery_enabled
}

# Private endpoint (commented out for now)
# resource "azurerm_private_endpoint" "storage_account" {
#   name                = "${var.name}-pe"
#   location            = var.location
#   resource_group_name = var.resource_group_name
#   subnet_id           = var.private_endpoint_subnet_id

#   private_service_connection {
#     name                           = "${var.name}-connection"
#     is_manual_connection           = false
#     private_connection_resource_id = azurerm_storage_account.main.id
#     subresource_names              = ["blob"]
#   }

#   tags = var.tags
# }
