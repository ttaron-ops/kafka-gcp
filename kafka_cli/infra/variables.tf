#################################
###   GENERAL CONFIGURATIONS  ###
#################################

variable "project_apis" {
  description = "APIs to enable in the project"
  type        = set(string)
  default = [
    "compute.googleapis.com",
    "cloudkms.googleapis.com",
    "container.googleapis.com",
    "storage.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iamcredentials.googleapis.com",
    "servicenetworking.googleapis.com",
    "binaryauthorization.googleapis.com"
  ]
}

variable "project_id" {
  type        = string
  description = "The GCP project to use for environment deployment."
}

variable "project_name" {
  type        = string
  description = "The GCP project name."
}

variable "region" {
  type        = string
  description = "Region where the resources should be created."
  default     = "us-west1"
}

variable "zone" {
  type        = string
  description = "Zone where the resources should be created."
  default     = "us-west1-a"
}

variable "resource_prefix" {
  type        = string
  description = "Prefix for resource names"
  default     = "kafka"
}

#################################
###     ENABLE/DISABLE        ###
#################################

variable "vpc_enabled" {
  description = "Enable VPC creation"
  type        = bool
  default     = true
}

variable "keyring_enabled" {
  description = "Enable Keyring creation"
  type        = bool
  default     = false
}

variable "vpc_peering_enabled" {
  description = "Enable VPC Peering"
  type        = bool
  default     = false
}

variable "kafka_ui_enabled" {
  description = "Enable Kafka UI"
  type        = bool
  default     = false
}

#################################
###           VPC             ###
#################################

variable "vpc_name" {
  description = "VPC Name"
  type        = string
  default     = "application-vpc"
}

variable "subnet_cidr" {
  description = "CIDR range for the VPC subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "vpc_firewall" {
  description = "Firewall rules"
  type = list(object({
    name                    = string
    network                 = optional(string)
    priority                = number
    source_service_accounts = optional(list(string))
    source_ranges           = optional(list(string))
    source_tags             = optional(list(string))
    target_tags             = optional(list(string))
    direction               = string
    allow = optional(list(object({
      protocol = optional(string)
      ports    = optional(list(string))
    })), [])
    deny = optional(list(object({
      protocol = optional(string)
      ports    = optional(list(string))
    })), [])
  }))
  default = []
}

#################################
###           KMS             ###
#################################

variable "keyrings" {
  description = "Configuration for KMS keyrings and their keys"
  type = list(object({
    ring_name = string
    keys = list(object({
      name                 = string
      rotation_period      = string
      purpose              = string
      key_algorithm        = string
      key_protection_level = string
      key_users            = optional(list(string), [])
      labels               = map(string)
    }))
  }))
  default = []
}

#################################
###          COMPUTE          ###
#################################

variable "instance_count" {
  description = "Number of instances to create"
  type        = number
  default     = 1
}

variable "machine_type" {
  description = "GCP machine type for instances"
  type        = string
  default     = "e2-medium"
}

variable "disk_image" {
  description = "Boot disk image"
  type        = string
  default     = "debian-cloud/debian-11"
}

variable "disk_size_gb" {
  description = "Boot disk size in GB"
  type        = number
  default     = 50
}

variable "kafka_broker_count" {
  description = "Number of Kafka broker instances"
  type        = number
  default     = 3
}

variable "kafka_version" {
  description = "Kafka version to install"
  type        = string
  default     = "3.6.0"
}

variable "default_partitions" {
  description = "Default number of partitions for auto created topics"
  type        = number
  default     = 3
}

variable "default_replication_factor" {
  description = "Default replication factor for auto created topics"
  type        = number
  default     = 3
}

variable "min_insync_replicas" {
  description = "Minimum number of replicas that must acknowledge writes"
  type        = number
  default     = 2
}

#################################
###          SSH             ###
#################################

variable "ssh_user" {
  description = "SSH username"
  type        = string
  default     = "kafka"
}

variable "ssh_pub_key" {
  description = "SSH public key for instance access"
  type        = string
}