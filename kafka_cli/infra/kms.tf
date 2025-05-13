locals {
  flattened_keys = merge([
    for kr in var.keyrings : {
      for key in kr.keys : "${kr.ring_name}-${key.name}" => {
        ring_name            = kr.ring_name
        key_name             = key.name
        rotation_period      = key.rotation_period
        purpose              = key.purpose
        key_algorithm        = key.key_algorithm
        key_protection_level = key.key_protection_level
        key_users            = key.key_users
        labels               = key.labels
      }
    }
  ]...)
}

resource "google_kms_key_ring" "key_ring" {
  for_each = var.keyring_enabled ? { for kr in var.keyrings : kr.ring_name => kr } : {}
  name     = each.key
  location = var.region
  project  = var.project_id
}

resource "google_kms_crypto_key" "kms_key" {
  for_each = var.keyring_enabled ? local.flattened_keys : {}

  name            = each.value.key_name
  key_ring        = google_kms_key_ring.key_ring[each.value.ring_name].id
  rotation_period = each.value.rotation_period
  purpose         = each.value.purpose

  version_template {
    algorithm        = each.value.key_algorithm
    protection_level = each.value.key_protection_level
  }

  labels = each.value.labels
}

resource "google_kms_crypto_key_iam_binding" "crypto_key" {
  for_each = var.keyring_enabled ? local.flattened_keys : {}

  crypto_key_id = google_kms_crypto_key.kms_key[each.key].id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"

  members = each.value.key_users
}

# module "project-iam-bindings" {    #fix this
#   source   = "terraform-google-modules/iam/google//modules/projects_iam"
#   projects = ["${google_project.app_project.project_id}"]
#   mode     = "additive"

#   for_each = local.filtered_node_pools

#   bindings = {
#     "roles/cloudkms.cryptoKeyEncrypterDecrypter" = [
#       "serviceAccount:gke-${each.value["name"]}-sa@${google_project.app_project.project_id}.iam.gserviceaccount.com"
#     ]
#   }
# }