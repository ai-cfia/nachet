variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "environment" {
  description = "The environment (dev, staging, prod)"
  type        = string
}

variable "location" {
  description = "The Azure region where resources will be created"
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

variable "infrastructure_resource_group_name" {
  description = "The name of the resource group for infrastructure components"
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

variable "container_apps_subnet_name" {
  description = "The name of the subnet for container apps"
  type        = string
}

variable "private_endpoints_subnet_name" {
  description = "The name of the subnet for private endpoints"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to the resource"
  type        = map(string)
  default     = {}
}