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

variable "container_app_environment_id" {
  description = "Container App Environment ID (shared)"
  type        = string
}

# Container Registry variables
variable "acr_login_server" {
  description = "Azure Container Registry login server"
  type        = string
}

variable "acr_admin_username" {
  description = "Azure Container Registry admin username"
  type        = string
}

variable "acr_admin_password" {
  description = "Azure Container Registry admin password"
  type        = string
  sensitive   = true
}

# Container Configuration
variable "nachet_image" {
  description = "Docker image for Nachet application"
  type        = string
}

# Environment variables following the var.env_ pattern for secrets
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
