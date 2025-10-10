# Data sources for VNet and subnet
data "azurerm_virtual_network" "existing" {
  name                = var.vnet_name
  resource_group_name = var.vnet_resource_group_name
}

data "azurerm_subnet" "container_instances" {
  name                 = var.subnet_name
  virtual_network_name = var.vnet_name
  resource_group_name  = var.vnet_resource_group_name
}

# Container Instance Group
resource "azurerm_container_group" "main" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = var.os_type

  # Network configuration
  ip_address_type = "Private"
  subnet_ids      = [data.azurerm_subnet.container_instances.id]

  # Container Registry credentials
  image_registry_credential {
    server   = var.registry_login_server
    username = var.registry_username
    password = var.registry_password
  }

  container {
    name   = var.container_name
    image  = var.image
    cpu    = var.cpu
    memory = var.memory

    ports {
      port     = 443
      protocol = "TCP"
    }

    ports {
      port     = 80
      protocol = "TCP"
    }

    ports {
      port     = 8404
      protocol = "TCP"
    }

    environment_variables = var.environment_variables
    secure_environment_variables = var.secure_environment_variables

    # SSL volume mount
    volume {
      name       = "ssl-certs"
      mount_path = "/etc/ssl/certs"
      read_only  = true
      
      secret = {
        "server.pem" = base64encode(var.ssl_certificate_content)
      }
    }
  }

  tags = var.tags
}
