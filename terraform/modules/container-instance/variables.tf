variable "name" {
  description = "The name of the Container Group"
  type        = string
}

variable "location" {
  description = "The Azure region where the Container Group should be created"
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group in which to create the Container Group"
  type        = string
}

variable "os_type" {
  description = "The OS type for the containers (Linux or Windows)"
  type        = string
  default     = "Linux"
}

# Network configuration
variable "vnet_name" {
  description = "The name of the virtual network"
  type        = string
}

variable "vnet_resource_group_name" {
  description = "The name of the resource group containing the virtual network"
  type        = string
}

variable "subnet_name" {
  description = "The name of the subnet for container instances"
  type        = string
}

# Container Registry configuration
variable "registry_login_server" {
  description = "The container registry login server"
  type        = string
}

variable "registry_username" {
  description = "The container registry username"
  type        = string
}

variable "registry_password" {
  description = "The container registry password"
  type        = string
  sensitive   = true
}

# Container configuration
variable "container_name" {
  description = "The name of the container"
  type        = string
  default     = "main"
}

variable "image" {
  description = "The container image"
  type        = string
}

variable "cpu" {
  description = "The number of CPU cores to allocate to the container"
  type        = number
  default     = 1
}

variable "memory" {
  description = "The amount of memory to allocate to the container (in GB)"
  type        = number
  default     = 1.5
}

variable "port" {
  description = "The port to expose"
  type        = number
  default     = 80
}

variable "protocol" {
  description = "The protocol for the port (TCP or UDP)"
  type        = string
  default     = "TCP"
}

# Environment variables
variable "environment_variables" {
  description = "A map of environment variables to set in the container"
  type        = map(string)
  default     = {}
}

variable "secure_environment_variables" {
  description = "A map of secure environment variables to set in the container"
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "tags" {
  description = "A mapping of tags to assign to the resource"
  type        = map(string)
  default     = {}
}