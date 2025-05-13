output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "vpc_name" {
  description = "The VPC name"
  value       = var.vpc_enabled ? var.vpc_name : "N/A"
}

output "subnet_cidr" {
  description = "The subnet CIDR range"
  value       = var.vpc_enabled ? var.subnet_cidr : "N/A"
}

output "kafka_brokers" {
  description = "List of Kafka broker instance names"
  value       = google_compute_instance.kafka_broker[*].name
}

output "kafka_broker_ips" {
  description = "List of Kafka broker internal IPs"
  value       = google_compute_instance.kafka_broker[*].network_interface[0].network_ip
}

output "kafka_version" {
  description = "The Kafka version installed"
  value       = var.kafka_version
}

output "kafka_ui_enabled" {
  description = "Whether Kafka UI is enabled"
  value       = var.kafka_ui_enabled
}

output "ssh_user" {
  description = "SSH username for instance access"
  value       = var.ssh_user
}

