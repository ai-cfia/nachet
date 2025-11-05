# Terraform State Storage Account Private Endpoint
data "azurerm_storage_account" "tfstate" {
  name                = "tfstatenachet"
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_endpoint" "tfstate_storage" {
  name                = "tfstatenachet-sa-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "tfstatenachet-sa-connection"
    is_manual_connection           = false
    private_connection_resource_id = data.azurerm_storage_account.tfstate.id
    subresource_names              = ["blob"]
  }

  tags = var.tags
}

# Container App Environment
module "container_app_environment" {
  source = "../modules/container-app-environment"
  
  # Default
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Networking
  vnet_name                  = var.vnet_name
  vnet_resource_group_name   = var.vnet_resource_group_name
  private_endpoint_subnet_id = var.private_endpoint_subnet_id
  container_apps_subnet_name = var.container_apps_subnet_name

  # CAE
  infrastructure_resource_group_name = var.cae_infrastructure_resource_group_name
}

# PostgreSQL Database
# module "db" {
#   source = "../modules/postgresql-flexible-server"

#   # Default
#   project_name        = var.project_name
#   environment         = var.environment
#   location            = var.location
#   resource_group_name = var.resource_group_name
#   tags                = var.tags

#   # Network
#   vnet_name                = var.vnet_name
#   vnet_resource_group_name = var.vnet_resource_group_name
#   postgresql_subnet_name   = var.postgresql_subnet_name

#   # PostgreSQL Configuration
#   postgresql_admin_username     = var.postgresql_admin_username
#   postgresql_admin_password     = var.postgresql_admin_password
#   postgresql_sku_name           = var.postgresql_sku_name
#   postgresql_storage_mb         = var.postgresql_storage_mb
#   postgresql_version            = var.postgresql_version
#   public_network_access_enabled = var.postgresql_public_network_access_enabled
# }

# Container Registry
# module "container_registry" {
#   source = "../modules/container-registry"

#   # Default
#   name                = "${var.project_name}${var.environment}acr"
#   resource_group_name = var.resource_group_name
#   location            = var.location
#   tags                = var.tags

#   # Network
#   vnet_name                  = var.vnet_name
#   vnet_resource_group_name   = var.vnet_resource_group_name
#   private_endpoint_subnet_id = var.private_endpoint_subnet_id

#   # ACR
#   allowed_ip_1 = var.acr_allowed_ip_1
#   allowed_ip_2 = var.acr_allowed_ip_2
# }

module "storage_account_nachet_external" {
  source = "../modules/storage-account"

  name                = "${var.project_name}external"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  # Storage Configuration
  account_tier             = var.storage_account_tier
  account_replication_type = var.storage_replication_type

  # Network Security
  public_network_access_enabled = var.storage_public_access_enabled
  allowed_ips                   = var.storage_allowed_ips

  # Security Features
  malware_scanning_enabled          = var.storage_malware_scanning_enabled
  malware_scanning_cap_gb_per_month = var.storage_malware_scanning_cap_gb_per_month
  sensitive_data_discovery_enabled  = var.storage_sensitive_data_discovery_enabled

  # Blob Properties
  blob_delete_retention_days      = var.blob_delete_retention_days
  container_delete_retention_days = var.container_delete_retention_days
  blob_versioning_enabled         = var.blob_versioning_enabled
  blob_change_feed_enabled        = var.blob_change_feed_enabled
}

# Nachet Application (Combined Frontend + Backend)
# module "nachet" {
#   source = "../modules/container-app-nachet"

#   # Default
#   project_name        = var.project_name
#   environment         = var.environment
#   location            = var.location
#   resource_group_name = var.resource_group_name
#   tags                = var.tags

#   # Container App Environment
#   container_app_environment_id = module.container_app_environment.container_app_environment_id

#   # Container Registry
#   acr_login_server    = module.container_registry.login_server
#   acr_admin_username  = module.container_registry.admin_username
#   acr_admin_password  = module.container_registry.admin_password

#   # Container Image
#   nachet_image = var.nachet_image

#   # Environment variables
#   env_azure_api_scope_claim           = var.env_azure_api_scope_claim
#   env_azure_auth_enabled              = var.env_azure_auth_enabled
#   env_azure_client_id                 = var.env_azure_client_id
#   env_azure_tenant_id                 = var.env_azure_tenant_id
#   env_blob_storage_endpoint_base      = var.env_blob_storage_endpoint_base
#   env_blob_storage_endpoint_protocol  = var.env_blob_storage_endpoint_protocol
#   env_blob_storage_endpoint_suffix    = var.env_blob_storage_endpoint_suffix
#   env_blob_storage_key                = var.env_blob_storage_key
#   env_blob_storage_name               = var.env_blob_storage_name
#   env_blob_storage_provider           = var.env_blob_storage_provider
#   env_cors_allow_origins              = var.env_cors_allow_origins
#   env_db_host                         = var.env_db_host
#   env_db_name                         = var.env_db_name
#   env_db_password                     = var.env_db_password
#   env_db_port                         = var.env_db_port
#   env_db_user                         = var.env_db_user
#   env_frontend_blob_container         = var.env_frontend_blob_container
#   env_frontend_version_file           = var.env_frontend_version_file
#   env_minio_access_key                = var.env_minio_access_key
#   env_minio_secret_key                = var.env_minio_secret_key
#   env_nachet_schema                   = var.env_nachet_schema
#   env_security_headers_preset         = var.env_security_headers_preset
#   env_testing                         = var.env_testing
#   env_trusted_hosts                   = var.env_trusted_hosts
# }

# Proxy Container Instance
# module "proxy" {
#   source = "../modules/container-instance-proxy"

#   # Default
#   name                = "${var.project_name}-${var.environment}-proxy"
#   location            = var.location
#   resource_group_name = var.resource_group_name
#   tags                = var.tags

#   # Network
#   vnet_name                 = var.vnet_name
#   vnet_resource_group_name  = var.vnet_resource_group_name
#   subnet_name              = var.container_instances_subnet_name

#   # Container Registry
#   registry_login_server = module.container_registry.login_server
#   registry_username     = module.container_registry.admin_username
#   registry_password     = module.container_registry.admin_password

#   # Container Configuration
#   container_name = "nachet-proxy"
#   image         = var.proxy_image
#   cpu           = var.proxy_cpu
#   memory        = var.proxy_memory

#   # SSL Certificate
#   ssl_certificate_content = var.proxy_ssl_certificate_content

#   # Environment variables
#   environment_variables = var.proxy_environment_variables
#   secure_environment_variables = var.proxy_secure_environment_variables
# }
