variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name where Container Apps will be deployed (from nachet module)"
  type        = string
}

variable "container_app_environment_id" {
  description = "Container App Environment ID"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

variable "postgresql_server_fqdn" {
  description = "PostgreSQL server FQDN"
  type        = string
}

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

variable "allowed_ip_addresses" {
  description = "List of IP addresses allowed to access Container Apps"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_public_access" {
  description = "Enable public access for monitoring apps"
  type        = bool
  default     = false
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

# Configuration
variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
}

variable "loki_auth_enabled" {
  description = "Enable authentication for Loki"
  type        = bool
  default     = false
}
