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
  description = "Resource group name for inference servers"
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

variable "triton_image" {
  description = "Docker image for Triton inference server"
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

variable "azure_storage_account_key" {
  description = "Storage account key for Triton model repository (optional)"
  type        = string
  default     = ""
  sensitive   = true
}
