output "swin_classifier_name" {
  value = azurerm_container_app.swin_classifier.name
}

output "swin_22_spp_name" {
  value = azurerm_container_app.swin_22_spp.name
}

output "swin_27_spp_name" {
  value = azurerm_container_app.swin_27_spp.name
}

output "swin_classifier_endpoint" {
  value = "http://${azurerm_container_app.swin_classifier.name}:8000"
}

output "swin_22_spp_endpoint" {
  value = "http://${azurerm_container_app.swin_22_spp.name}:8000"
}

output "swin_27_spp_endpoint" {
  value = "http://${azurerm_container_app.swin_27_spp.name}:8000"
}
