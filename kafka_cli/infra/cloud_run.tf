resource "google_cloud_run_service" "kafka_ui" {
  count = var.kafka_ui_enabled ? 1 : 0
  name     = "kafka-ui"
  location = var.region

  template {
    spec {
      containers {
        image = "docker.io/provectuslabs/kafka-ui:master"

        env {
          name  = "DYNAMIC_CONFIG_ENABLED"
          value = "true"
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  metadata {
    annotations = {
      "run.googleapis.com/ingress" = "internal"
    }
  }
}

resource "google_cloud_run_service_iam_member" "invoker" {
  count = var.kafka_ui_enabled ? 1 : 0
  service    = google_cloud_run_service.kafka_ui.name
  location   = google_cloud_run_service.kafka_ui.location
  role       = "roles/run.invoker"
  member     = "allAuthenticatedUsers"
}