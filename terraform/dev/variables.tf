# DEFAULT

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "nachet"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "canadacentral"
}

variable "resource_group_name" {
  description = "Main resource group name"
  type        = string
  default     = "rg-nachet"
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "nachet"
    ManagedBy   = "Terraform"
    Department  = "CFIA"
  }
}

# Network Configuration
variable "vnet_name" {
  description = "Name of the existing VNet where subnets will be created"
  type        = string
}

variable "vnet_resource_group_name" {
  description = "Resource group name where VNet exists"
  type        = string
}

variable "container_apps_subnet_name" {
  description = "Name of the existing Container Apps subnet (created by pipeline)"
  type        = string
  default     = "nachet-container-apps-subnet-dev"
}

variable "private_endpoint_subnet_id" {
  description = "CAE PE subnet id"
  type        = string
}


# variable "enable_observability_stack" {
#   description = "Enable Grafana LGTM + Alloy observability stack"
#   type        = bool
#   default     = true
# }

# variable "deploy_inference_servers" {
#   description = "Deploy local Triton inference servers (set to false to use external ML endpoints)"
#   type        = bool
#   default     = true
# }

# # Observability Stack Images (with cost-optimized defaults)
# variable "loki_image" {
#   description = "Docker image for Loki"
#   type        = string
#   default     = "grafana/loki:3.0.0"
# }

# variable "grafana_image" {
#   description = "Docker image for Grafana"
#   type        = string
#   default     = "grafana/grafana:10.4.0"
# }

# variable "tempo_image" {
#   description = "Docker image for Tempo"
#   type        = string
#   default     = "grafana/tempo:2.4.0"
# }

# variable "mimir_image" {
#   description = "Docker image for Mimir"
#   type        = string
#   default     = "grafana/mimir:2.12.0"
# }

# variable "alloy_image" {
#   description = "Docker image for Alloy"
#   type        = string
#   default     = "grafana/alloy:v1.0.0"
# }

# # Observability Stack Resources (minimum for cost optimization)
# variable "loki_cpu" {
#   description = "CPU allocation for Loki"
#   type        = number
#   default     = 0.25 # Reduced from 0.5 for cost
# }

# variable "loki_memory" {
#   description = "Memory allocation for Loki"
#   type        = string
#   default     = "0.5Gi" # Reduced from 1Gi for cost
# }

# variable "grafana_cpu" {
#   description = "CPU allocation for Grafana"
#   type        = number
#   default     = 0.25 # Reduced from 0.5 for cost
# }

# variable "grafana_memory" {
#   description = "Memory allocation for Grafana"
#   type        = string
#   default     = "0.5Gi" # Reduced from 1Gi for cost
# }

# variable "tempo_cpu" {
#   description = "CPU allocation for Tempo"
#   type        = number
#   default     = 0.25
# }

# variable "tempo_memory" {
#   description = "Memory allocation for Tempo"
#   type        = string
#   default     = "0.5Gi"
# }

# variable "mimir_cpu" {
#   description = "CPU allocation for Mimir"
#   type        = number
#   default     = 0.25 # Reduced from 0.5 for cost
# }

# variable "mimir_memory" {
#   description = "Memory allocation for Mimir"
#   type        = string
#   default     = "0.5Gi" # Reduced from 1Gi for cost
# }

# variable "alloy_cpu" {
#   description = "CPU allocation for Alloy"
#   type        = number
#   default     = 0.25
# }

# variable "alloy_memory" {
#   description = "Memory allocation for Alloy"
#   type        = string
#   default     = "0.5Gi"
# }

# variable "grafana_admin_password" {
#   description = "Grafana admin password - REQUIRED, no default for security"
#   type        = string
#   sensitive   = true
#   # NO DEFAULT - must be provided in terraform.tfvars
# }

# variable "loki_auth_enabled" {
#   description = "Enable authentication for Loki"
#   type        = bool
#   default     = false
# }

# # Container Images
variable "nachet_image" {
  description = "Docker image for Nachet application (combined frontend + backend)"
  type        = string
  default     = "ghcr.io/ai-cfia/nachet:dev"
}

# variable "triton_image" {
#   description = "Docker image for Triton inference server"
#   type        = string
#   default     = "nvcr.io/nvidia/tritonserver:24.10-py3"
# }

# # Container Apps Resources

variable "cae_infrastructure_resource_group_name" {
  description = "Infra resource group name"
  type        = string
}

# variable "triton_cpu" {
#   description = "CPU for Triton server containers"
#   type        = number
#   default     = 0.5 # Minimum for ML inference
# }

# variable "triton_memory" {
#   description = "Memory for Triton server containers"
#   type        = string
#   default     = "1Gi" # Minimum for ML models
# }

# # Backend Environment Variables


# # Azure Storage for Triton Models
# variable "azure_storage_account_key" {
#   description = "Storage account key for Triton model repository"
#   type        = string
#   default     = ""
#   sensitive   = true
# }



# PostgreSQL Configuration
variable "postgresql_public_network_access_enabled" {
  description = "Enable the db for public access"
  type        = bool
}

# Network Configuration (restored for private endpoint)
variable "postgresql_subnet_name" {
  description = "Name of the existing PostgreSQL subnet (created by pipeline)"
  type        = string
  default     = "nachet-postgresql-subnet-dev"
}

# Private endpoint is always enabled - no variable needed

variable "postgresql_admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  sensitive   = true
}

variable "postgresql_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "postgresql_sku_name" {
  description = "SKU for PostgreSQL flexible server"
  type        = string
  default     = "Standard_B1ms"
}

variable "postgresql_storage_mb" {
  description = "Storage size in MB for PostgreSQL"
  type        = number
  default     = 32768
}

variable "postgresql_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16"
}


# Container Registry Configuration
variable "acr_allowed_ip_1" {
  description = "First IP address allowed to access the Container Registry"
  type        = string
}

variable "acr_allowed_ip_2" {
  description = "Second IP address allowed to access the Container Registry"
  type        = string
}

# Container Instance Configuration
# variable "container_instances_subnet_name" {
#   description = "Name of the subnet for container instances"
#   type        = string
#   default     = "nachet-containerinstances-subnet-dev"
# }

# variable "acr_login_server" {
#   description = "Container Registry login server"
#   type        = string
# }

# variable "acr_username" {
#   description = "Container Registry username"
#   type        = string
# }

# variable "acr_password" {
#   description = "Container Registry password"
#   type        = string
#   sensitive   = true
# }

# variable "pgadmin_image" {
#   description = "Docker image for PgAdmin container"
#   type        = string
#   default     = "nachetdev.azurecr.io/nachet/pgadmin"
# }

# variable "pgadmin_environment_variables" {
#   description = "Environment variables for PgAdmin container"
#   type        = map(string)
#   default     = {}
# }

# variable "pgadmin_secure_environment_variables" {
#   description = "Secure environment variables for PgAdmin container"
#   type        = map(string)
#   default     = {}
#   sensitive   = true
# }

# Nachet Environment Variables (following var.env_ pattern)
variable "env_azure_api_scope_claim" {
  description = "Azure API scope claim"
  type        = string
  sensitive   = true
}

variable "env_azure_auth_enabled" {
  description = "Azure authentication enabled flag"
  type        = string
  default     = "true"
}

variable "env_azure_client_id" {
  description = "Azure client ID"
  type        = string
  sensitive   = true
}

variable "env_azure_tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
}

variable "env_blob_storage_endpoint_base" {
  description = "Blob storage endpoint base URL"
  type        = string
}

variable "env_blob_storage_endpoint_protocol" {
  description = "Blob storage endpoint protocol"
  type        = string
  default     = "https"
}

variable "env_blob_storage_endpoint_suffix" {
  description = "Blob storage endpoint suffix"
  type        = string
  default     = "core.windows.net"
}

variable "env_blob_storage_key" {
  description = "Blob storage access key"
  type        = string
  sensitive   = true
}

variable "env_blob_storage_name" {
  description = "Blob storage account name"
  type        = string
}

variable "env_blob_storage_provider" {
  description = "Blob storage provider"
  type        = string
  default     = "azure"
}

variable "env_cors_allow_origins" {
  description = "CORS allowed origins"
  type        = string
  default     = "*"
}

variable "env_db_host" {
  description = "Database host"
  type        = string
}

variable "env_db_name" {
  description = "Database name"
  type        = string
}

variable "env_db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "env_db_port" {
  description = "Database port"
  type        = string
  default     = "5432"
}

variable "env_db_user" {
  description = "Database user"
  type        = string
}

variable "env_frontend_blob_container" {
  description = "Frontend blob container name"
  type        = string
  default     = "frontend"
}

variable "env_frontend_version_file" {
  description = "Frontend version file name"
  type        = string
  default     = "version.json"
}

variable "env_minio_access_key" {
  description = "MinIO access key (if using MinIO instead of Azure Blob)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "env_minio_secret_key" {
  description = "MinIO secret key (if using MinIO instead of Azure Blob)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "env_nachet_schema" {
  description = "Nachet database schema name"
  type        = string
  default     = "nachet"
}

variable "env_security_headers_preset" {
  description = "Security headers preset configuration"
  type        = string
  default     = "strict"
}

variable "env_testing" {
  description = "Testing mode flag"
  type        = string
  default     = "false"
}

variable "env_trusted_hosts" {
  description = "Trusted hosts for the application"
  type        = string
  default     = "*"
}

# Proxy Configuration
variable "container_instances_subnet_name" {
  description = "Name of the subnet for container instances"
  type        = string
  default     = "nachet-containerinstances-subnet-dev"
}

variable "proxy_image" {
  description = "Docker image for proxy container"
  type        = string
  default     = "ghcr.io/ai-cfia/nachet-proxy:latest"
}

variable "proxy_cpu" {
  description = "CPU allocation for proxy container"
  type        = number
  default     = 1
}

variable "proxy_memory" {
  description = "Memory allocation for proxy container (in GB)"
  type        = number
  default     = 2
}

variable "proxy_ssl_certificate_content" {
  description = "SSL certificate content in PEM format (certificate + private key)"
  type        = string
  sensitive   = true
}

variable "proxy_environment_variables" {
  description = "Environment variables for proxy container"
  type        = map(string)
  default     = {}
}

variable "proxy_secure_environment_variables" {
  description = "Secure environment variables for proxy container"
  type        = map(string)
  default     = {}
  sensitive   = true
}
