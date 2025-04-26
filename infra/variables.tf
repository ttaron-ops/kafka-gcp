variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "resource_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "kafka"
}

variable "subnet_cidr" {
  description = "CIDR range for the VPC subnet"
  type        = string
  default     = "10.0.0.0/24"
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

variable "ssh_user" {
  description = "SSH username"
  type        = string
  default     = "kafka"
}

variable "ssh_pub_key" {
  description = "SSH public key for instance access"
  type        = string
}
