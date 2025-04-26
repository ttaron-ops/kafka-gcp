output "kafka_broker_public_ips" {
  description = "Public IP addresses of Kafka brokers"
  value       = google_compute_instance.kafka_broker[*].network_interface[0].access_config[0].nat_ip
}

output "kafka_broker_internal_ips" {
  description = "Internal IP addresses of Kafka brokers"
  value       = google_compute_address.kafka_internal_ips[*].address
}

output "controller_quorum_voters" {
  description = "KRaft controller quorum voters string"
  value       = join(",", [for i in range(var.kafka_broker_count) : "${i}@${google_compute_address.kafka_internal_ips[i].address}:9093"])
}

output "cluster_size" {
  description = "Number of nodes in the Kafka cluster"
  value       = var.kafka_broker_count
}

output "vpc_network" {
  description = "The VPC network created"
  value       = google_compute_network.vpc_network.name
}

output "subnet" {
  description = "The subnet created"
  value       = google_compute_subnetwork.subnet.name
}
