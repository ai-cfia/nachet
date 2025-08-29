output "resource_group_name" {
  description = "Resource group name"
  value       = module.nachet.resource_group_name
}

output "postgresql_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = module.nachet.postgresql_fqdn
}

output "backend_fqdn" {
  description = "Backend Container App FQDN"
  value       = module.nachet.backend_fqdn
}

output "backend_url" {
  description = "Backend Container App URL"
  value       = module.nachet.backend_url
}


output "swin_classifier_fqdns" {
  description = "Swin Classifier Container Apps FQDNs"
  value       = module.nachet.swin_classifier_fqdns
}

output "container_app_environment_id" {
  description = "Container App Environment ID"
  value       = module.nachet.container_app_environment_id
}

output "storage_account_name" {
  description = "Storage Account name"
  value       = module.nachet.storage_account_name
}

output "storage_account_primary_key" {
  description = "Storage Account primary key"
  value       = module.nachet.storage_account_primary_key
  sensitive   = true
}

output "storage_account_connection_string" {
  description = "Storage Account connection string"
  value       = module.nachet.storage_account_connection_string
  sensitive   = true
}

output "nachet_app_url" {
  description = "Nachet application URL (restricted to your IP)"
  value       = module.nachet.nachet_app_url
}

output "nachet_app_fqdn" {
  description = "Nachet application FQDN"
  value       = module.nachet.nachet_app_fqdn
}

# Observability Stack Outputs
output "grafana_url" {
  description = "Grafana dashboard URL (restricted to your IP)"
  value       = module.nachet.grafana_url
}

output "observability_stack_enabled" {
  description = "Whether observability stack is enabled"
  value       = module.nachet.observability_stack_enabled
}

output "alloy_dashboard_url" {
  description = "Alloy dashboard URL (restricted to your IP)"
  value       = module.nachet.alloy_dashboard_url
}
