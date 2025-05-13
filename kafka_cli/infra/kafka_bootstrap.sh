#!/bin/bash

# Exit on error
set -e

# Get instance metadata
INSTANCE_NAME=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/name")
BROKER_ID=$(echo $INSTANCE_NAME | grep -o '[0-9]*$')
KAFKA_VERSION=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/kafka_version")
KAFKA_BROKER_COUNT=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/kafka_broker_count")
DEFAULT_PARTITIONS=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/default_partitions")
DEFAULT_REPLICATION_FACTOR=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/default_replication_factor")
MIN_INSYNC_REPLICAS=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/min_insync_replicas")

# Install Java
apt-get update
apt-get install -y openjdk-11-jdk

# Create Kafka user and directories
useradd -m -s /bin/bash kafka
mkdir -p /opt/kafka
mkdir -p /var/lib/kafka/data
mkdir -p /var/log/kafka
chown -R kafka:kafka /opt/kafka /var/lib/kafka /var/log/kafka

# Download and install Kafka
cd /opt/kafka
wget https://downloads.apache.org/kafka/${KAFKA_VERSION}/kafka_2.13-${KAFKA_VERSION}.tgz
tar xzf kafka_2.13-${KAFKA_VERSION}.tgz --strip-components=1
rm kafka_2.13-${KAFKA_VERSION}.tgz

# Download and install JMX Exporter
wget https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.17.2/jmx_prometheus_javaagent-0.17.2.jar -O /opt/kafka/jmx_prometheus_javaagent.jar

# Create JMX Exporter config
cat > /opt/kafka/jmx-config.yml << EOF
lowercaseOutputName: true
lowercaseOutputLabelNames: true
rules:
  - pattern: kafka.server<type=(.+), name=(.+), clientId=(.+), topic=(.+), partition=(.*)><>Value
    name: kafka_server_\$1_\$2
    type: GAUGE
    labels:
      clientId: "\$3"
      topic: "\$4"
      partition: "\$5"
  - pattern: kafka.server<type=(.+), name=(.+), clientId=(.+), brokerHost=(.+), brokerPort=(.+), topic=(.+), partition=(.*)><>Value
    name: kafka_server_\$1_\$2
    type: GAUGE
    labels:
      clientId: "\$3"
      broker: "\$4:\$5"
      topic: "\$6"
      partition: "\$7"
  - pattern: kafka.server<type=(.+), name=(.+), clientId=(.+), topic=(.+), partition=(.*)><>Count
    name: kafka_server_\$1_\$2_count
    type: COUNTER
    labels:
      clientId: "\$3"
      topic: "\$4"
      partition: "\$5"
EOF

# Create Kafka systemd service
cat > /etc/systemd/system/kafka.service << EOF
[Unit]
Description=Apache Kafka
After=network.target

[Service]
Type=simple
User=kafka
Group=kafka
Environment=KAFKA_HEAP_OPTS="-Xmx1G -Xms1G"
Environment=KAFKA_OPTS="-javaagent:/opt/kafka/jmx_prometheus_javaagent.jar=8080:/opt/kafka/jmx-config.yml"
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Configure Kafka
cat > /opt/kafka/config/server.properties << EOF
# Broker ID
broker.id=${BROKER_ID}

# Network settings
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://${INSTANCE_NAME}:9092

# Log settings
log.dirs=/var/lib/kafka/data
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000

# Zookeeper settings
zookeeper.connect=localhost:2181

# Topic defaults
num.partitions=${DEFAULT_PARTITIONS}
default.replication.factor=${DEFAULT_REPLICATION_FACTOR}
min.insync.replicas=${MIN_INSYNC_REPLICAS}

# Performance tuning
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
num.partitions=${DEFAULT_PARTITIONS}
num.recovery.threads.per.data.dir=1
log.flush.interval.messages=10000
log.flush.interval.ms=1000
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connection.timeout.ms=18000
EOF

# Set permissions
chown -R kafka:kafka /opt/kafka /var/lib/kafka /var/log/kafka

# Enable and start Kafka service
systemctl daemon-reload
systemctl enable kafka
systemctl start kafka

# Wait for Kafka to start
sleep 30

# Create topics if this is the first broker
if [ "$BROKER_ID" = "0" ]; then
    # Wait for all brokers to be available
    sleep 60
    
    # Create system topics with proper replication factor
    /opt/kafka/bin/kafka-topics.sh --create \
        --bootstrap-server localhost:9092 \
        --topic __consumer_offsets \
        --partitions 50 \
        --replication-factor ${DEFAULT_REPLICATION_FACTOR} \
        --config cleanup.policy=compact \
        --config min.insync.replicas=${MIN_INSYNC_REPLICAS}
fi 