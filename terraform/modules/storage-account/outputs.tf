output "id" {
  description = "The ID of the Storage Account"
  value       = azurerm_storage_account.main.id
}

output "name" {
  description = "The name of the Storage Account"
  value       = azurerm_storage_account.main.name
}

output "primary_blob_endpoint" {
  description = "The endpoint URL for blob storage in the primary location"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "primary_access_key" {
  description = "The primary access key for the storage account"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "secondary_access_key" {
  description = "The secondary access key for the storage account"
  value       = azurerm_storage_account.main.secondary_access_key
  sensitive   = true
}

output "primary_connection_string" {
  description = "The primary connection string for the storage account"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

# Private endpoint outputs (commented out for now)
# output "private_endpoint_id" {
#   description = "The ID of the private endpoint"
#   value       = azurerm_private_endpoint.storage_account.id
# }

# output "private_endpoint_ip" {
#   description = "The private IP address of the storage account"
#   value       = azurerm_private_endpoint.storage_account.private_service_connection[0].private_ip_address
# }

output "threat_protection_id" {
  description = "The ID of the Advanced Threat Protection configuration"
  value       = azurerm_advanced_threat_protection.storage.id
}