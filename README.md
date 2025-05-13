# Kafka-CLI

Interactive command-line tool for provisioning and managing Kafka clusters on GCP.

## Features

- ⚡️ **Interactive Wizard**: Step-by-step guided configuration of Kafka clusters
- 🏗 **Automated Infrastructure Provisioning**: Uses Terraform to provision cloud resources
- 🌐 **Dynamic Networking**: Custom VPC configurations and security integrations
- ➕ **Addon Marketplace**: Seamless deployment of optional tools (Kafka UI, Prometheus, etc.)
- ☁️ **Flexible Deployment Targets**: Deploy to GCP or existing Kubernetes clusters
- 💾 **Profiles & Configuration Management**: Save and reuse cluster configurations
- 🧪 **Dry-Run Mode**: Preview infrastructure changes safely
- 🩺 **Health Checks**: Built-in commands to verify status of resources
- 🔧 **Custom Helm Values Support**: Override default configurations
- 🚀 **CLI Auto-Updater**: Keep your tool up-to-date

## Installation

```bash
# Install from PyPI
pip install kafka-cli

# Or install in development mode
git clone https://github.com/your-username/kafka-cli.git
cd kafka-cli
pip install -e .
```

## Quick Start

```bash
# Start the interactive wizard
kafka-cli start

# List available profiles
kafka-cli profiles list

# Check cluster health
kafka-cli health check --profile my-cluster
```

## Requirements

- Python 3.11+
- Terraform 1.0+
- GCP account with appropriate permissions
- kubectl (for Kubernetes deployments)

## Documentation

For detailed documentation, see [docs/](docs/).

## License

MIT
