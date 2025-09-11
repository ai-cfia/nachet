output "container_app_environment_id" {
  description = "The ID of the Container App Environment"
  value       = azurerm_container_app_environment.nachet.id
}

output "container_app_environment_name" {
  description = "The name of the Container App Environment"
  value       = azurerm_container_app_environment.nachet.name
}

output "log_analytics_workspace_id" {
  description = "The ID of the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.nachet.id
}

# output "private_endpoint_id" {
#   description = "The ID of the Container App Environment private endpoint"
#   value       = azurerm_private_endpoint.container_app_environment.id
# }