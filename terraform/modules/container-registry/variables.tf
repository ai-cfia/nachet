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

variable "allowed_ip_1" {
  description = "First IP address allowed to access the Container Registry"
  type        = string
}

variable "allowed_ip_2" {
  description = "Second IP address allowed to access the Container Registry"
  type        = string
}

variable "vnet_name" {
  description = "The name of the virtual network"
  type        = string
}

variable "vnet_resource_group_name" {
  description = "The name of the resource group containing the virtual network"
  type        = string
}

variable "tags" {
  description = "A mapping of tags to assign to the resource"
  type        = map(string)
  default     = {}
}

variable "private_endpoint_subnet_id" {
  description = "ACR PE subnet id"
  type        = string
}
