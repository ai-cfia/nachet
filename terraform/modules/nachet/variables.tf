variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

# Network Configuration
variable "vnet_name" {
  description = "Name of the existing VNet where subnets will be created"
  type        = string
}

variable "container_apps_subnet_cidr" {
  description = "CIDR block for Container Apps subnet (e.g., 10.0.1.0/26)"
  type        = string
}

variable "postgresql_subnet_cidr" {
  description = "CIDR block for PostgreSQL subnet (e.g., 10.0.2.0/28)"
  type        = string
}

variable "storage_subnet_cidr" {
  description = "CIDR block for Storage subnet - optional (e.g., 10.0.3.0/29)"
  type        = string
  default     = ""
}


# Optional: NSG IDs if you want to associate existing NSGs with subnets
variable "container_apps_nsg_id" {
  description = "ID of existing NSG to associate with Container Apps subnet (optional)"
  type        = string
  default     = ""
}

variable "postgresql_nsg_id" {
  description = "ID of existing NSG to associate with PostgreSQL subnet (optional)"
  type        = string
  default     = ""
}

variable "storage_nsg_id" {
  description = "ID of existing NSG to associate with Storage subnet (optional)"
  type        = string
  default     = ""
}

variable "enable_public_access" {
  description = "Enable public access for Container Apps (set to false for full private deployment)"
  type        = bool
  default     = false
}

variable "enable_observability_stack" {
  description = "Enable Grafana LGTM + Alloy observability stack"
  type        = bool
  default     = true
}

variable "allowed_ip_addresses" {
  description = "List of IP addresses allowed to access Container Apps directly (CIDR format, e.g. 205.194.32.99/32)"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Allow all by default - CHANGE THIS!
}

# Container Images
variable "backend_image" {
  description = "Docker image for Nachet backend"
  type        = string
}

variable "triton_image" {
  description = "Docker image for Triton inference server"
  type        = string
}

# Observability Stack Images
variable "loki_image" {
  description = "Docker image for Loki"
  type        = string
  default     = "grafana/loki:3.0.0"
}

variable "grafana_image" {
  description = "Docker image for Grafana"
  type        = string
  default     = "grafana/grafana:10.4.0"
}

variable "tempo_image" {
  description = "Docker image for Tempo"
  type        = string
  default     = "grafana/tempo:2.4.0"
}

variable "mimir_image" {
  description = "Docker image for Mimir"
  type        = string
  default     = "grafana/mimir:2.12.0"
}

variable "alloy_image" {
  description = "Docker image for Alloy"
  type        = string
  default     = "grafana/alloy:v1.0.0"
}

# Observability Stack Resources
variable "loki_cpu" {
  description = "CPU allocation for Loki"
  type        = number
  default     = 0.5
}

variable "loki_memory" {
  description = "Memory allocation for Loki"
  type        = string
  default     = "1Gi"
}

variable "grafana_cpu" {
  description = "CPU allocation for Grafana"
  type        = number
  default     = 0.5
}

variable "grafana_memory" {
  description = "Memory allocation for Grafana"
  type        = string
  default     = "1Gi"
}

variable "tempo_cpu" {
  description = "CPU allocation for Tempo"
  type        = number
  default     = 0.25
}

variable "tempo_memory" {
  description = "Memory allocation for Tempo"
  type        = string
  default     = "0.5Gi"
}

variable "mimir_cpu" {
  description = "CPU allocation for Mimir"
  type        = number
  default     = 0.5
}

variable "mimir_memory" {
  description = "Memory allocation for Mimir"
  type        = string
  default     = "1Gi"
}

variable "alloy_cpu" {
  description = "CPU allocation for Alloy"
  type        = number
  default     = 0.25
}

variable "alloy_memory" {
  description = "Memory allocation for Alloy"
  type        = string
  default     = "0.5Gi"
}

# Observability Stack Configuration
variable "grafana_admin_password" {
  description = "Grafana admin password - REQUIRED, no default for security"
  type        = string
  sensitive   = true
  # NO DEFAULT - must be provided in terraform.tfvars
}

variable "loki_auth_enabled" {
  description = "Enable authentication for Loki"
  type        = bool
  default     = false
}

variable "observability_replicas_min" {
  description = "Minimum replicas for observability components"
  type        = number
  default     = 1
}

variable "observability_replicas_max" {
  description = "Maximum replicas for observability components"
  type        = number
  default     = 2
}

variable "observability_database_names" {
  description = "Database names for observability components"
  type = object({
    loki    = string
    grafana = string
    tempo   = string
    mimir   = string
  })
  default = {
    loki    = "loki_db"
    grafana = "grafana_db"
    tempo   = "tempo_db"
    mimir   = "mimir_db"
  }
}

# PostgreSQL Configuration
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
}

variable "postgresql_storage_mb" {
  description = "Storage size in MB for PostgreSQL"
  type        = number
}

variable "postgresql_version" {
  description = "PostgreSQL version"
  type        = string
}

# Container Apps Resources
variable "container_app_cpu" {
  description = "CPU for container apps"
  type        = number
}

variable "container_app_memory" {
  description = "Memory for container apps"
  type        = string
}

variable "triton_cpu" {
  description = "CPU for Triton server containers"
  type        = number
}

variable "triton_memory" {
  description = "Memory for Triton server containers"
  type        = string
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
}

variable "backend_port" {
  description = "Backend application port"
  type        = string
}

# ML Model Endpoints
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
}

variable "log_level" {
  description = "Application log level"
  type        = string
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
