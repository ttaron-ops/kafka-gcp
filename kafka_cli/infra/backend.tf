terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.3.0"

  backend "gcs" {
    bucket = var.terraform_state_bucket
    prefix = var.terraform_state_prefix
  }
}