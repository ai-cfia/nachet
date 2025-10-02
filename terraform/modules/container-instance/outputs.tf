output "id" {
  description = "The ID of the Container Group"
  value       = azurerm_container_group.main.id
}

output "name" {
  description = "The name of the Container Group"
  value       = azurerm_container_group.main.name
}

output "ip_address" {
  description = "The private IP address of the Container Group"
  value       = azurerm_container_group.main.ip_address
}

output "fqdn" {
  description = "The FQDN of the Container Group"
  value       = azurerm_container_group.main.fqdn
}

output "location" {
  description = "The location of the Container Group"
  value       = azurerm_container_group.main.location
}

output "resource_group_name" {
  description = "The resource group name of the Container Group"
  value       = azurerm_container_group.main.resource_group_name
}
