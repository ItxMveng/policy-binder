# Infrastructure de production de l'API sur Cloud Run (écrite et validée, appliquée dès qu'un compte
# de facturation Google Cloud est disponible ; la démo actuelle tourne sur Hugging Face Spaces).

locals {
  # Les valeurs sont ajoutées hors Terraform (gcloud secrets versions add) : elles ne finissent
  # jamais dans l'état Terraform.
  secrets = ["LLM_API_KEY", "QDRANT_URL", "QDRANT_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
}

resource "google_project_service" "apis" {
  for_each           = toset(["run.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com"])
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "policy-binder"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

resource "google_service_account" "api" {
  account_id   = "policy-binder-api"
  display_name = "API Le Classeur (Cloud Run)"
}

resource "google_secret_manager_secret" "runtime" {
  for_each  = toset(local.secrets)
  secret_id = lower(replace(each.value, "_", "-"))
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "api_reads_secrets" {
  for_each  = google_secret_manager_secret.runtime
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "policy-binder-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api.email
    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }
    containers {
      image = var.image
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
      env {
        name  = "ALLOWED_ORIGINS"
        value = var.allowed_origins
      }
      dynamic "env" {
        for_each = google_secret_manager_secret.runtime
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = "latest"
            }
          }
        }
      }
      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 12
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.api_reads_secrets]
}

# Démo publique : tout le monde peut appeler l'API (les limites sont appliquées par l'API).
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
