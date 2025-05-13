resource "google_compute_instance" "kafka" {
  count        = var.kafka_broker_count
  name         = "${var.resource_prefix}-broker-${count.index}"
  machine_type = var.machine_type
  zone         = var.zone

  tags = ["kafka-broker"]

  boot_disk {
    initialize_params {
      image  = var.disk_image
      size   = var.disk_size_gb
      type   = "pd-standard"
    }
  }

  network_interface {
    network = var.vpc_enabled ? google_compute_network.vpc[0].name : "default"
    subnetwork = var.vpc_enabled ? google_compute_subnetwork.subnet[0].name : null
    access_config {
      // Ephemeral public IP
    }
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${var.ssh_pub_key}"
    kafka_version = var.kafka_version
    kafka_broker_count = var.kafka_broker_count
    default_partitions = var.default_partitions
    default_replication_factor = var.default_replication_factor
    min_insync_replicas = var.min_insync_replicas
  }

  metadata_startup_script = file("${path.module}/kafka_bootstrap.sh")

  service_account {
    scopes = ["cloud-platform"]
  }
}
