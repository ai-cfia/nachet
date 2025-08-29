resource "azurerm_container_app_environment" "nachet" {
  name                       = "${var.project_name}-cae-${var.environment}"
  location                   = azurerm_resource_group.nachet.location
  resource_group_name        = azurerm_resource_group.nachet.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.nachet.id
  
  # Use the created subnet for Container Apps
  infrastructure_subnet_id = azurerm_subnet.container_apps.id
  
  tags = var.tags
}

resource "azurerm_container_app" "backend" {
  name                         = "${var.project_name}-backend-ca-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.nachet.id
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
      
      env {
        name  = "DATABASE_URL"
        value = "postgresql://${var.postgresql_admin_username}:${var.postgresql_admin_password}@${azurerm_postgresql_flexible_server.nachet.fqdn}:5432/nachet_db?sslmode=require"
      }
      
      env {
        name  = "FERTISCAN_DB_URL"
        value = var.fertiscan_db_url != "" ? var.fertiscan_db_url : "postgresql://${var.postgresql_admin_username}:${var.postgresql_admin_password}@${azurerm_postgresql_flexible_server.nachet.fqdn}:5432/fertiscan_db?sslmode=require"
      }
      
      env {
        name  = "NACHET_AZURE_STORAGE_CONNECTION_STRING"
        value = var.nachet_azure_storage_connection_string != "" ? var.nachet_azure_storage_connection_string : azurerm_storage_account.nachet.primary_connection_string
      }
      
      env {
        name  = "NACHET_DATA"
        value = var.nachet_data_path
      }
      
      env {
        name  = "FRONTEND_URL"
        value = "https://${var.project_name}-backend-ca-${var.environment}.${azurerm_container_app_environment.nachet.default_domain}"
      }
      
      env {
        name  = "BACKEND_URL"
        value = "https://${var.project_name}-backend-ca-${var.environment}.${azurerm_container_app_environment.nachet.default_domain}"
      }
      
      
      env {
        name  = "ML_MODEL_ENDPOINT_RCNN"
        value = var.ml_model_endpoint_rcnn
      }
      
      env {
        name  = "SWIN_MODEL_ENDPOINT"
        value = var.ml_model_endpoint_swin != "" ? var.ml_model_endpoint_swin : "http://${azurerm_container_app.swin_classifier.name}:8000"
      }
      
      env {
        name  = "SWIN_22_SPP_MODEL_ENDPOINT"
        value = var.ml_model_endpoint_swin_22_spp != "" ? var.ml_model_endpoint_swin_22_spp : "http://${azurerm_container_app.swin_22_spp.name}:8000"
      }
      
      env {
        name  = "SWIN_27_SPP_MODEL_ENDPOINT"
        value = var.ml_model_endpoint_swin_27_spp != "" ? var.ml_model_endpoint_swin_27_spp : "http://${azurerm_container_app.swin_27_spp.name}:8000"
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
  
  depends_on = [
    azurerm_container_app.swin_classifier,
    azurerm_container_app.swin_22_spp,
    azurerm_container_app.swin_27_spp
  ]
}
