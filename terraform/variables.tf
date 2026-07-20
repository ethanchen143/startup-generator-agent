variable "gcp_project_id" {
  type        = string
  description = "GCP Project ID for deployment"
  default     = "startup-generator-agent-prod"
}

variable "gcp_region" {
  type        = string
  description = "GCP region for Cloud Run deployment"
  default     = "us-central1"
}

variable "service_name" {
  type        = string
  description = "Name of the Cloud Run service"
  default     = "5-days-agent-service"
}

variable "container_image" {
  type        = string
  description = "Container image URI"
  default     = "gcr.io/startup-generator-agent-prod/backend:latest"
}

variable "fast_model" {
  type        = string
  description = "Fast model for discovery and search"
  default     = "gemini-2.5-flash"
}

variable "reasoning_model" {
  type        = string
  description = "High reasoning model for ideation and implementation"
  default     = "gemini-2.5-pro"
}
