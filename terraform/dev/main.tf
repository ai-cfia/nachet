# Container App Environment
module "container_app_environment" {
  source = "../modules/container-app-environment"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Network configuration
  vnet_name                          = var.vnet_name
  vnet_resource_group_name           = var.vnet_resource_group_name
  container_apps_subnet_name         = var.container_apps_subnet_name
  private_endpoints_subnet_name      = var.private_endpoints_subnet_name
  infrastructure_resource_group_name = var.infrastructure_resource_group_name
}

# PostgreSQL Database
module "db" {
  source = "../modules/db"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Network (for private endpoint)
  vnet_name                = var.vnet_name
  vnet_resource_group_name = var.vnet_resource_group_name
  postgresql_subnet_name   = var.postgresql_subnet_name

  # PostgreSQL Configuration
  postgresql_admin_username     = var.postgresql_admin_username
  postgresql_admin_password     = var.postgresql_admin_password
  postgresql_sku_name           = var.postgresql_sku_name
  postgresql_storage_mb         = var.postgresql_storage_mb
  postgresql_version            = var.postgresql_version
  public_network_access_enabled = var.public_network_access_enabled
}

# Container Registry
module "container_registry" {
  source = "../modules/container-registry"

  name                = "${var.project_name}-${var.environment}-acr"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  vnet_name                     = var.vnet_name
  vnet_resource_group_name      = var.vnet_resource_group_name
  private_endpoints_subnet_name = var.private_endpoints_subnet_name

  allowed_ip_ranges = var.acr_allowed_ip_ranges
}

# module "pgadmin" {
#   source = "../modules/pgadmin"
  
#   project_name                 = var.project_name
#   environment                  = var.environment
#   resource_group_name          = var.resource_group_name
#   container_app_environment_id = module.container_app_environment.container_app_environment_id
#   pgadmin_password             = var.pgadmin_password
#   tags                         = var.tags
# }

# Module 3: Nachet Application (Storage and Backend) - Commented out for now
# module "nachet" {
#   source = "../modules/nachet"

#   project_name                 = var.project_name
#   environment                  = var.environment
#   location                     = var.location
#   resource_group_name          = var.rg_nachet
#   container_app_environment_id = module.container_app_environment.container_app_environment_id
#   tags                         = var.tags

#   # Container configuration
#   backend_image        = var.backend_image
#   container_app_cpu    = var.container_app_cpu
#   container_app_memory = var.container_app_memory
#   backend_port         = var.backend_port

#   # Access control
#   enable_public_access = var.enable_public_access
#   allowed_ip_addresses = var.allowed_ip_addresses

#   # Database connections from DB module
#   database_url = module.db.nachet_connection_string

#   # ML Model Endpoints - use external endpoints only (no cross-module references)
#   ml_model_endpoint_rcnn        = var.ml_model_endpoint_rcnn
#   ml_model_endpoint_swin        = var.ml_model_endpoint_swin
#   ml_model_endpoint_swin_22_spp = var.ml_model_endpoint_swin_22_spp
#   ml_model_endpoint_swin_27_spp = var.ml_model_endpoint_swin_27_spp
#   ml_api_key                    = var.ml_api_key

#   # Application Security
#   jwt_secret     = var.jwt_secret
#   session_secret = var.session_secret
#   encryption_key = var.encryption_key

#   # Application Configuration
#   cors_allowed_origins = var.cors_allowed_origins
#   log_level            = var.log_level
# }

# # Module 3: Inference Servers (Triton containers with their own storage)
# module "nachet_inference" {
#   source = "../modules/nachet-inference"
#   count  = var.deploy_inference_servers ? 1 : 0

#   project_name        = var.project_name
#   environment         = var.environment
#   location            = var.location
#   resource_group_name = var.rg_nachet
#   tags                = var.tags

#   # Container App Environment from nachet module
#   container_app_environment_id = module.nachet.container_app_environment_id

#   # Triton configuration
#   triton_image  = var.triton_image
#   triton_cpu    = var.triton_cpu
#   triton_memory = var.triton_memory

#   # Storage key (optional)
#   azure_storage_account_key = var.azure_storage_account_key
# }

# Module 4: Monitoring Stack (Grafana, Loki, Tempo, Mimir, Alloy)
# module "monitoring" {
#   source = "../modules/monitoring"
#   count  = var.enable_observability_stack ? 1 : 0

#   project_name        = var.project_name
#   environment         = var.environment
#   resource_group_name = var.rg_nachet
#   tags                = var.tags

#   # Container App Environment from nachet module
#   container_app_environment_id = module.nachet.container_app_environment_id

#   # Database connection from db module
#   postgresql_server_fqdn    = module.db.postgresql_server_fqdn
#   postgresql_admin_username = var.postgresql_admin_username
#   postgresql_admin_password = var.postgresql_admin_password

#   # Access control
#   enable_public_access = var.enable_public_access
#   allowed_ip_addresses = var.allowed_ip_addresses

#   # Observability Stack Images
#   loki_image    = var.loki_image
#   grafana_image = var.grafana_image
#   tempo_image   = var.tempo_image
#   mimir_image   = var.mimir_image
#   alloy_image   = var.alloy_image

#   # Observability Stack Resources
#   loki_cpu       = var.loki_cpu
#   loki_memory    = var.loki_memory
#   grafana_cpu    = var.grafana_cpu
#   grafana_memory = var.grafana_memory
#   tempo_cpu      = var.tempo_cpu
#   tempo_memory   = var.tempo_memory
#   mimir_cpu      = var.mimir_cpu
#   mimir_memory   = var.mimir_memory
#   alloy_cpu      = var.alloy_cpu
#   alloy_memory   = var.alloy_memory

#   # Configuration
#   grafana_admin_password = var.grafana_admin_password
#   loki_auth_enabled      = var.loki_auth_enabled
# }
