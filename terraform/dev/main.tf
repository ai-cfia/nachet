terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstatenachet"
    container_name       = "tfstate"
    key                  = "nachet-dev.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

module "nachet" {
  source = "../modules/nachet"
  
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
  
  # Container Images
  backend_image    = var.backend_image
  blob_mock_image  = var.blob_mock_image
  triton_image     = var.triton_image
  
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
  jwt_secret      = var.jwt_secret
  session_secret  = var.session_secret
  encryption_key  = var.encryption_key
  
  # Application Configuration
  cors_allowed_origins = var.cors_allowed_origins
  log_level            = var.log_level
  
  # Azure Storage for Triton Models
  azure_storage_account_key = var.azure_storage_account_key
  
  # Blob Mock Configuration
  blob_mock_port = var.blob_mock_port
  
  # Additional Database URLs
  fertiscan_db_url = var.fertiscan_db_url
}
