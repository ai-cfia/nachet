# Nachet Application Outputs
# output "resource_group_name" {
#   description = "Resource group name"
#   value       = module.nachet.resource_group_name
# }

# output "storage_account_name" {
#   description = "Storage account name"
#   value       = module.nachet.storage_account_name
# }

# output "storage_account_primary_key" {
#   description = "Storage Account primary key"
#   value       = module.nachet.storage_account_primary_access_key
#   sensitive   = true
# }

# output "storage_account_connection_string" {
#   description = "Storage Account connection string"
#   value       = module.nachet.storage_account_primary_connection_string
#   sensitive   = true
# }

# output "nachet_app_url" {
#   description = "Nachet application URL"
#   value       = module.nachet.nachet_app_url
# }

# output "backend_fqdn" {
#   description = "Backend Container App FQDN"
#   value       = module.nachet.backend_fqdn
# }

# output "backend_url" {
#   description = "Backend Container App URL"
#   value       = module.nachet.backend_url
# }

# # Database Outputs
# output "postgresql_fqdn" {
#   description = "PostgreSQL server FQDN"
#   value       = module.db.postgresql_server_fqdn
# }

# PgAdmin Outputs
# output "pgadmin_url" {
#   description = "PgAdmin internal URL (accessible from VNet only)"
#   value       = module.pgadmin.pgadmin_url
# }

# Inference Server Outputs
# output "inference_servers_deployed" {
#   description = "Whether inference servers are deployed"
#   value       = var.deploy_inference_servers
# }

# output "swin_endpoints" {
#   description = "Swin model endpoints (if deployed)"
#   value = var.deploy_inference_servers ? (
#     length(module.nachet_inference) > 0 ? {
#       swin_base   = module.nachet_inference[0].swin_classifier_endpoint
#       swin_22_spp = module.nachet_inference[0].swin_22_spp_endpoint
#       swin_27_spp = module.nachet_inference[0].swin_27_spp_endpoint
#     } : {}
#   ) : {}
# }

# # Monitoring Stack Outputs
# output "observability_stack_enabled" {
#   description = "Whether observability stack is enabled"
#   value       = var.enable_observability_stack
# }

# output "grafana_url" {
#   description = "Grafana dashboard URL (if enabled)"
#   value       = var.enable_observability_stack && length(module.monitoring) > 0 ? module.monitoring[0].grafana_url : "Monitoring disabled"
# }

# output "loki_url" {
#   description = "Loki logs endpoint (if enabled)"
#   value       = var.enable_observability_stack && length(module.monitoring) > 0 ? module.monitoring[0].loki_url : "Monitoring disabled"
# }

# Container Registry Outputs
# output "container_registry_id" {
#   description = "Container Registry ID"
#   value       = module.container_registry.id
# }

# output "container_registry_name" {
#   description = "Container Registry name"
#   value       = module.container_registry.name
# }

# output "container_registry_login_server" {
#   description = "Container Registry login server URL"
#   value       = module.container_registry.login_server
# }

# output "container_registry_admin_username" {
#   description = "Container Registry admin username"
#   value       = module.container_registry.admin_username
#   sensitive   = true
# }

# output "container_registry_admin_password" {
#   description = "Container Registry admin password"
#   value       = module.container_registry.admin_password
#   sensitive   = true
# }

# output "container_registry_private_endpoint_ip" {
#   description = "Container Registry private endpoint IP address"
#   value       = module.container_registry.private_endpoint_ip
# }

# PgAdmin Container Instance Outputs
# output "pgadmin_ip_address" {
#   description = "PgAdmin container private IP address"
#   value       = module.pgadmin.ip_address
# }

# output "pgadmin_fqdn" {
#   description = "PgAdmin container FQDN"
#   value       = module.pgadmin.fqdn
# }

# Storage Account Outputs
output "storage_account_id" {
  description = "Storage Account ID"
  value       = module.storage_account.id
}

output "storage_account_name" {
  description = "Storage Account name"
  value       = module.storage_account.name
}

output "storage_account_primary_blob_endpoint" {
  description = "Storage Account primary blob endpoint"
  value       = module.storage_account.primary_blob_endpoint
}

output "storage_account_primary_access_key" {
  description = "Storage Account primary access key"
  value       = module.storage_account.primary_access_key
  sensitive   = true
}

output "storage_account_primary_connection_string" {
  description = "Storage Account primary connection string"
  value       = module.storage_account.primary_connection_string
  sensitive   = true
}

output "storage_account_threat_protection_id" {
  description = "Storage Account threat protection ID"
  value       = module.storage_account.threat_protection_id
}
