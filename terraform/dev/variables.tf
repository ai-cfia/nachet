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
  description = "Resource group name"
  type        = string
  default     = "nachet-dev-rg"
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

variable "container_apps_subnet_cidr" {
  description = "CIDR block for Container Apps subnet (e.g., 10.0.1.0/26)"
  type        = string
  default     = "10.0.1.0/26"  # 59 usable IPs
}

variable "postgresql_subnet_cidr" {
  description = "CIDR block for PostgreSQL subnet (e.g., 10.0.2.0/28)"
  type        = string
  default     = "10.0.2.0/28"  # 11 usable IPs
}

variable "storage_subnet_cidr" {
  description = "CIDR block for Storage subnet - optional (e.g., 10.0.3.0/29)"
  type        = string
  default     = ""  # Optional - leave empty if not using private endpoints
}

variable "app_gateway_subnet_cidr" {
  description = "CIDR block for Application Gateway subnet (e.g., 10.0.4.0/27)"
  type        = string
  default     = "10.0.4.0/27"  # 27 usable IPs for App Gateway
}

variable "enable_public_access" {
  description = "Enable public access for Container Apps (set to false for full private deployment)"
  type        = bool
  default     = false
}

# Container Images
variable "backend_image" {
  description = "Docker image for Nachet backend"
  type        = string
  default     = "ghcr.io/ai-cfia/nachet-backend:dev"
}

variable "triton_image" {
  description = "Docker image for Triton inference server"
  type        = string
  default     = "nvcr.io/nvidia/tritonserver:24.10-py3"
}

# PostgreSQL Configuration
variable "postgresql_admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "nachetadmin"
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
  default     = "B_Standard_B2ms"
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

# Container Apps Resources
variable "container_app_cpu" {
  description = "CPU for container apps"
  type        = number
  default     = 0.5
}

variable "container_app_memory" {
  description = "Memory for container apps"
  type        = string
  default     = "1Gi"
}

variable "triton_cpu" {
  description = "CPU for Triton server containers"
  type        = number
  default     = 2
}

variable "triton_memory" {
  description = "Memory for Triton server containers"
  type        = string
  default     = "4Gi"
}

# Backend Environment Variables
variable "nachet_azure_storage_connection_string" {
  description = "Azure Storage connection string for Nachet"
  type        = string
  sensitive   = true
}

variable "nachet_data_path" {
  description = "Data path for Nachet"
  type        = string
  default     = "/app/data"
}

variable "backend_port" {
  description = "Backend application port"
  type        = string
  default     = "8080"
}

# ML Model Endpoints (if using external services instead of Triton)
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

# Application Configuration
variable "jwt_secret" {
  description = "JWT secret for authentication"
  type        = string
  sensitive   = true
}

variable "cors_allowed_origins" {
  description = "CORS allowed origins"
  type        = string
  default     = "*"
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "DEBUG"
}

# Azure Storage for Triton Models
variable "azure_storage_account_key" {
  description = "Storage account key for Triton model repository"
  type        = string
  default     = ""
  sensitive   = true
}

# Additional Backend Environment Variables
variable "fertiscan_db_url" {
  description = "FertiScan database connection URL"
  type        = string
  default     = ""
  sensitive   = true
}

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
