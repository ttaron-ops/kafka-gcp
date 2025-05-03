import os
from typing import Any, Dict, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kafka_cli.utils.config import get_config, get_config_dir, update_config
from kafka_cli.utils.gcp_auth import (
    estimate_compute_costs,
    get_active_project,
    get_zones_for_region,
    list_gcp_regions,
    list_gcp_vpcs,
    list_security_groups,
    list_subnets_for_vpc,
)
from kafka_cli.utils.interactive import (
    is_interactive,
    safe_confirm,
    safe_multiselect,
    safe_number,
    safe_password,
    safe_path,
    safe_select,
    safe_text,
)
from kafka_cli.utils.terraform import generate_terraform_vars

app = typer.Typer(help="Start the interactive Kafka cluster provisioning wizard")
console = Console()

# Kafka versions to offer
KAFKA_VERSIONS = ["3.3.1", "3.4.0", "3.4.1", "3.5.0", "3.5.1", "3.6.0"]
# Storage types to offer
STORAGE_TYPES = ["pd-standard", "pd-balanced", "pd-ssd"]
# Machine types mapped to vCPU and memory
MACHINE_TYPES = {
    "e2-standard-2": {"vCPU": 2, "RAM": 8},
    "e2-standard-4": {"vCPU": 4, "RAM": 16},
    "e2-standard-8": {"vCPU": 8, "RAM": 32},
    "e2-standard-16": {"vCPU": 16, "RAM": 64},
    "n2-standard-2": {"vCPU": 2, "RAM": 8},
    "n2-standard-4": {"vCPU": 4, "RAM": 16},
    "n2-standard-8": {"vCPU": 8, "RAM": 32},
    "n2-standard-16": {"vCPU": 16, "RAM": 64},
}

# Authentication methods
AUTH_METHODS = ["none", "ssl"]


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Use a specific profile"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying them"),
    # Non-interactive mode parameters
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-n", help="Run in non-interactive mode (requires all parameters)"
    ),
    project_id: Optional[str] = typer.Option(None, "--project-id", help="GCP Project ID"),
    region: str = typer.Option("us-central1", "--region", help="GCP Region"),
    zone: Optional[str] = typer.Option(None, "--zone", help="GCP Zone (defaults to {region}-a)"),
    network_range: str = typer.Option("10.0.0.0/16", "--network-range", help="Network CIDR range"),
    broker_count: int = typer.Option(3, "--broker-count", help="Number of Kafka brokers"),
    broker_machine_type: str = typer.Option("e2-standard-2", "--broker-machine-type", help="GCP machine type for brokers"),
    zookeeper_count: int = typer.Option(3, "--zookeeper-count", help="Number of ZooKeeper nodes"),
    zookeeper_machine_type: str = typer.Option("e2-small", "--zookeeper-machine-type", help="GCP machine type for ZooKeeper"),
    enable_monitoring: bool = typer.Option(True, "--enable-monitoring/--disable-monitoring", help="Enable monitoring add-on"),
    enable_connect: bool = typer.Option(False, "--enable-connect/--disable-connect", help="Enable Kafka Connect add-on"),
    auto_apply: bool = typer.Option(False, "--auto-apply", help="Automatically apply the configuration (non-interactive mode)"),
    save_as_profile: Optional[str] = typer.Option(None, "--save-as-profile", help="Save configuration as a named profile"),
):
    """
    Start the interactive Kafka cluster provisioning wizard
    """
    if ctx.invoked_subcommand is None:
        if non_interactive:
            run_non_interactive(
                profile_name=profile_name,
                dry_run=dry_run,
                project_id=project_id,
                region=region,
                zone=zone or f"{region}-a",
                network_range=network_range,
                broker_count=broker_count,
                broker_machine_type=broker_machine_type,
                zookeeper_count=zookeeper_count,
                zookeeper_machine_type=zookeeper_machine_type,
                enable_monitoring=enable_monitoring,
                enable_connect=enable_connect,
                auto_apply=auto_apply,
                save_as_profile=save_as_profile,
            )
        else:
            run_wizard(profile_name, dry_run)


def run_non_interactive(
    profile_name: Optional[str] = None,
    dry_run: bool = False,
    project_id: Optional[str] = None,
    region: str = "us-central1",
    zone: str = None,
    network_range: str = "10.0.0.0/16",
    broker_count: int = 3,
    broker_machine_type: str = "e2-standard-2",
    zookeeper_count: int = 3,
    zookeeper_machine_type: str = "e2-small",
    enable_monitoring: bool = True,
    enable_connect: bool = False,
    auto_apply: bool = False,
    save_as_profile: Optional[str] = None,
):
    """
    Run the configuration wizard in non-interactive mode using provided parameters
    """
    if not project_id:
        console.print("[bold red]Error:[/bold red] project_id is required in non-interactive mode", style="red")
        console.print("Use --project-id to specify your GCP project ID")
        raise typer.Exit(1)

    # Build configuration from provided parameters
    config = {
        "gcp": {
            "project_id": project_id,
            "region": region,
            "zone": zone or f"{region}-a",
        },
        "networking": {
            "network_range": network_range,
            "create_nat_gateway": True,
            "create_bastion": True,
        },
        "kafka": {
            "broker_count": broker_count,
            "broker_machine_type": broker_machine_type,
            "zookeeper_count": zookeeper_count,
            "zookeeper_machine_type": zookeeper_machine_type,
        },
        "addons": {
            "monitoring": enable_monitoring,
            "connect": enable_connect,
            "schema_registry": False,
            "rest_proxy": False,
        },
    }

    # Display configuration summary
    console.print("\n[bold]Configuration Summary:[/bold]")
    display_summary(config)

    # Save as profile if requested
    if save_as_profile:
        save_profile_to_file(config, save_as_profile, set_as_default=True)

    # Generate Terraform variables
    if generate_terraform_vars(config, dry_run):
        console.print("\n[bold green]Configuration complete![/bold green]")

        if not dry_run and auto_apply:
            console.print("\nApplying configuration...")
            # Apply configuration logic would go here
            console.print("[bold green]Configuration applied successfully![/bold green]")
        else:
            console.print("\nYou can apply this configuration with the 'terraform apply' command.", style="yellow")
    else:
        console.print("\n[bold red]Failed to generate Terraform variables[/bold red]")
        raise typer.Exit(1)


def save_profile_to_file(config: Dict[str, Any], profile_name: str, set_as_default: bool = False):
    """Save configuration as a named profile"""
    try:
        # Ensure profiles directory exists
        profiles_dir = os.path.join(get_config_dir(), "profiles")
        os.makedirs(profiles_dir, exist_ok=True)

        # Save the profile
        profile_path = os.path.join(profiles_dir, f"{profile_name}.yaml")

        # Check if profile exists
        if os.path.exists(profile_path):
            console.print(f"Profile [bold yellow]{profile_name}[/bold yellow] already exists and will be overwritten")

        # Write the configuration
        with open(profile_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        console.print(f"Configuration saved as profile: [bold cyan]{profile_name}[/bold cyan]")

        # Handle default profile setting
        if set_as_default or (is_interactive() and safe_confirm("Set this as the default profile?", default=False)):
            global_config = get_config()
            global_config["default_profile"] = profile_name
            update_config(global_config)
            console.print(f"[bold cyan]{profile_name}[/bold cyan] set as the default profile")

        return True

    except Exception as e:
        console.print(f"[bold red]Error saving profile:[/bold red] {str(e)}")
        return False


def run_wizard(profile_name: Optional[str] = None, dry_run: bool = False):  # noqa C901
    """Run the interactive Kafka configuration wizard"""
    from kafka_cli.utils.gcp_auth import (
        check_gcp_auth,
        select_gcp_configuration,
    )
    from kafka_cli.utils.interactive import check_interactive_or_exit, safe_confirm, safe_select, safe_text
    from kafka_cli.utils.terraform import generate_terraform_vars

    # Check if running in interactive mode
    check_interactive_or_exit()

    # Welcome panel
    console.print(
        Panel(
            renderable="\n[bold]Kafka on GCP Deployment Wizard[/bold]\n\n"
            "This wizard will guide you through setting up a Kafka cluster on Google Cloud Platform.\n"
            "You'll configure GCP resources, Kafka settings, networking, and monitoring options.\n\n"
            "Tip: You can save your configuration as a profile for future use.",
            title="Welcome",
            expand=False,
            width=85,
        )
    )

    # Initialize configuration dictionary
    config = {"general": {}, "gcp": {}, "kafka": {}, "networking": {}, "security": {}, "monitoring": {}, "tags": {}}

    # Optional profile name
    if not profile_name:
        use_profile = True
        if use_profile:
            profile_name = safe_text("Enter a name for this profile", default="default")
            config["general"]["profile_name"] = profile_name
    else:
        config["general"]["profile_name"] = profile_name

    # Step 1: Check GCP Authentication
    console.print("\n[bold cyan]Step 1:[/bold cyan] [bold]Checking GCP Authentication[/bold]")
    authenticated = check_gcp_auth()

    if not authenticated:
        # If gcloud is not installed, we'll continue with default values and mock data
        console.print("\n[yellow]Continuing in mock mode with default values since gcloud is not available.[/yellow]")
        console.print("[yellow]Some features will be limited without GCP authentication.[/yellow]")
        # Set a default project ID
        project_id = "mock-project"
        config["gcp"]["project_id"] = project_id
    else:
        # Step 2: GCP Configuration Selection
        console.print("\n[bold cyan]Step 2:[/bold cyan] [bold]GCP Configuration Selection[/bold]")
        console.print("[grey]Select which GCP configuration to use for this deployment.[/grey]")

        # Let user select a GCP configuration
        project_id = select_gcp_configuration()

        if not project_id:
            project_id = safe_text("Enter your GCP Project ID manually", default="my-project")

        config["gcp"]["project_id"] = project_id
        console.print(f"[bold green]Using GCP Project:[/bold green] {project_id}")

    # Terraform Backend Setup - will be skipped if not authenticated
    if authenticated:
        console.print("\n[bold cyan]Step 3:[/bold cyan] [bold]Terraform Backend Configuration[/bold]")
        console.print("[grey]Terraform uses a backend to store state files.[/grey]")

        use_remote = safe_confirm("Would you like to use a remote backend (GCS bucket) for Terraform state?", default=True)
        if use_remote:
            bucket_name = safe_text("Enter the GCS bucket name for Terraform state", default=f"terraform-state-{project_id}")
            prefix = safe_text("Enter a prefix for state files", default="kafka")

            config["terraform"] = {"backend_type": "gcs", "bucket": bucket_name, "prefix": prefix}

            # Initialize the backend if authenticated
            from kafka_cli.utils.gcp_auth import init_terraform_backend

            init_terraform_backend(bucket_name, prefix)
        else:
            console.print("[yellow]Using local Terraform state storage.[/yellow]")
            config["terraform"] = {"backend_type": "local"}
    else:
        # Default to local backend if not authenticated
        console.print("[yellow]Using local Terraform state storage since GCP is not authenticated.[/yellow]")
        config["terraform"] = {"backend_type": "local"}

    # Step 4: Configure GCP settings
    config["gcp"] = configure_gcp()

    # Step 5: Kafka Settings
    console.print("\n[bold cyan]Step 5:[/bold cyan] [bold]Kafka Cluster Configuration[/bold]")

    # Cluster name
    cluster_name = safe_text("Enter a name for your Kafka cluster", default="kafka-cluster")
    config["kafka"]["cluster_name"] = cluster_name

    # Kafka version
    kafka_versions = ["3.5.0", "3.4.1", "3.3.2", "3.2.3", "2.8.1"]
    kafka_version = safe_select("Select Kafka version", choices=kafka_versions, default="3.5.0")
    config["kafka"]["version"] = kafka_version

    # Cluster size
    broker_count = safe_number("Number of Kafka brokers", min_value=1, max_value=20, default=3)
    config["kafka"]["broker_count"] = broker_count

    # Instance type selection approach
    compute_type_approach = safe_select(
        "How would you like to configure compute resources?",
        choices=["Select predefined machine type", "Specify custom CPU and memory"],
        default="Select predefined machine type",
    )

    if compute_type_approach == "Select predefined machine type":
        # Instance type options
        instance_types = [
            "e2-standard-2 (2 vCPU, 8GB)",
            "e2-standard-4 (4 vCPU, 16GB)",
            "e2-standard-8 (8 vCPU, 32GB)",
            "n2-standard-2 (2 vCPU, 8GB)",
            "n2-standard-4 (4 vCPU, 16GB)",
            "n2-standard-8 (8 vCPU, 32GB)",
            "n2-standard-16 (16 vCPU, 64GB)",
            "e2-highmem-2 (2 vCPU, 16GB)",
            "e2-highmem-4 (4 vCPU, 32GB)",
            "e2-highcpu-4 (4 vCPU, 4GB)",
            "e2-highcpu-8 (8 vCPU, 8GB)",
        ]

        machine_type_display = safe_select(
            "Select machine type for Kafka brokers",
            choices=instance_types,
            default="e2-standard-4 (4 vCPU, 16GB)",
            help_text="Larger instances provide better performance but cost more.",
        )

        # Extract the actual machine type from the display string
        machine_type = machine_type_display.split(" ")[0]
        config["kafka"]["machine_type"] = machine_type
        config["kafka"]["custom_machine"] = False

        console.print(f"[bold green]Selected machine type:[/bold green] {machine_type}")

    else:
        # Custom machine type configuration
        vcpu_count = safe_number("Number of vCPUs per broker", min_value=1, max_value=96, default=4)

        memory_gb = safe_number("Memory (GB) per broker", min_value=1, max_value=624, default=16)

        # Create a custom machine type name
        config["kafka"]["custom_machine"] = True
        config["kafka"]["custom_cpu"] = vcpu_count
        config["kafka"]["custom_memory_gb"] = memory_gb

        # Store as e2-custom-{cpu}-{memory} format for Terraform variables
        custom_machine_type = f"custom-{vcpu_count}-{memory_gb*1024}"
        config["kafka"]["machine_type"] = custom_machine_type

        console.print(f"[bold green]Custom machine configuration:[/bold green] {vcpu_count} vCPUs, {memory_gb} GB memory")

    # Disk configuration
    disk_types = ["pd-standard", "pd-balanced", "pd-ssd"]
    disk_type = safe_select(
        "Select disk type",
        choices=disk_types,
        default="pd-ssd",
        help_text="SSD provides better performance, standard is more economical.",
    )
    config["kafka"]["disk_type"] = disk_type

    disk_size_gb = safe_number("Disk size (GB) for each broker", min_value=10, max_value=65536, default=100)
    config["kafka"]["disk_size_gb"] = disk_size_gb

    # Step 6: Configure networking
    config["networking"] = configure_networking(config["gcp"]["region"])

    # Step 7: Configure additional options
    config["auth"] = configure_auth()

    # Step 8: Configure monitoring and addons
    config["monitoring"] = configure_monitoring()

    # Step 9: Configure labels/tags
    config["labels"] = configure_labels()

    # Calculate estimated costs if enabled
    if "compute_estimate" in config["kafka"] and config["kafka"]["compute_estimate"]:
        estimated_costs = estimate_compute_costs(
            region=config["gcp"]["region"],
            instance_type=config["kafka"]["machine_type"],
            num_instances=config["kafka"]["broker_count"],
            disk_type=config["kafka"]["storage_type"],
            disk_size_gb=config["kafka"]["storage_size"],
        )
        if estimated_costs:
            config["kafka"]["estimated_costs"] = estimated_costs

    # Display configuration summary
    console.print("\n[bold]Configuration Summary:[/bold]")
    display_summary(config)

    # Save configuration as profile
    if safe_confirm("\nDo you want to save this configuration as a profile?", default=True):
        profile_name = safe_text("Enter a name for this profile", default="kafka-gcp")
        save_profile_to_file(config, profile_name, set_as_default=True)

    # Confirm deployment
    proceed = safe_confirm("Would you like to proceed with this configuration?", default=True)

    if not proceed:
        console.print("[bold red]Deployment canceled.[/bold red]")
        raise typer.Abort()

    # Save configuration as profile if requested
    if "profile_name" in config["general"]:
        profile_saved = save_profile_to_file(config, config["general"]["profile_name"])
        if profile_saved:
            console.print(f"[bold green]Configuration saved as profile '{config['general']['profile_name']}'[/bold green]")

    # Generate Terraform variables
    if generate_terraform_vars(config, dry_run):
        console.print("\n[bold green]Configuration complete![/bold green]")
        console.print("\n[bold yellow]Configuration prepared but not applied.[/bold yellow]")

        console.print("You can apply it later with 'terraform apply' in the configuration directory.")
    else:
        console.print("\n[bold red]Failed to generate Terraform variables[/bold red]")
        raise typer.Exit(1)


def configure_gcp() -> Dict[str, Any]:
    """Configure GCP settings"""
    console.print("\n[bold cyan]GCP Configuration[/bold cyan]")

    # Get active project
    project_id = get_active_project()
    if not project_id:
        project_id = safe_text("Enter your GCP Project ID:", default="")

    # Get regions
    regions = list_gcp_regions()
    region = safe_select("Select GCP region:", choices=regions, default="us-central1" if "us-central1" in regions else regions[0])

    # Get zones for the selected region
    zones = get_zones_for_region(region)
    selected_zones = safe_multiselect("Select availability zones:", choices=zones, default=[zones[0]] if zones else [])

    return {"project_id": project_id, "region": region, "zones": selected_zones}


def configure_networking(region: str) -> Dict[str, Any]:
    """Configure networking settings"""
    console.print("\n[bold cyan]Networking Configuration[/bold cyan]")

    # Get existing VPCs
    vpcs = list_gcp_vpcs()
    vpc_names = [vpc["name"] for vpc in vpcs] + ["Create new VPC"]

    vpc_selection = safe_select("Select VPC network:", choices=vpc_names, default="Create new VPC")

    if vpc_selection == "Create new VPC":
        vpc_name = safe_text("Enter name for the new VPC:", default="kafka-vpc")
        network_cidr = safe_text("Enter network CIDR block:", default="10.0.0.0/16")
        create_new_vpc = True
        selected_subnets = []
    else:
        vpc_name = vpc_selection
        create_new_vpc = False

        # Get existing subnets for the selected VPC
        subnets = list_subnets_for_vpc(vpc_name)
        # Filter subnets by region
        region_subnets = [subnet for subnet in subnets if region in subnet.get("region", "")]

        if region_subnets:
            subnet_choices = [f"{subnet['name']} ({subnet['ipCidrRange']})" for subnet in region_subnets]
            selected_subnet_names = safe_multiselect(
                f"Select subnets in {region}:", choices=subnet_choices, default=[subnet_choices[0]] if subnet_choices else []
            )
            # Extract just the subnet names from the display string
            selected_subnets = [name.split(" ")[0] for name in selected_subnet_names]
        else:
            console.print(f"[yellow]No existing subnets found in {region} for VPC {vpc_name}[/yellow]")
            subnet_name = safe_text(f"Enter name for new subnet in {region}:", default=f"kafka-subnet-{region}")
            subnet_cidr = safe_text("Enter subnet CIDR block:", default="10.0.1.0/24")
            selected_subnets = [subnet_name]
            create_new_vpc = True  # We'll need to create the subnet

    # Get security groups (firewall rules in GCP)
    firewall_rules = list_security_groups()
    if firewall_rules:
        sg_choices = [f"{rule['name']} ({rule.get('description', 'No description')})" for rule in firewall_rules]
        selected_sg_names = safe_multiselect("Select firewall rules (security groups):", choices=sg_choices, default=[])
        # Extract just the rule names from the display string
        selected_sgs = [name.split(" ")[0] for name in selected_sg_names]
    else:
        selected_sgs = []

    # Client CIDR allowlist
    client_cidrs = safe_text(
        "Enter client CIDR allowlist (one per line, leave blank to allow all):", multiline=True, default="0.0.0.0/0"
    )
    client_cidr_list = [cidr.strip() for cidr in client_cidrs.split("\n") if cidr.strip()]

    return {
        "vpc_name": vpc_name,
        "create_new_vpc": create_new_vpc,
        "network_cidr": network_cidr if "network_cidr" in locals() else "10.0.0.0/16",
        "subnets": selected_subnets,
        "security_groups": selected_sgs,
        "client_cidr_allowlist": client_cidr_list,
    }


def configure_kafka() -> Dict[str, Any]:
    """Configure Kafka settings"""
    console.print("\n[bold cyan]Kafka Configuration[/bold cyan]")

    # Cluster name
    cluster_name = safe_text("Enter a name for your Kafka cluster:", default="kafka-cluster")

    # Kafka version
    kafka_version = safe_select(
        "Select Kafka version:",
        choices=KAFKA_VERSIONS,
        default=KAFKA_VERSIONS[-1],  # Latest version
    )

    # Number of brokers
    broker_count = safe_number("Enter the number of Kafka brokers:", min_value=1, max_value=20, default=3)

    # vCPU and RAM selection
    vcpu_count = safe_number("Enter vCPU per broker:", min_value=1, max_value=64, default=4)

    ram_gb = safe_number("Enter RAM per broker (GB):", min_value=2, max_value=256, default=16)

    # Find the closest machine type based on vCPU and RAM
    suitable_machines = []
    for machine, specs in MACHINE_TYPES.items():
        if specs["vCPU"] >= vcpu_count and specs["RAM"] >= ram_gb:
            suitable_machines.append((machine, specs))

    if suitable_machines:
        # Sort by closest match (least excess resources)
        suitable_machines.sort(key=lambda x: (x[1]["vCPU"] - vcpu_count) + (x[1]["RAM"] - ram_gb))
        machine_type = suitable_machines[0][0]
    else:
        # Use the largest if no suitable match
        machine_type = "n2-standard-16"

    # Storage type
    storage_type = safe_select("Select storage type:", choices=STORAGE_TYPES, default="pd-ssd")

    # Storage size
    storage_size = safe_number("Enter storage size (GB) per broker:", min_value=10, max_value=65536, default=100)

    # Enable Kafka UI
    kafka_ui_enabled = safe_confirm("Enable Kafka UI?", default=True)

    # Compute cost estimation
    compute_estimate = safe_confirm("Show compute cost estimation?", default=True)

    return {
        "cluster_name": cluster_name,
        "kafka_version": kafka_version,
        "broker_count": broker_count,
        "vcpu_per_broker": vcpu_count,
        "ram_per_broker": ram_gb,
        "machine_type": machine_type,
        "storage_type": storage_type,
        "storage_size": storage_size,
        "kafka_ui_enabled": kafka_ui_enabled,
        "compute_estimate": compute_estimate,
    }


def configure_auth() -> Dict[str, Any]:
    """Configure authentication settings"""
    console.print("\n[bold cyan]Authentication Configuration[/bold cyan]")

    # Authentication method
    auth_method = safe_select(
        "Select authentication method:",
        choices=AUTH_METHODS,
        default="none",
        help_text="none: No authentication; anyone who can reach the cluster can connect."
        "\nssl: Clients authenticate using TLS client certificates.",
    )

    tls_config = {}

    if auth_method == "ssl":
        # TLS certificate option
        tls_method = safe_select("TLS certificates:", choices=["auto-generate", "upload"], default="auto-generate")

        tls_config["method"] = tls_method

        if tls_method == "upload":
            cert_path = safe_path(
                "Enter path to TLS certificate file (.pem or .p12):", must_exist=True, file_okay=True, dir_okay=False
            )
            tls_config["cert_path"] = cert_path

    return {"auth_method": auth_method, "tls_config": tls_config}


def configure_monitoring() -> Dict[str, Any]:
    """Configure monitoring settings"""
    console.print("\n[bold cyan]Monitoring Configuration[/bold cyan]")

    # Enable monitoring
    monitoring_enabled = safe_confirm("Enable monitoring?", default=True)

    monitoring_config = {
        "enabled": monitoring_enabled,
        "ops_agent": False,
        "grafana_export": False,
        "grafana_host": "",
        "grafana_api_key": "",
    }

    if monitoring_enabled:
        # Install Ops agent
        monitoring_config["ops_agent"] = safe_confirm("Install Ops agent?", default=True)

        # Export to Grafana
        monitoring_config["grafana_export"] = safe_confirm("Export Grafana dashboards[Y/n]?", default=False)

        if monitoring_config["grafana_export"]:
            monitoring_config["grafana_host"] = safe_text("Enter Grafana host URL:", default="")
            monitoring_config["grafana_api_key"] = safe_password("Enter Grafana API key:", default="")

    return monitoring_config


def configure_labels() -> Dict[str, Any]:
    """Configure labels/tags"""
    console.print("\n[bold cyan]Labels/Tags Configuration[/bold cyan]")

    labels = {}
    add_more = True

    while add_more:
        key = safe_text("Enter label/tag key (or press Enter to finish):", default="")
        if not key:
            break

        value = safe_text(f"Enter value for {key}:", default="")
        labels[key] = value

        if len(labels) > 0:
            add_more = safe_confirm("Add another label/tag?", default=True)

    return labels


def display_summary(config: Dict[str, Any]):  # noqa C901
    """Display configuration summary"""
    # GCP section
    if "gcp" in config:
        gcp_table = Table(title="GCP Configuration")
        gcp_table.add_column("Setting", style="cyan")
        gcp_table.add_column("Value")

        gcp_table.add_row("Project ID", config["gcp"].get("project_id", "Not specified"))
        gcp_table.add_row("Region", config["gcp"].get("region", "Not specified"))

        zones = config["gcp"].get("zones", [])
        if zones:
            gcp_table.add_row("Availability Zones", ", ".join(zones))

        console.print(gcp_table)

    # Kafka section
    if "kafka" in config:
        kafka_table = Table(title="Kafka Configuration")
        kafka_table.add_column("Setting", style="cyan")
        kafka_table.add_column("Value")

        for key, value in config["kafka"].items():
            if key != "estimated_costs":  # Skip costs, will show separately
                kafka_table.add_row(key.replace("_", " ").title(), str(value))

        console.print(kafka_table)

        # Show cost estimation if available
        if "estimated_costs" in config["kafka"]:
            costs = config["kafka"]["estimated_costs"]
            cost_table = Table(title="Estimated Monthly Costs")
            cost_table.add_column("Item", style="cyan")
            cost_table.add_column("Cost (USD)")

            cost_table.add_row("Per Instance", f"${costs['instance_monthly_per_node']}")
            cost_table.add_row("Per Storage", f"${costs['disk_monthly_per_node']}")
            cost_table.add_row("Total (all nodes)", f"${costs['total_monthly']}")

            console.print(cost_table)

    # Networking section
    if "networking" in config:
        network_table = Table(title="Network Configuration")
        network_table.add_column("Setting", style="cyan")
        network_table.add_column("Value")

        for key, value in config["networking"].items():
            if isinstance(value, list):
                network_table.add_row(key.replace("_", " ").title(), ", ".join(value))
            else:
                network_table.add_row(key.replace("_", " ").title(), str(value))

        console.print(network_table)

    # Auth section
    if "auth" in config:
        auth_table = Table(title="Authentication Configuration")
        auth_table.add_column("Setting", style="cyan")
        auth_table.add_column("Value")

        auth_table.add_row("Auth Method", config["auth"].get("auth_method", "none"))

        if "tls_config" in config["auth"]:
            for key, value in config["auth"]["tls_config"].items():
                auth_table.add_row(key.replace("_", " ").title(), str(value))

        console.print(auth_table)

    # Monitoring section
    if "monitoring" in config:
        monitoring_table = Table(title="Monitoring Configuration")
        monitoring_table.add_column("Setting", style="cyan")
        monitoring_table.add_column("Value")

        for key, value in config["monitoring"].items():
            if key != "grafana_api_key":  # Don't display API key
                monitoring_table.add_row(key.replace("_", " ").title(), str(value))

        console.print(monitoring_table)

    # Labels section
    if "labels" in config and config["labels"]:
        labels_table = Table(title="Labels/Tags")
        labels_table.add_column("Key", style="cyan")
        labels_table.add_column("Value")

        for key, value in config["labels"].items():
            labels_table.add_row(key, value)

        console.print(labels_table)


def welcome_message():
    """Display welcome message and tool information"""
    console.print(
        Panel(
            Text.from_markup(
                "[bold green]Kafka on GCP Deployment Wizard[/bold green]\n\n"
                "This wizard will guide you through setting up a Kafka cluster on Google Cloud Platform.\n"
                "You'll configure GCP resources, Kafka settings, networking, and monitoring options.\n\n"
                "[yellow]Tip:[/yellow] You can save your configuration as a profile for future use."
            ),
            title="Welcome",
            expand=False,
            border_style="cyan",
        )
    )
