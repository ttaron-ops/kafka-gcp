#!/bin/bash
set -e

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "Terraform is not installed. Please install it first."
    exit 1
fi

# Check if gcloud is configured
if ! command -v gcloud &> /dev/null; then
    echo "gcloud is not installed. Please install it first."
    exit 1
fi

# Function to read user input with default value
read_input() {
    local prompt="$1"
    local default="$2"
    local input
    
    if [ -n "$default" ]; then
        prompt="$prompt [$default]"
    fi
    
    read -p "$prompt: " input
    
    if [ -z "$input" ] && [ -n "$default" ]; then
        echo "$default"
    else
        echo "$input"
    fi
}

echo "Kafka GCP Terraform Configuration Generator"
echo "==========================================="
echo "This script will help you generate a terraform.tfvars file and apply the Terraform configuration."
echo

# Read GCP project settings
PROJECT_ID=$(read_input "GCP Project ID" "")
PROJECT_NAME=$(read_input "GCP Project Name" "$PROJECT_ID")
REGION=$(read_input "GCP Region" "us-west1")
ZONE=$(read_input "GCP Zone" "us-west1-a")
RESOURCE_PREFIX=$(read_input "Resource prefix" "kafka")

# Read feature flags
VPC_ENABLED=$(read_input "Enable VPC creation? (y/n)" "y")
VPC_ENABLED=$( [ "$VPC_ENABLED" = "y" ] && echo "true" || echo "false" )

KEYRING_ENABLED=$(read_input "Enable Keyring creation? (y/n)" "n")
KEYRING_ENABLED=$( [ "$KEYRING_ENABLED" = "y" ] && echo "true" || echo "false" )

VPC_PEERING_ENABLED=$(read_input "Enable VPC Peering? (y/n)" "n")
VPC_PEERING_ENABLED=$( [ "$VPC_PEERING_ENABLED" = "y" ] && echo "true" || echo "false" )

KAFKA_UI_ENABLED=$(read_input "Enable Kafka UI? (y/n)" "n")
KAFKA_UI_ENABLED=$( [ "$KAFKA_UI_ENABLED" = "y" ] && echo "true" || echo "false" )

# Read VPC settings if enabled
if [ "$VPC_ENABLED" = "true" ]; then
    VPC_NAME=$(read_input "VPC Name" "application-vpc")
    SUBNET_CIDR=$(read_input "Subnet CIDR" "10.0.0.0/24")
fi

# Read instance settings
INSTANCE_COUNT=$(read_input "Number of instances" "1")
MACHINE_TYPE=$(read_input "Machine type" "e2-medium")
DISK_IMAGE=$(read_input "Disk image" "debian-cloud/debian-11")
DISK_SIZE_GB=$(read_input "Disk size in GB" "50")
KAFKA_BROKER_COUNT=$(read_input "Number of Kafka brokers" "3")

# Read Kafka settings
KAFKA_VERSION=$(read_input "Kafka version" "3.6.0")
DEFAULT_PARTITIONS=$(read_input "Default partitions" "3")
DEFAULT_REPLICATION_FACTOR=$(read_input "Default replication factor" "3")
MIN_INSYNC_REPLICAS=$(read_input "Minimum in-sync replicas" "2")

# Read SSH settings
SSH_USER=$(read_input "SSH username" "kafka")

# Get public SSH key
if [ -f ~/.ssh/id_rsa.pub ]; then
    DEFAULT_SSH_KEY=$(cat ~/.ssh/id_rsa.pub)
else
    DEFAULT_SSH_KEY=""
fi

SSH_PUB_KEY=$(read_input "SSH public key" "$DEFAULT_SSH_KEY")

# Generate terraform.tfvars file
cat > terraform.tfvars <<EOF
# GCP Project settings
project_id      = "$PROJECT_ID"
project_name    = "$PROJECT_NAME"
region          = "$REGION"
zone            = "$ZONE"
resource_prefix = "$RESOURCE_PREFIX"

# Feature flags
vpc_enabled         = $VPC_ENABLED
keyring_enabled     = $KEYRING_ENABLED
vpc_peering_enabled = $VPC_PEERING_ENABLED
kafka_ui_enabled    = $KAFKA_UI_ENABLED

# VPC settings
vpc_name     = "$VPC_NAME"
subnet_cidr  = "$SUBNET_CIDR"

# Instance settings
instance_count      = $INSTANCE_COUNT
machine_type        = "$MACHINE_TYPE"
disk_image          = "$DISK_IMAGE"
disk_size_gb        = $DISK_SIZE_GB
kafka_broker_count  = $KAFKA_BROKER_COUNT

# Kafka settings
kafka_version              = "$KAFKA_VERSION"
default_partitions         = $DEFAULT_PARTITIONS
default_replication_factor = $DEFAULT_REPLICATION_FACTOR
min_insync_replicas       = $MIN_INSYNC_REPLICAS

# SSH settings
ssh_user    = "$SSH_USER"
ssh_pub_key = "$SSH_PUB_KEY"
EOF

echo
echo "Generated terraform.tfvars file:"
echo "--------------------------------"
cat terraform.tfvars
echo "--------------------------------"
echo

# Initialize Terraform
echo "Initializing Terraform..."
terraform init

# Generate and show the plan
echo "Generating Terraform plan..."
terraform plan -out=terraform.plan

# Ask for confirmation before applying
read -p "Do you want to apply the Terraform plan? (y/n): " apply_confirmation

if [ "$apply_confirmation" == "y" ] || [ "$apply_confirmation" == "Y" ]; then
    echo "Applying Terraform plan..."
    terraform apply terraform.plan
    
    echo
    echo "Terraform apply completed."
    echo "Kafka cluster outputs:"
    terraform output
else
    echo "Terraform apply was cancelled."
fi
