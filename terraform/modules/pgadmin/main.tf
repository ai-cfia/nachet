# PgAdmin Container App for database management
resource "azurerm_container_app" "pgadmin" {
  name                         = "${var.project_name}-pgadmin-ca-${var.environment}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/container_app#workload_profile_name-1
  # workload_profile_name = "Consumption"

  template {
    container {
      name   = "pgadmin"
      image  = "dpage/pgadmin4:latest"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "PGADMIN_DEFAULT_EMAIL"
        value = "admin@nachet.local"
      }

      env {
        name  = "PGADMIN_DEFAULT_PASSWORD"
        value = var.pgadmin_password
      }

      env {
        name  = "PGADMIN_LISTEN_PORT"
        value = "80"
      }

      env {
        name  = "PGADMIN_CONFIG_SERVER_MODE"
        value = "True"
      }
    }

    min_replicas = 1
    max_replicas = 1
  }

  ingress {
    external_enabled = false
    target_port      = 80

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}
