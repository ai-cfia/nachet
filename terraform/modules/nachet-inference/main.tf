# Resource Group for Inference
resource "azurerm_resource_group" "inference" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# Storage Account for Triton Models
resource "azurerm_storage_account" "triton_models" {
  name                     = replace("${var.project_name}${var.environment}triton", "-", "")
  resource_group_name      = azurerm_resource_group.inference.name
  location                 = azurerm_resource_group.inference.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "models" {
  name                  = "triton-models"
  storage_account_name  = azurerm_storage_account.triton_models.name
  container_access_type = "private"
}

# Swin Classifier Container App
resource "azurerm_container_app" "swin_classifier" {
  name                         = "${var.project_name}-swin-triton-ca-${var.environment}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = azurerm_resource_group.inference.name
  revision_mode                = "Single"

  template {
    container {
      name   = "triton-swin"
      image  = var.triton_image
      cpu    = var.triton_cpu
      memory = var.triton_memory

      command = [
        "tritonserver",
        "--model-repository=azure://${azurerm_storage_account.triton_models.name}/${azurerm_storage_container.models.name}/swin",
        "--log-verbose=1",
        "--strict-model-config=false"
      ]

      env {
        name  = "AZURE_STORAGE_ACCOUNT"
        value = azurerm_storage_account.triton_models.name
      }

      env {
        name  = "AZURE_STORAGE_KEY"
        value = var.azure_storage_account_key != "" ? var.azure_storage_account_key : azurerm_storage_account.triton_models.primary_access_key
      }

      liveness_probe {
        transport               = "HTTP"
        path                    = "/v2/health/live"
        port                    = 8000
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        path                    = "/v2/health/ready"
        port                    = 8000
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }

    min_replicas = 1
    max_replicas = 3
  }

  ingress {
    external_enabled = false
    target_port      = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}

# Swin 22 SPP Container App
resource "azurerm_container_app" "swin_22_spp" {
  name                         = "${var.project_name}-swin-22-spp-triton-ca-${var.environment}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = azurerm_resource_group.inference.name
  revision_mode                = "Single"

  template {
    container {
      name   = "triton-swin-22-spp"
      image  = var.triton_image
      cpu    = var.triton_cpu
      memory = var.triton_memory

      command = [
        "tritonserver",
        "--model-repository=azure://${azurerm_storage_account.triton_models.name}/${azurerm_storage_container.models.name}/swin-22-spp",
        "--log-verbose=1",
        "--strict-model-config=false"
      ]

      env {
        name  = "AZURE_STORAGE_ACCOUNT"
        value = azurerm_storage_account.triton_models.name
      }

      env {
        name  = "AZURE_STORAGE_KEY"
        value = var.azure_storage_account_key != "" ? var.azure_storage_account_key : azurerm_storage_account.triton_models.primary_access_key
      }

      liveness_probe {
        transport               = "HTTP"
        path                    = "/v2/health/live"
        port                    = 8000
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        path                    = "/v2/health/ready"
        port                    = 8000
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }

    min_replicas = 1
    max_replicas = 3
  }

  ingress {
    external_enabled = false
    target_port      = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}

# Swin 27 SPP Container App
resource "azurerm_container_app" "swin_27_spp" {
  name                         = "${var.project_name}-swin-27-spp-triton-ca-${var.environment}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = azurerm_resource_group.inference.name
  revision_mode                = "Single"

  template {
    container {
      name   = "triton-swin-27-spp"
      image  = var.triton_image
      cpu    = var.triton_cpu
      memory = var.triton_memory

      command = [
        "tritonserver",
        "--model-repository=azure://${azurerm_storage_account.triton_models.name}/${azurerm_storage_container.models.name}/swin-27-spp",
        "--log-verbose=1",
        "--strict-model-config=false"
      ]

      env {
        name  = "AZURE_STORAGE_ACCOUNT"
        value = azurerm_storage_account.triton_models.name
      }

      env {
        name  = "AZURE_STORAGE_KEY"
        value = var.azure_storage_account_key != "" ? var.azure_storage_account_key : azurerm_storage_account.triton_models.primary_access_key
      }

      liveness_probe {
        transport               = "HTTP"
        path                    = "/v2/health/live"
        port                    = 8000
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        path                    = "/v2/health/ready"
        port                    = 8000
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }

    min_replicas = 1
    max_replicas = 3
  }

  ingress {
    external_enabled = false
    target_port      = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}
