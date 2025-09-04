output "loki_url" {
  value = length(azurerm_container_app.loki) > 0 ? "https://${azurerm_container_app.loki[0].latest_revision_fqdn}" : ""
}

output "grafana_url" {
  value = length(azurerm_container_app.grafana) > 0 ? "https://${azurerm_container_app.grafana[0].latest_revision_fqdn}" : ""
}

output "tempo_url" {
  value = length(azurerm_container_app.tempo) > 0 ? "https://${azurerm_container_app.tempo[0].latest_revision_fqdn}" : ""
}

output "mimir_url" {
  value = length(azurerm_container_app.mimir) > 0 ? "https://${azurerm_container_app.mimir[0].latest_revision_fqdn}" : ""
}

output "alloy_url" {
  value = length(azurerm_container_app.alloy) > 0 ? "https://${azurerm_container_app.alloy[0].latest_revision_fqdn}" : ""
}
