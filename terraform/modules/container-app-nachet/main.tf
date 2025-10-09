resource "azurerm_container_app" "nachet" {
  name                         = "${var.project_name}-nachet-ca-${var.environment}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  registry {
    server               = var.acr_login_server
    username             = var.acr_admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = var.acr_admin_password
  }

  template {
    container {
      name   = "nachet"
      image  = var.nachet_image
      cpu    = 2
      memory = "4Gi"

      env {
        name  = "AZURE_API_SCOPE_CLAIM"
        value = var.env_azure_api_scope_claim
      }

      env {
        name  = "AZURE_AUTH_ENABLED"
        value = var.env_azure_auth_enabled
      }
      
      env {
        name  = "AZURE_CLIENT_ID"
        value = var.env_azure_client_id
      }
      
      env {
        name  = "AZURE_TENANT_ID"
        value = var.env_azure_tenant_id
      }

      env {
        name  = "BLOB_STORAGE_ENDPOINT_BASE"
        value = var.env_blob_storage_endpoint_base
      }

      env {
        name  = "BLOB_STORAGE_ENDPOINT_PROTOCOL"
        value = var.env_blob_storage_endpoint_protocol
      }

      env {
        name  = "BLOB_STORAGE_ENDPOINT_SUFFIX"
        value = var.env_blob_storage_endpoint_suffix
      }

      env {
        name  = "BLOB_STORAGE_KEY"
        value = var.env_blob_storage_key
      }

      env {
        name  = "BLOB_STORAGE_NAME"
        value = var.env_blob_storage_name
      }

      env {
        name  = "BLOB_STORAGE_PROVIDER"
        value = var.env_blob_storage_provider
      }

      env {
        name  = "CORS_ALLOW_ORIGINS"
        value = var.env_cors_allow_origins
      }

      env {
        name  = "DB_HOST"
        value = var.env_db_host
      }

      env {
        name  = "DB_NAME"
        value = var.env_db_name
      }

      env {
        name  = "DB_PASSWORD"
        value = var.env_db_password
      }

      env {
        name  = "DB_PORT"
        value = var.env_db_port
      }

      env {
        name  = "DB_USER"
        value = var.env_db_user
      }

      env {
        name  = "FRONTEND_BLOB_CONTAINER"
        value = var.env_frontend_blob_container
      }

      env {
        name  = "FRONTEND_VERSION_FILE"
        value = var.env_frontend_version_file
      }

      env {
        name  = "MINIO_ACCESS_KEY"
        value = var.env_minio_access_key
      }

      env {
        name  = "MINIO_SECRET_KEY"
        value = var.env_minio_secret_key
      }

      env {
        name  = "NACHET_SCHEMA"
        value = var.env_nachet_schema
      }

      env {
        name  = "SECURITY_HEADERS_PRESET"
        value = var.env_security_headers_preset
      }

      env {
        name  = "TESTING"
        value = var.env_testing
      }

      env {
        name  = "TRUSTED_HOSTS"
        value = var.env_trusted_hosts
      }

    }

    min_replicas = 1
    max_replicas = 1
  }

  ingress {
    external_enabled = false
    target_port      = 8080

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}