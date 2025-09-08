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
  default     = "canadacentral"
}

variable "resource_group_name" {
  description = "Resource group name (will be used as prefix)"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

# Network Configuration
variable "vnet_name" {
  description = "Name of the existing VNet"
  type        = string
}

variable "vnet_resource_group_name" {
  description = "Resource group name where VNet exists"
  type        = string
}

variable "container_apps_subnet_name" {
  description = "Name of the existing Container Apps subnet (created by pipeline)"
  type        = string
}

# Container Configuration
variable "backend_image" {
  description = "Docker image for Nachet backend"
  type        = string
}

variable "container_app_cpu" {
  description = "CPU for container app"
  type        = number
}

variable "container_app_memory" {
  description = "Memory for container app"
  type        = string
}

variable "backend_port" {
  description = "Backend application port"
  type        = string
}

variable "enable_public_access" {
  description = "Enable public access for the application"
  type        = bool
  default     = false
}

variable "allowed_ip_addresses" {
  description = "List of IP addresses allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Database connections
variable "database_url" {
  description = "Nachet database connection URL"
  type        = string
  sensitive   = true
}


# Storage

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

variable "ml_api_key" {
  description = "API key for ML model endpoints"
  type        = string
  default     = ""
  sensitive   = true
}

# Application Security
variable "jwt_secret" {
  description = "JWT secret for authentication"
  type        = string
  sensitive   = true
}

variable "session_secret" {
  description = "Session secret for cookies"
  type        = string
  sensitive   = true
}

variable "encryption_key" {
  description = "Encryption key for sensitive data"
  type        = string
  sensitive   = true
}

# Application Configuration
variable "cors_allowed_origins" {
  description = "CORS allowed origins"
  type        = string
}

variable "log_level" {
  description = "Application log level"
  type        = string
}
