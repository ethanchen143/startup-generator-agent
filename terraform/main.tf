terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# GCP Secret Manager for API Keys
resource "google_secret_manager_secret" "google_api_key" {
  secret_id = "google-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "google_search_api_key" {
  secret_id = "google-search-api-key"
  replication {
    auto {}
  }
}

# Cloud Run Service Deployment
resource "google_cloud_run_v2_service" "agent_service" {
  name     = var.service_name
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }

      env {
        name  = "FAST_MODEL"
        value = var.fast_model
      }

      env {
        name  = "REASONING_MODEL"
        value = var.reasoning_model
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_SEARCH_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_search_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}

# IAM Policy for Public Access to Dashboard API
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.agent_service.project
  location = google_cloud_run_v2_service.agent_service.location
  name     = google_cloud_run_v2_service.agent_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
