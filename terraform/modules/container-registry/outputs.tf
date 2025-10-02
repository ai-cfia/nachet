output "id" {
  description = "The ID of the Container Registry"
  value       = azurerm_container_registry.main.id
}

output "name" {
  description = "The name of the Container Registry"
  value       = azurerm_container_registry.main.name
}

output "login_server" {
  description = "The URL that can be used to log into the container registry"
  value       = azurerm_container_registry.main.login_server
}

output "admin_username" {
  description = "The Username associated with the Container Registry Admin account"
  value       = azurerm_container_registry.main.admin_username
  sensitive   = true
}

output "admin_password" {
  description = "The Password associated with the Container Registry Admin account"
  value       = azurerm_container_registry.main.admin_password
  sensitive   = true
}

output "private_endpoint_id" {
  description = "The ID of the private endpoint"
  value       = azurerm_private_endpoint.container_registry.id
}

output "private_endpoint_ip" {
  description = "The private IP address of the container registry"
  value       = azurerm_private_endpoint.container_registry.private_service_connection[0].private_ip_address
}
