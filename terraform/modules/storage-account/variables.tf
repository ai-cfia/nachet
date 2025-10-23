variable "name" {
  description = "The name of the Storage Account"
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group in which to create the Storage Account"
  type        = string
}

variable "location" {
  description = "The Azure region where the Storage Account should be created"
  type        = string
}

variable "account_tier" {
  description = "The tier of the storage account"
  type        = string
  default     = "Standard"
}

variable "account_replication_type" {
  description = "The replication type of the storage account"
  type        = string
  default     = "LRS"
}

variable "public_network_access_enabled" {
  description = "Whether the public network access is enabled"
  type        = bool
  default     = true
}

variable "allowed_ips" {
  description = "List of IP addresses/CIDR blocks allowed to access the Storage Account"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "A mapping of tags to assign to the resource"
  type        = map(string)
  default     = {}
}

# Private endpoint variables (commented out for now)
# variable "private_endpoint_subnet_id" {
#   description = "Storage Account PE subnet id"
#   type        = string
# }

# Blob properties variables
variable "blob_delete_retention_days" {
  description = "Number of days to retain deleted blobs"
  type        = number
  default     = 7
}

variable "container_delete_retention_days" {
  description = "Number of days to retain deleted containers"
  type        = number
  default     = 7
}

variable "blob_versioning_enabled" {
  description = "Enable blob versioning"
  type        = bool
  default     = false
}

variable "blob_change_feed_enabled" {
  description = "Enable blob change feed"
  type        = bool
  default     = false
}

