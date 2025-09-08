# Resource Group
resource "azurerm_resource_group" "nachet" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# Storage Account for Nachet
resource "azurerm_storage_account" "nachet" {
  name                     = replace("${var.project_name}${var.environment}st", "-", "")
  resource_group_name      = azurerm_resource_group.nachet.name
  location                 = azurerm_resource_group.nachet.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  # Security enhancements for Azure Policy compliance
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = true
  public_network_access_enabled   = var.enable_public_access
  https_traffic_only_enabled      = true

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
    versioning_enabled  = true
    change_feed_enabled = true
  }

  tags = var.tags
}

# Blob Container for Nachet images
resource "azurerm_storage_container" "nachet_images" {
  name                  = "nachet-images"
  storage_account_name  = azurerm_storage_account.nachet.name
  container_access_type = "private"
}

# Nachet Backend Container App
resource "azurerm_container_app" "backend" {
  name                         = "${var.project_name}-backend-ca-${var.environment}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = azurerm_resource_group.nachet.name
  revision_mode                = "Single"

  template {
    container {
      name   = "nachet-backend"
      image  = var.backend_image
      cpu    = var.container_app_cpu
      memory = var.container_app_memory

      env {
        name  = "PORT"
        value = var.backend_port
      }

      liveness_probe {
        path                    = "/health"
        port                    = tonumber(var.backend_port)
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        path                    = "/health"
        port                    = tonumber(var.backend_port)
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }


      env {
        name  = "NACHET_AZURE_STORAGE_CONNECTION_STRING"
        value = azurerm_storage_account.nachet.primary_connection_string
      }

      env {
        name  = "NACHET_DATA"
        value = "/app/data" # Fixed path, no need for variable
      }

      env {
        name  = "FRONTEND_URL"
        value = "https://${azurerm_container_app.backend.latest_revision_fqdn}"
      }

      env {
        name  = "BACKEND_URL"
        value = "https://${azurerm_container_app.backend.latest_revision_fqdn}"
      }

      env {
        name  = "ML_MODEL_ENDPOINT_RCNN"
        value = var.ml_model_endpoint_rcnn
      }

      env {
        name  = "SWIN_MODEL_ENDPOINT"
        value = var.ml_model_endpoint_swin
      }

      env {
        name  = "SWIN_22_SPP_MODEL_ENDPOINT"
        value = var.ml_model_endpoint_swin_22_spp
      }

      env {
        name  = "SWIN_27_SPP_MODEL_ENDPOINT"
        value = var.ml_model_endpoint_swin_27_spp
      }

      env {
        name  = "ML_API_KEY"
        value = var.ml_api_key
      }

      env {
        name  = "JWT_SECRET"
        value = var.jwt_secret
      }

      env {
        name  = "SESSION_SECRET"
        value = var.session_secret
      }

      env {
        name  = "ENCRYPTION_KEY"
        value = var.encryption_key
      }

      env {
        name  = "CORS_ALLOWED_ORIGINS"
        value = var.cors_allowed_origins
      }

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }
    }

    min_replicas = 1
    max_replicas = 5
  }

  ingress {
    external_enabled = var.enable_public_access
    target_port      = tonumber(var.backend_port)

    dynamic "ip_security_restriction" {
      for_each = var.allowed_ip_addresses
      content {
        ip_address_range = ip_security_restriction.value
        name             = "AllowIP-${ip_security_restriction.key}"
        action           = "Allow"
      }
    }

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

    cors {
      allowed_origins = split(",", var.cors_allowed_origins)
      allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      allowed_headers = ["*"]
    }
  }

  tags = var.tags
}
