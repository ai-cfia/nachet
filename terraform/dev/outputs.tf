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

output "app_gateway_public_ip" {
  description = "Application Gateway public IP address"
  value       = module.nachet.app_gateway_public_ip
}

output "app_gateway_url" {
  description = "Application Gateway public URL to access Nachet"
  value       = module.nachet.app_gateway_url
}
