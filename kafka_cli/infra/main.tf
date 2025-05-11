# resource "google_project_service" "project_apis" {
#   project                    = google_project.app_project.project_id
#   for_each                   = var.project_apis
#   service                    = each.value
#   disable_on_destroy         = false #true
#   disable_dependent_services = true
# }

# resource "time_sleep" "api_enabling" {
#   create_duration = "5m"
#   depends_on = [
#     google_project_service.project_apis
#   ]
# }