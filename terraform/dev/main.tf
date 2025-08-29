
module "nachet" {
  source = "../modules/nachet"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Network Configuration
  vnet_name                  = var.vnet_name
  container_apps_subnet_cidr = var.container_apps_subnet_cidr
  postgresql_subnet_cidr     = var.postgresql_subnet_cidr
  storage_subnet_cidr        = var.storage_subnet_cidr
  enable_public_access       = var.enable_public_access
  allowed_ip_addresses       = var.allowed_ip_addresses
  enable_observability_stack = var.enable_observability_stack

  # Observability Stack Images
  loki_image    = var.loki_image
  grafana_image = var.grafana_image
  tempo_image   = var.tempo_image
  mimir_image   = var.mimir_image
  alloy_image   = var.alloy_image

  # Observability Stack Resources
  loki_cpu       = var.loki_cpu
  loki_memory    = var.loki_memory
  grafana_cpu    = var.grafana_cpu
  grafana_memory = var.grafana_memory
  tempo_cpu      = var.tempo_cpu
  tempo_memory   = var.tempo_memory
  mimir_cpu      = var.mimir_cpu
  mimir_memory   = var.mimir_memory
  alloy_cpu      = var.alloy_cpu
  alloy_memory   = var.alloy_memory

  # Observability Configuration
  grafana_admin_password = var.grafana_admin_password
  loki_auth_enabled      = var.loki_auth_enabled

  # Container Images
  backend_image = var.backend_image
  triton_image  = var.triton_image

  # PostgreSQL Configuration
  postgresql_admin_username = var.postgresql_admin_username
  postgresql_admin_password = var.postgresql_admin_password
  postgresql_sku_name       = var.postgresql_sku_name
  postgresql_storage_mb     = var.postgresql_storage_mb
  postgresql_version        = var.postgresql_version

  # Container Apps Resources
  container_app_cpu    = var.container_app_cpu
  container_app_memory = var.container_app_memory
  triton_cpu           = var.triton_cpu
  triton_memory        = var.triton_memory

  # Backend Environment Variables
  nachet_azure_storage_connection_string = var.nachet_azure_storage_connection_string
  nachet_data_path                       = var.nachet_data_path
  backend_port                           = var.backend_port

  # ML Model Endpoints
  ml_model_endpoint_rcnn        = var.ml_model_endpoint_rcnn
  ml_model_endpoint_swin        = var.ml_model_endpoint_swin
  ml_model_endpoint_swin_22_spp = var.ml_model_endpoint_swin_22_spp
  ml_model_endpoint_swin_27_spp = var.ml_model_endpoint_swin_27_spp
  ml_api_key                    = var.ml_api_key

  # Application Security
  jwt_secret     = var.jwt_secret
  session_secret = var.session_secret
  encryption_key = var.encryption_key

  # Application Configuration
  cors_allowed_origins = var.cors_allowed_origins
  log_level            = var.log_level

  # Azure Storage for Triton Models
  azure_storage_account_key = var.azure_storage_account_key

  # Additional Database URLs
  fertiscan_db_url = var.fertiscan_db_url
}
