# Kafka on GCP - Complete Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [CLI Commands Reference](#cli-commands-reference)
   - [start](#start-command)
   - [profiles](#profiles-command)
   - [health](#health-command)
   - [addons](#addons-command)
   - [terraform](#terraform-command)
6. [Configuration Options](#configuration-options)
   - [GCP Configuration](#gcp-configuration)
   - [Kafka Configuration](#kafka-configuration)
   - [Networking Configuration](#networking-configuration)
   - [Security Configuration](#security-configuration)
7. [Terraform Infrastructure](#terraform-infrastructure)
8. [Add-ons](#add-ons)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)
11. [Development Guide](#development-guide)

## Introduction

**kafka-cli** is an interactive command-line tool designed to simplify the provisioning and management of Apache Kafka clusters on Google Cloud Platform (GCP). It provides a step-by-step wizard interface for configuration, automated infrastructure provisioning using Terraform, and various management capabilities.

### Key Features

- ⚡️ **Interactive Wizard**: User-friendly setup process with step-by-step guidance
- 🏗 **Automated Infrastructure Provisioning**: Uses Terraform to manage cloud resources
- 🌐 **Dynamic Networking**: Custom VPC configurations and security integrations
- ➕ **Addon Marketplace**: Deploy optional components like Kafka UI, monitoring tools, and more
- ☁️ **Flexible Deployment**: Deploy to GCP infrastructure
- 💾 **Profiles & Configuration Management**: Save and reuse cluster configurations
- 🧪 **Dry-Run Mode**: Preview infrastructure changes without applying them
- 🩺 **Health Checks**: Built-in diagnostics for cluster resources
- 🔧 **Custom Helm Values Support**: Override default configurations
- 🚀 **CLI Auto-Updater**: Keep the tool up-to-date automatically

## Architecture Overview

The kafka-cli tool creates a Kafka cluster on GCP with the following components:

- **Kafka Brokers**: A configurable number of Kafka broker instances running in GCE VMs
- **KRaft Mode**: Modern Kafka deployment without ZooKeeper (available in Kafka 3.x+)
- **Custom VPC Network**: Isolated network environment for security
- **Firewall Rules**: Preconfigured security rules for Kafka communication
- **Add-on Components**: Optional monitoring, management, and connectivity tools

### High-Level Design

```
                           +---------------------+
                           |                     |
                           |    Kafka CLI Tool   |
                           |                     |
                           +----------+----------+
                                      |
                                      | Generates & Applies
                                      v
                           +----------+----------+
                           |                     |
                           |  Terraform Configs  |
                           |                     |
                           +----------+----------+
                                      |
                                      | Provisions
                                      v
                     +----------------+----------------+
                     |                                 |
          +----------+----------+        +------------+------------+
          |                     |        |                         |
          |    GCP Network      |        |   GCE Instances         |
          |    Infrastructure   |        |   (Kafka Brokers)       |
          |                     |        |                         |
          +---------------------+        +-------------------------+
```

## Installation

### Prerequisites

- Python 3.11+
- pip (Python package manager)
- Google Cloud SDK (gcloud CLI)
- Terraform 1.0+
- GCP account with appropriate permissions

### Installation Methods

**Via pip (Recommended)**:

```bash
pip install kafka-cli
```

**Development Installation**:

```bash
# Clone the repository
git clone https://github.com/your-username/kafka-cli.git
cd kafka-cli

# Install in development mode
pip install -e .
```

### GCP Authentication

Before using the tool, you need to authenticate with GCP:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Quick Start

### Interactive Wizard

Launch the interactive configuration wizard:

```bash
kafka-cli start
```

The wizard will guide you through:
1. GCP configuration (project, region, zone)
2. Terraform backend setup (for state storage)
3. Kafka cluster configuration (version, size, resources)
4. Networking setup
5. Security options
6. Add-ons selection

### Non-interactive Mode

For automation purposes, you can use non-interactive mode:

```bash
kafka-cli start --non-interactive \
  --project-id=my-project \
  --region=us-central1 \
  --broker-count=3 \
  --broker-machine-type=e2-standard-4 \
  --save-as-profile=my-cluster
```

### Using Profiles

```bash
# Create and save a new deployment as a profile
kafka-cli start --save-as-profile=my-cluster

# Use an existing profile
kafka-cli start --profile=my-cluster

# List available profiles
kafka-cli profiles list
```

## CLI Commands Reference

### Start Command

The `start` command initiates the interactive wizard or non-interactive deployment:

```bash
kafka-cli start [OPTIONS]
```

**Options**:
- `--profile, -p TEXT`: Use a specific profile
- `--dry-run`: Preview changes without applying them
- `--non-interactive, -n`: Run in non-interactive mode (requires parameters)
- `--project-id TEXT`: GCP Project ID
- `--region TEXT`: GCP Region (default: us-central1)
- `--zone TEXT`: GCP Zone (defaults to {region}-a)
- `--network-range TEXT`: Network CIDR range (default: 10.0.0.0/16)
- `--broker-count INTEGER`: Number of Kafka brokers (default: 3)
- `--broker-machine-type TEXT`: GCP machine type for brokers (default: e2-standard-2)
- `--enable-monitoring/--disable-monitoring`: Enable/disable monitoring add-on
- `--enable-connect/--disable-connect`: Enable/disable Kafka Connect add-on
- `--auto-apply`: Automatically apply the configuration
- `--save-as-profile TEXT`: Save configuration as a profile

### Profiles Command

Manage saved cluster configurations:

```bash
kafka-cli profiles [COMMAND]
```

**Subcommands**:
- `list`: List all saved profiles
- `show`: Show details of a specific profile
- `delete`: Delete a saved profile
- `export`: Export a profile to a YAML file
- `import`: Import a profile from a YAML file

### Health Command

Check the health and status of deployed clusters:

```bash
kafka-cli health [COMMAND]
```

**Subcommands**:
- `check`: Run health checks on a cluster
- `status`: Get cluster status information
- `diagnostics`: Generate diagnostic information

### Addons Command

Manage add-on components for your Kafka clusters:

```bash
kafka-cli addons [COMMAND]
```

**Subcommands**:
- `list`: List available add-ons
- `install`: Install an add-on to a cluster
- `uninstall`: Remove an add-on from a cluster
- `update`: Update an installed add-on

### Terraform Command

Direct access to Terraform operations:

```bash
kafka-cli terraform [COMMAND]
```

**Subcommands**:
- `plan`: Generate and show an execution plan
- `apply`: Apply the changes required to reach the desired state
- `destroy`: Destroy the Terraform-managed infrastructure
- `output`: Show output values from your Terraform state

## Configuration Options

### GCP Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `project_id` | GCP Project ID | - |
| `region` | GCP Region | us-central1 |
| `zone` | GCP Zone | {region}-a |

### Kafka Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `version` | Kafka Version | 3.5.0 |
| `broker_count` | Number of Kafka brokers | 3 |
| `machine_type` | GCP machine type | e2-standard-4 |
| `disk_size_gb` | Disk size in GB | 100 |
| `default_partitions` | Default partitions per topic | 3 |
| `default_replication_factor` | Default replication factor | 3 |
| `min_insync_replicas` | Minimum in-sync replicas | 2 |

### Networking Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `network_range` | VPC network range (CIDR) | 10.0.0.0/16 |
| `subnet_cidr` | Subnet CIDR range | 10.0.0.0/24 |
| `create_nat_gateway` | Create Cloud NAT gateway | true |
| `create_bastion` | Create a bastion host | true |

### Security Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `auth_method` | Authentication method | none |
| `enable_encryption` | Enable TLS encryption | false |
| `enable_acls` | Enable Kafka ACLs | false |

## Terraform Infrastructure

The kafka-cli tool generates and manages Terraform configurations that provision the following infrastructure:

### Network Resources
- VPC network
- Subnet
- Firewall rules for Kafka traffic
- [Optional] Cloud NAT for outbound connectivity
- [Optional] Bastion host for secure access

### Compute Resources
- Kafka broker instances (GCE VMs)
- Static internal IP addresses for brokers
- Boot disks with appropriate size

### Configurations
- Systemd service for Kafka
- KRaft mode configuration (for Kafka 3.x+)
- Network listener and protocol configurations
- Disk and file system configurations

## Add-ons

The tool supports several add-ons that can enhance your Kafka deployment:

| Add-on | Description |
|--------|-------------|
| Monitoring | Prometheus and Grafana for metrics collection and visualization |
| Kafka Connect | Data integration framework for streaming data between systems |
| Schema Registry | Centralized schema management for Kafka messages |
| Kafka UI | Web interface for managing and monitoring Kafka |
| REST Proxy | HTTP interface to Kafka cluster |

## Troubleshooting

### Common Issues

**GCP Authentication Errors**:
- Ensure you're authenticated with `gcloud auth login`
- Verify project permissions with `gcloud projects get-iam-policy PROJECT_ID`

**Terraform Errors**:
- Check the Terraform state in `.terraform` directory
- Use `kafka-cli terraform plan` to debug configuration issues

**Kafka Connection Issues**:
- Verify firewall rules with `gcloud compute firewall-rules list`
- Check broker status with `kafka-cli health status`

### Diagnostic Commands

```bash
# Run full diagnostics
kafka-cli health diagnostics --profile=my-cluster

# Check specific component
kafka-cli health check --component=brokers --profile=my-cluster
```

## Advanced Usage

### Custom Terraform Variables

You can customize the Terraform variables by creating a `terraform.tfvars` file in your working directory:

```hcl
# terraform.tfvars
project_id = "my-project"
region = "us-west1"
kafka_broker_count = 5
machine_type = "n2-standard-8"
```

### Remote State Management

Set up remote state storage for collaborative use:

```bash
kafka-cli terraform init \
  --backend-config="bucket=my-terraform-state" \
  --backend-config="prefix=kafka/prod"
```

### Automation Integration

The tool can be integrated into CI/CD pipelines using the non-interactive mode:

```bash
# Example CI/CD script
kafka-cli start --non-interactive \
  --project-id=${PROJECT_ID} \
  --region=${REGION} \
  --broker-count=${BROKER_COUNT} \
  --auto-apply
```

## Development Guide

### Project Structure

```
kafka-cli/
├── kafka_cli/             # Main package
│   ├── __init__.py
│   ├── main.py            # CLI entry point
│   ├── commands/          # CLI commands implementation
│   ├── addons/            # Add-on functionality
│   ├── templates/         # Template files
│   ├── terraform/         # Terraform wrapper functionality
│   └── utils/             # Utility functions
├── infra/                 # Terraform configuration files
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── apply_terraform.sh
├── tests/                 # Test cases
├── pyproject.toml         # Project metadata
└── README.md              # Project README
```

### Setting up a Development Environment

```bash
# Clone the repository
git clone https://github.com/your-username/kafka-cli.git
cd kafka-cli

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_terraform.py
```

### Code Style and Linting

The project follows these code style guidelines:
- Black for code formatting (line length 88)
- isort for import sorting
- flake8 for linting
- mypy for type checking

```bash
# Format code
black kafka_cli tests

# Sort imports
isort kafka_cli tests

# Run linting
flake8 kafka_cli tests

# Run type checking
mypy kafka_cli
```
