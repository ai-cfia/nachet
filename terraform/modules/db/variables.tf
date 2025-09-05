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
  description = "Resource group name for database"
  type        = string
}

variable "vnet_resource_group_name" {
  description = "Resource group name where VNet exists"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    "env" = "dev"
  }
}

# Network Configuration
variable "vnet_name" {
  description = "Name of the existing VNet"
  type        = string
}

variable "postgresql_subnet_cidr" {
  description = "CIDR block for PostgreSQL subnet"
  type        = string
}

variable "route_table_id" {
  description = "Full Azure Resource ID of the existing route table"
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
