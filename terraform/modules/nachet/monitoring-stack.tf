# PostgreSQL databases for observability stack
resource "azurerm_postgresql_flexible_server_database" "loki" {
  count     = var.enable_observability_stack ? 1 : 0
  name      = var.observability_database_names.loki
  server_id = azurerm_postgresql_flexible_server.nachet.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_postgresql_flexible_server_database" "grafana" {
  count     = var.enable_observability_stack ? 1 : 0
  name      = var.observability_database_names.grafana
  server_id = azurerm_postgresql_flexible_server.nachet.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_postgresql_flexible_server_database" "tempo" {
  count     = var.enable_observability_stack ? 1 : 0
  name      = var.observability_database_names.tempo
  server_id = azurerm_postgresql_flexible_server.nachet.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_postgresql_flexible_server_database" "mimir" {
  count     = var.enable_observability_stack ? 1 : 0
  name      = var.observability_database_names.mimir
  server_id = azurerm_postgresql_flexible_server.nachet.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Loki - Log aggregation system
resource "azurerm_container_app" "loki" {
  count                        = var.enable_observability_stack ? 1 : 0
  name                         = "${var.project_name}-loki-ca-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.nachet.id
  resource_group_name          = azurerm_resource_group.nachet.name
  revision_mode                = "Single"

  template {
    container {
      name   = "loki"
      image  = var.loki_image
      cpu    = var.loki_cpu
      memory = var.loki_memory

      args = ["-config.file=/etc/loki/local-config.yaml"]

      # Health checks for Loki
      liveness_probe {
        path                    = "/ready"
        port                    = 3100
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        path                    = "/ready"
        port                    = 3100
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }

      env {
        name  = "LOKI_AUTH_ENABLED"
        value = tostring(var.loki_auth_enabled)
      }

      # PostgreSQL configuration for Loki
      env {
        name  = "LOKI_STORAGE_BACKEND"
        value = "postgres"
      }

      env {
        name  = "POSTGRES_HOST"
        value = azurerm_postgresql_flexible_server.nachet.fqdn
      }

      env {
        name  = "POSTGRES_USER"
        value = var.postgresql_admin_username
      }

      env {
        name  = "POSTGRES_PASSWORD"
        value = var.postgresql_admin_password
      }

      env {
        name  = "POSTGRES_DB"
        value = "loki_db"
      }
    }

    # No volume needed - using PostgreSQL

    min_replicas = 1
    max_replicas = 2
  }

  ingress {
    external_enabled = var.enable_public_access
    target_port      = 3100

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
  }

  tags = var.tags
}

# Grafana - Visualization and dashboards
resource "azurerm_container_app" "grafana" {
  count                        = var.enable_observability_stack ? 1 : 0
  name                         = "${var.project_name}-grafana-ca-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.nachet.id
  resource_group_name          = azurerm_resource_group.nachet.name
  revision_mode                = "Single"

  template {
    container {
      name   = "grafana"
      image  = var.grafana_image
      cpu    = var.grafana_cpu
      memory = var.grafana_memory

      # Health checks for Grafana
      liveness_probe {
        path                    = "/api/health"
        port                    = 3000
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        path                    = "/api/health"
        port                    = 3000
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }

      env {
        name  = "GF_SECURITY_ADMIN_PASSWORD"
        value = var.grafana_admin_password
      }

      env {
        name  = "GF_USERS_ALLOW_SIGN_UP"
        value = "false" # Keep hardcoded for security
      }

      env {
        name  = "GF_LOG_LEVEL"
        value = "info"
      }

      # PostgreSQL configuration for Grafana
      env {
        name  = "GF_DATABASE_TYPE"
        value = "postgres"
      }

      env {
        name  = "GF_DATABASE_HOST"
        value = "${azurerm_postgresql_flexible_server.nachet.fqdn}:5432"
      }

      env {
        name  = "GF_DATABASE_NAME"
        value = "grafana_db"
      }

      env {
        name  = "GF_DATABASE_USER"
        value = var.postgresql_admin_username
      }

      env {
        name  = "GF_DATABASE_PASSWORD"
        value = var.postgresql_admin_password
      }

      env {
        name  = "GF_DATABASE_SSL_MODE"
        value = "require"
      }
    }

    # No volume needed - using PostgreSQL

    min_replicas = 1
    max_replicas = 2
  }

  ingress {
    external_enabled = var.enable_public_access # Allow external access for Grafana dashboards
    target_port      = 3000

    # IP restrictions - only allow your specified IP address
    dynamic "ip_security_restriction" {
      for_each = var.allowed_ip_addresses
      content {
        ip_address_range = ip_security_restriction.value
        name             = "AllowGrafanaIP-${ip_security_restriction.key}"
        action           = "Allow"
      }
    }

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}

# Tempo - Distributed tracing system
resource "azurerm_container_app" "tempo" {
  count                        = var.enable_observability_stack ? 1 : 0
  name                         = "${var.project_name}-tempo-ca-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.nachet.id
  resource_group_name          = azurerm_resource_group.nachet.name
  revision_mode                = "Single"

  template {
    container {
      name   = "tempo"
      image  = var.tempo_image
      cpu    = var.tempo_cpu
      memory = var.tempo_memory

      args = ["-config.file=/etc/tempo/tempo.yaml"]

      # Health checks for Tempo
      liveness_probe {
        path                    = "/ready"
        port                    = 3200
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        path                    = "/ready"
        port                    = 3200
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }

      # PostgreSQL configuration for Tempo
      env {
        name  = "TEMPO_STORAGE_TRACE_BACKEND"
        value = "postgresql"
      }

      env {
        name  = "TEMPO_STORAGE_TRACE_POSTGRESQL_ENDPOINT"
        value = "${azurerm_postgresql_flexible_server.nachet.fqdn}:5432"
      }

      env {
        name  = "TEMPO_STORAGE_TRACE_POSTGRESQL_DATABASE"
        value = "tempo_db"
      }

      env {
        name  = "TEMPO_STORAGE_TRACE_POSTGRESQL_USERNAME"
        value = var.postgresql_admin_username
      }

      env {
        name  = "TEMPO_STORAGE_TRACE_POSTGRESQL_PASSWORD"
        value = var.postgresql_admin_password
      }
    }

    # No volume needed - using PostgreSQL

    min_replicas = 1
    max_replicas = 2
  }

  ingress {
    external_enabled = false # Internal only
    target_port      = 3200

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}

# Mimir - Long-term metrics storage
resource "azurerm_container_app" "mimir" {
  count                        = var.enable_observability_stack ? 1 : 0
  name                         = "${var.project_name}-mimir-ca-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.nachet.id
  resource_group_name          = azurerm_resource_group.nachet.name
  revision_mode                = "Single"

  template {
    container {
      name   = "mimir"
      image  = var.mimir_image
      cpu    = var.mimir_cpu
      memory = var.mimir_memory

      args = ["-config.file=/etc/mimir/mimir.yaml"]

      # Health checks for Mimir
      liveness_probe {
        path                    = "/ready"
        port                    = 8080
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        path                    = "/ready"
        port                    = 8080
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }

      # PostgreSQL configuration for Mimir
      env {
        name  = "MIMIR_BLOCKS_STORAGE_BACKEND"
        value = "postgresql"
      }

      env {
        name  = "MIMIR_BLOCKS_STORAGE_POSTGRESQL_ENDPOINT"
        value = "${azurerm_postgresql_flexible_server.nachet.fqdn}:5432"
      }

      env {
        name  = "MIMIR_BLOCKS_STORAGE_POSTGRESQL_DATABASE"
        value = "mimir_db"
      }

      env {
        name  = "MIMIR_BLOCKS_STORAGE_POSTGRESQL_USERNAME"
        value = var.postgresql_admin_username
      }

      env {
        name  = "MIMIR_BLOCKS_STORAGE_POSTGRESQL_PASSWORD"
        value = var.postgresql_admin_password
      }
    }

    # No volume needed - using PostgreSQL

    min_replicas = 1
    max_replicas = 2
  }

  ingress {
    external_enabled = false # Internal only
    target_port      = 8080

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}

# Alloy - Telemetry data collection agent
resource "azurerm_container_app" "alloy" {
  count                        = var.enable_observability_stack ? 1 : 0
  name                         = "${var.project_name}-alloy-ca-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.nachet.id
  resource_group_name          = azurerm_resource_group.nachet.name
  revision_mode                = "Single"

  template {
    container {
      name   = "alloy"
      image  = var.alloy_image
      cpu    = var.alloy_cpu
      memory = var.alloy_memory

      args = ["run", "--server.http.listen-addr=0.0.0.0:12345", "--storage.path", "/tmp/alloy"]

      # Health checks for Alloy
      liveness_probe {
        path                    = "/-/healthy"
        port                    = 12345
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        path                    = "/-/ready"
        port                    = 12345
        transport               = "HTTP"
        initial_delay           = 60
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }

      env {
        name  = "ALLOY_MODE"
        value = "flow"
      }
    }

    min_replicas = 1
    max_replicas = 1
  }

  ingress {
    external_enabled = var.enable_public_access # Allow external access for Alloy dashboard
    target_port      = 12345

    # IP restrictions - only allow your specified IP address
    dynamic "ip_security_restriction" {
      for_each = var.allowed_ip_addresses
      content {
        ip_address_range = ip_security_restriction.value
        name             = "AllowAlloyIP-${ip_security_restriction.key}"
        action           = "Allow"
      }
    }

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags
}

# All data stored in PostgreSQL - no additional storage needed
