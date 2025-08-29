# Public IP for Application Gateway
resource "azurerm_public_ip" "app_gateway" {
  name                = "${var.project_name}-appgw-pip-${var.environment}"
  resource_group_name = azurerm_resource_group.nachet.name
  location            = azurerm_resource_group.nachet.location
  allocation_method   = "Static"
  sku                 = "Standard"
  
  tags = var.tags
}

# Application Gateway
resource "azurerm_application_gateway" "nachet" {
  name                = "${var.project_name}-appgw-${var.environment}"
  resource_group_name = azurerm_resource_group.nachet.name
  location            = azurerm_resource_group.nachet.location
  
  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 2
  }
  
  gateway_ip_configuration {
    name      = "appgw-ip-config"
    subnet_id = azurerm_subnet.app_gateway.id
  }
  
  frontend_port {
    name = "http-port"
    port = 80
  }
  
  frontend_port {
    name = "https-port"
    port = 443
  }
  
  frontend_ip_configuration {
    name                 = "appgw-frontend-ip"
    public_ip_address_id = azurerm_public_ip.app_gateway.id
  }
  
  backend_address_pool {
    name  = "nachet-backend-pool"
    fqdns = [azurerm_container_app.backend.latest_revision_fqdn]
  }
  
  backend_http_settings {
    name                  = "nachet-backend-settings"
    cookie_based_affinity = "Disabled"
    path                  = "/"
    port                  = 443
    protocol              = "Https"
    request_timeout       = 60
    
    # Container Apps use HTTPS with self-signed certs
    probe_name = "nachet-health-probe"
  }
  
  http_listener {
    name                           = "nachet-http-listener"
    frontend_ip_configuration_name = "appgw-frontend-ip"
    frontend_port_name             = "http-port"
    protocol                       = "Http"
  }
  
  request_routing_rule {
    name                       = "nachet-routing-rule"
    rule_type                  = "Basic"
    http_listener_name         = "nachet-http-listener"
    backend_address_pool_name  = "nachet-backend-pool"
    backend_http_settings_name = "nachet-backend-settings"
    priority                   = 1
  }
  
  probe {
    name                = "nachet-health-probe"
    protocol            = "Https"
    path                = "/health"
    host                = azurerm_container_app.backend.latest_revision_fqdn
    interval            = 30
    timeout             = 30
    unhealthy_threshold = 3
    
    match {
      status_code = ["200-399"]
    }
  }
  
  tags = var.tags
  
  depends_on = [azurerm_container_app.backend]
}
