variable "name" {
  description = "The name of the Container Registry"
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group in which to create the Container Registry"
  type        = string
}

variable "location" {
  description = "The Azure region where the Container Registry should be created"
  type        = string
}

variable "allowed_ip_ranges" {
  description = "List of IP ranges allowed to access the Container Registry"
  type        = list(string)
  default     = []
}

variable "vnet_name" {
  description = "The name of the virtual network"
  type        = string
}

variable "vnet_resource_group_name" {
  description = "The name of the resource group containing the virtual network"
  type        = string
}

variable "private_endpoints_subnet_name" {
  description = "The name of the subnet for private endpoints"
  type        = string
}

variable "tags" {
  description = "A mapping of tags to assign to the resource"
  type        = map(string)
  default     = {}
}