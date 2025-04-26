terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.0"
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# VPC Network
resource "google_compute_network" "vpc_network" {
  name                    = "${var.resource_prefix}-vpc"
  auto_create_subnetworks = false
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.resource_prefix}-subnet"
  ip_cidr_range = var.subnet_cidr
  network       = google_compute_network.vpc_network.id
  region        = var.region
}

# Firewall rules for Kafka in KRaft mode
resource "google_compute_firewall" "kafka_firewall" {
  name    = "${var.resource_prefix}-kafka-firewall"
  network = google_compute_network.vpc_network.id

  allow {
    protocol = "tcp"
    ports    = ["9092", "9093", "22"] # Kafka external, Kafka internal, SSH
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["kafka"]
}

# Reserve static internal IPs for Kafka brokers
resource "google_compute_address" "kafka_internal_ips" {
  count        = var.kafka_broker_count
  name         = "${var.resource_prefix}-broker-${count.index}-internal-ip"
  address_type = "INTERNAL"
  purpose      = "GCE_ENDPOINT"
  subnetwork   = google_compute_subnetwork.subnet.id
  region       = var.region
}

# Compute instances for Kafka brokers in KRaft mode
resource "google_compute_instance" "kafka_broker" {
  count        = var.kafka_broker_count
  name         = "${var.resource_prefix}-broker-${count.index}"
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["kafka"]

  boot_disk {
    initialize_params {
      image = var.disk_image
      size  = var.disk_size_gb
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subnet.id
    network_ip = google_compute_address.kafka_internal_ips[count.index].address
    access_config {
      // Ephemeral public IP
    }
  }

  # Include broker information as both metadata and labels
  metadata = {
    ssh-keys = "${var.ssh_user}:${var.ssh_pub_key}"
    broker-id = count.index
    cluster-size = var.kafka_broker_count
    kraft-mode = "true"
  }

  labels = {
    broker-id = "${count.index}"
    kafka-node = "true"
    kraft-mode = "true"
  }

  # This script will run on instance startup
  metadata_startup_script = <<SCRIPT
#!/bin/bash
set -e

# Install Java and other dependencies
apt-get update
apt-get install -y openjdk-11-jdk wget curl jq

# Create kafka user
useradd -m -s /bin/bash kafka || true

# Set up directories
mkdir -p /opt/kafka/data
mkdir -p /opt/kafka/logs
mkdir -p /opt/kafka/config
chown -R kafka:kafka /opt/kafka

# Download and extract Kafka
KAFKA_VERSION="${var.kafka_version}"
wget -q "https://archive.apache.org/dist/kafka/$${KAFKA_VERSION}/kafka_2.13-$${KAFKA_VERSION}.tgz" -O /tmp/kafka.tgz
tar -xzf /tmp/kafka.tgz -C /opt
mv /opt/kafka_2.13-$${KAFKA_VERSION} /opt/kafka/dist
chown -R kafka:kafka /opt/kafka

# Get instance metadata
BROKER_ID=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/broker-id" -H "Metadata-Flavor: Google")
CLUSTER_SIZE=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/cluster-size" -H "Metadata-Flavor: Google")
HOSTNAME=$(hostname)
INTERNAL_IP=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip" -H "Metadata-Flavor: Google")

# Get broker IPs
CONTROLLER_QUORUM_VOTERS=""
for i in $(seq 0 $((CLUSTER_SIZE-1))); do
  BROKER_IP=$(gcloud compute addresses describe ${var.resource_prefix}-broker-$i-internal-ip --region ${var.region} --format='get(address)' --project=${var.project_id})
  if [ $i -gt 0 ]; then
    CONTROLLER_QUORUM_VOTERS="$CONTROLLER_QUORUM_VOTERS,"
  fi
  CONTROLLER_QUORUM_VOTERS="$${CONTROLLER_QUORUM_VOTERS}$${i}@$${BROKER_IP}:9093"
done

# Generate KRaft mode properties
cat > /opt/kafka/config/kraft.properties <<EOF
# Server basics
broker.id=$BROKER_ID
node.id=$BROKER_ID

# KRaft mode configuration
process.roles=broker,controller
controller.quorum.voters=$CONTROLLER_QUORUM_VOTERS

# Listeners
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
advertised.listeners=PLAINTEXT://$INTERNAL_IP:9092
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT

# Log configuration
log.dirs=/opt/kafka/data
num.partitions=${var.default_partitions}
default.replication.factor=${var.default_replication_factor}

# Other configurations
offsets.topic.replication.factor=${var.default_replication_factor}
transaction.state.log.replication.factor=${var.default_replication_factor}
transaction.state.log.min.isr=${var.min_insync_replicas}
min.insync.replicas=${var.min_insync_replicas}

# KRaft mode specific settings
authorizer.class.name=
auto.create.topics.enable=true
EOF

# Format storage directories for KRaft mode
if [ "$BROKER_ID" == "0" ]; then
  # Only need to run this once on one node
  sudo -u kafka /opt/kafka/dist/bin/kafka-storage.sh format -t $(uuidgen) -c /opt/kafka/config/kraft.properties
fi

# Create a systemd service for Kafka
cat > /etc/systemd/system/kafka.service <<EOF
[Unit]
Description=Apache Kafka
After=network.target

[Service]
Type=simple
User=kafka
Group=kafka
ExecStart=/opt/kafka/dist/bin/kafka-server-start.sh /opt/kafka/config/kraft.properties
ExecStop=/opt/kafka/dist/bin/kafka-server-stop.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start Kafka service
systemctl daemon-reload
systemctl enable kafka
systemctl start kafka

echo "Kafka in KRaft mode setup completed."
SCRIPT

  # Make sure we have access to the GCP API for metadata lookups
  service_account {
    scopes = ["cloud-platform"]
  }

  depends_on = [google_compute_subnetwork.subnet]
}
