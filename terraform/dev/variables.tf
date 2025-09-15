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

variable "enable_public_access" {
  description = "Enable public access for Container Apps (set to false for full private deployment)"
  type        = bool
  default     = false
}

variable "allowed_ip_addresses" {
  description = "List of IP addresses allowed to access Container Apps (CIDR format)"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Allow all for dev - restrict in prod
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
variable "backend_image" {
  description = "Docker image for Nachet backend"
  type        = string
  default     = "ghcr.io/ai-cfia/nachet-backend:dev"
}

# variable "triton_image" {
#   description = "Docker image for Triton inference server"
#   type        = string
#   default     = "nvcr.io/nvidia/tritonserver:24.10-py3"
# }

# # Container Apps Resources
variable "container_app_cpu" {
  description = "CPU for container apps"
  type        = number
  default     = 0.25 # Minimum CPU allocation
}

variable "container_app_memory" {
  description = "Memory for container apps"
  type        = string
  default     = "0.5Gi" # Minimum memory allocation
}

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

variable "backend_port" {
  description = "Backend application port"
  type        = string
  default     = "8080"
}

# # ML Model Endpoints (if using external services instead of Triton)
variable "ml_model_endpoint_rcnn" {
  description = "RCNN model endpoint URL"
  type        = string
  default     = ""
  sensitive   = true
}

variable "ml_model_endpoint_swin" {
  description = "Swin model endpoint URL"
  type        = string
  default     = ""
  sensitive   = true
}

variable "ml_model_endpoint_swin_22_spp" {
  description = "Swin 22 SPP model endpoint URL"
  type        = string
  default     = ""
  sensitive   = true
}

variable "ml_model_endpoint_swin_27_spp" {
  description = "Swin 27 SPP model endpoint URL"
  type        = string
  default     = ""
  sensitive   = true
}

# ML Model API Keys
variable "ml_api_key" {
  description = "API key for ML model endpoints"
  type        = string
  default     = ""
  sensitive   = true
}

# # Application Configuration
variable "jwt_secret" {
  description = "JWT secret for authentication"
  type        = string
  sensitive   = true
}

variable "cors_allowed_origins" {
  description = "CORS allowed origins"
  type        = string
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "DEBUG"
}

# # Azure Storage for Triton Models
# variable "azure_storage_account_key" {
#   description = "Storage account key for Triton model repository"
#   type        = string
#   default     = ""
#   sensitive   = true
# }


variable "encryption_key" {
  description = "Encryption key for sensitive data"
  type        = string
  default     = ""
  sensitive   = true
}

variable "session_secret" {
  description = "Session secret for cookies"
  type        = string
  default     = ""
  sensitive   = true
}

variable "pgadmin_password" {
  description = "PgAdmin admin password"
  type        = string
  sensitive   = true
}

variable "pgadmin_image" {
  description = "PgAdmin container image from ACR"
  type        = string
  default     = "your-acr-name.azurecr.io/pgadmin:latest"
}

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

# Database connection string (used by application modules)
variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
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
