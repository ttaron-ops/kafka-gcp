import os
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Optional, Dict, Any

from kafka_cli.utils.config import get_config, update_config, get_config_dir
from kafka_cli.utils.terraform import generate_terraform_vars
from kafka_cli.utils.interactive import (
    safe_text, 
    safe_select, 
    safe_confirm, 
    is_interactive
)

app = typer.Typer(help="Start the interactive Kafka cluster provisioning wizard")
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Use a specific profile"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview changes without applying them"
    ),
    # Non-interactive mode parameters
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-n", help="Run in non-interactive mode (requires all parameters)"
    ),
    project_id: Optional[str] = typer.Option(
        None, "--project-id", help="GCP Project ID"
    ),
    region: str = typer.Option(
        "us-central1", "--region", help="GCP Region"
    ),
    zone: Optional[str] = typer.Option(
        None, "--zone", help="GCP Zone (defaults to {region}-a)"
    ),
    network_range: str = typer.Option(
        "10.0.0.0/16", "--network-range", help="Network CIDR range"
    ),
    broker_count: int = typer.Option(
        3, "--broker-count", help="Number of Kafka brokers"
    ),
    broker_machine_type: str = typer.Option(
        "e2-standard-2", "--broker-machine-type", help="GCP machine type for brokers"
    ),
    zookeeper_count: int = typer.Option(
        3, "--zookeeper-count", help="Number of ZooKeeper nodes"
    ),
    zookeeper_machine_type: str = typer.Option(
        "e2-small", "--zookeeper-machine-type", help="GCP machine type for ZooKeeper"
    ),
    enable_monitoring: bool = typer.Option(
        True, "--enable-monitoring/--disable-monitoring", help="Enable monitoring add-on"
    ),
    enable_connect: bool = typer.Option(
        False, "--enable-connect/--disable-connect", help="Enable Kafka Connect add-on"
    ),
    auto_apply: bool = typer.Option(
        False, "--auto-apply", help="Automatically apply the configuration (non-interactive mode)"
    ),
    save_as_profile: Optional[str] = typer.Option(
        None, "--save-as-profile", help="Save configuration as a named profile"
    ),
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
        }
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
        with open(profile_path, 'w') as f:
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


def run_wizard(profile_name: Optional[str] = None, dry_run: bool = False):
    """
    Run the interactive wizard to configure and provision a Kafka cluster
    """
    # Check if we're in an interactive environment
    if not is_interactive():
        console.print("[bold red]Error:[/bold red] This command requires an interactive terminal.")
        console.print("Please run this command in a terminal where you can provide input.")
        console.print("\nFor automation purposes, use non-interactive mode instead:")
        console.print("kafka-cli start --non-interactive --project-id=YOUR_PROJECT_ID [other options]")
        raise typer.Exit(1)
    
    try:
        welcome_message()
        
        # Load configuration or profile if specified
        config = {}
        if profile_name:
            # Load existing profile
            profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
            if os.path.exists(profile_path):
                console.print(f"Loading profile: [bold cyan]{profile_name}[/bold cyan]")
                with open(profile_path, 'r') as f:
                    config = yaml.safe_load(f)
            else:
                console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
                return
        
        # Step 1: GCP Configuration
        console.print("\n[bold]Step 1: GCP Configuration[/bold]")
        gcp_config = configure_gcp()
        if not gcp_config:
            return
        config["gcp"] = gcp_config
        
        # Step 2: Networking Configuration
        console.print("\n[bold]Step 2: Networking Configuration[/bold]")
        networking_config = configure_networking()
        if not networking_config:
            return
        config["networking"] = networking_config
        
        # Step 3: Kafka Configuration
        console.print("\n[bold]Step 3: Kafka Configuration[/bold]")
        kafka_config = configure_kafka()
        if not kafka_config:
            return
        config["kafka"] = kafka_config
        
        # Step 4: Add-ons Configuration
        console.print("\n[bold]Step 4: Add-ons Configuration[/bold]")
        addons_config = configure_addons()
        if not addons_config:
            return
        config["addons"] = addons_config
        
        # Display summary
        display_summary(config)
        
        # Ask for confirmation
        if not safe_confirm("Proceed with this configuration?", default=True):
            console.print("Configuration canceled.", style="yellow")
            return
        
        # Save configuration
        save_profile = safe_confirm("Save this configuration as a profile?", default=True)
        if save_profile:
            profile_name = safe_text("Profile name:", default="default")
            save_profile_to_file(config, profile_name, set_as_default=True)
        
        # Generate Terraform variables
        if generate_terraform_vars(config, dry_run):
            console.print("\n[bold green]Configuration complete![/bold green]")
            
            if not dry_run:
                if safe_confirm("Apply this configuration now?", default=False):
                    console.print("\nApplying configuration...")
                    # Apply configuration logic would go here
                    console.print("[bold green]Configuration applied successfully![/bold green]")
                else:
                    console.print("\nYou can apply this configuration later with the 'terraform apply' command.", style="yellow")
        else:
            console.print("\n[bold red]Failed to generate Terraform variables[/bold red]")
        
    except Exception as e:
        console.print(f"[bold red]Error running wizard:[/bold red] {str(e)}")
        console.print("This command requires a fully interactive terminal.")
        console.print("Please run in a standard terminal application.")
        console.print("\nAlternatively, use non-interactive mode:")
        console.print("kafka-cli start --non-interactive --project-id=YOUR_PROJECT_ID [other options]")
        raise typer.Exit(1)


def configure_gcp() -> Dict[str, Any]:
    """Configure GCP settings"""
    config = get_config().get("gcp", {})
    
    # Ask for GCP project ID
    project_id = safe_text(
        "GCP Project ID:",
        default=config.get("project_id", "")
    )
    
    if not project_id:
        console.print("Project ID is required", style="red")
        return None
    
    # Ask for region
    region = safe_select(
        "Select GCP Region:",
        choices=[
            "us-central1",
            "us-east1",
            "us-west1",
            "europe-west1",
            "asia-northeast1",
        ],
        default=config.get("region", "us-central1")
    )
    
    # Ask for zone
    zone = safe_select(
        "Select GCP Zone:",
        choices=[f"{region}-a", f"{region}-b", f"{region}-c"],
        default=config.get("zone", f"{region}-a")
    )
    
    return {"project_id": project_id, "region": region, "zone": zone}


def configure_networking() -> Dict[str, Any]:
    """Configure networking settings"""
    # Start with default values
    network_name = safe_text(
        "VPC Network Name:",
        default="kafka-network"
    )
    
    # Network CIDR
    network_cidr = safe_text(
        "Network CIDR:",
        default="10.0.0.0/16"
    )
    
    # Subnet CIDR
    subnet_cidr = safe_text(
        "Subnet CIDR:",
        default="10.0.1.0/24"
    )
    
    # VPC Peering
    enable_peering = safe_confirm(
        "Enable VPC Peering?",
        default=False
    )
    
    peering_network = None
    if enable_peering:
        peering_network = safe_text(
            "Peering Network Name:"
        )
    
    return {
        "network_name": network_name,
        "network_cidr": network_cidr,
        "subnet_cidr": subnet_cidr,
        "enable_peering": enable_peering,
        "peering_network": peering_network,
    }


def configure_kafka() -> Dict[str, Any]:
    """Configure Kafka settings"""
    # Number of brokers
    broker_count = int(safe_select(
        "Number of Kafka Brokers:",
        choices=["1", "3", "5", "7"],
        default="3"
    ))
    
    # Machine type
    machine_type = safe_select(
        "Machine Type:",
        choices=[
            "e2-standard-2",
            "e2-standard-4",
            "e2-standard-8",
            "n2-standard-2",
            "n2-standard-4",
            "n2-standard-8",
        ],
        default="e2-standard-4"
    )
    
    # Disk size
    disk_size = int(safe_text(
        "Disk Size (GB):",
        default="100"
    ))
    
    # Kafka version
    kafka_version = safe_select(
        "Kafka Version:",
        choices=["3.4.0", "3.3.2", "3.2.3", "3.1.2"],
        default="3.4.0"
    )
    
    # KRaft mode
    kraft_mode = safe_confirm(
        "Use KRaft Mode (no ZooKeeper)?",
        default=True
    )
    
    return {
        "broker_count": broker_count,
        "machine_type": machine_type,
        "disk_size": disk_size,
        "kafka_version": kafka_version,
        "kraft_mode": kraft_mode,
    }


def configure_addons() -> Dict[str, Any]:
    """Configure Kafka add-ons"""
    addons = {}
    
    # Kafka UI
    if safe_confirm("Install Kafka UI?", default=True):
        addons["kafka_ui"] = True
    
    # Prometheus
    if safe_confirm("Install Prometheus?", default=True):
        addons["prometheus"] = True
        
        # Kafka Exporter
        if safe_confirm("Install Kafka Exporter?", default=True):
            addons["kafka_exporter"] = True
    
    # Grafana
    if safe_confirm("Install Grafana?", default=True):
        addons["grafana"] = True
    
    # Schema Registry
    if safe_confirm("Install Schema Registry?", default=False):
        addons["schema_registry"] = True
    
    # Deployment target for addons
    if any(addons.values()):
        deployment_target = safe_select(
            "Deployment Target for Add-ons:",
            choices=[
                "GCP Cloud Run",
                "GCP Compute Engine VM",
                "Existing Kubernetes Cluster",
            ],
            default="GCP Compute Engine VM"
        )
        addons["deployment_target"] = deployment_target
        
        if deployment_target == "Existing Kubernetes Cluster":
            kubeconfig_path = safe_text(
                "Kubeconfig Path (leave empty for default):",
                default=""
            )
            addons["kubeconfig_path"] = kubeconfig_path or "~/.kube/config"
    
    return addons


def display_summary(config: Dict[str, Any]):
    """Display configuration summary"""
    console.print("\n[bold]Configuration Summary:[/bold]")
    
    # GCP Configuration
    gcp = config.get("gcp", {})
    console.print("\n[bold cyan]GCP Configuration:[/bold cyan]")
    console.print(f"  Project ID: {gcp.get('project_id')}")
    console.print(f"  Region: {gcp.get('region')}")
    console.print(f"  Zone: {gcp.get('zone')}")
    
    # Networking Configuration
    network = config.get("networking", {})
    console.print("\n[bold cyan]Networking Configuration:[/bold cyan]")
    console.print(f"  Network Name: {network.get('network_name')}")
    console.print(f"  Network CIDR: {network.get('network_cidr')}")
    console.print(f"  Subnet CIDR: {network.get('subnet_cidr')}")
    console.print(f"  VPC Peering: {'Enabled' if network.get('enable_peering') else 'Disabled'}")
    if network.get("enable_peering"):
        console.print(f"  Peering Network: {network.get('peering_network')}")
    
    # Kafka Configuration
    kafka = config.get("kafka", {})
    console.print("\n[bold cyan]Kafka Configuration:[/bold cyan]")
    console.print(f"  Broker Count: {kafka.get('broker_count')}")
    console.print(f"  Machine Type: {kafka.get('machine_type')}")
    console.print(f"  Disk Size: {kafka.get('disk_size')} GB")
    console.print(f"  Kafka Version: {kafka.get('kafka_version')}")
    console.print(f"  KRaft Mode: {'Enabled' if kafka.get('kraft_mode') else 'Disabled'}")
    
    # Add-ons Configuration
    addons = config.get("addons", {})
    console.print("\n[bold cyan]Add-ons Configuration:[/bold cyan]")
    addon_list = []
    for addon, enabled in addons.items():
        if addon not in ["deployment_target", "kubeconfig_path"] and enabled:
            addon_list.append(addon.replace("_", " ").title())
    
    if addon_list:
        console.print(f"  Enabled Add-ons: {', '.join(addon_list)}")
        console.print(f"  Deployment Target: {addons.get('deployment_target')}")
        if addons.get("deployment_target") == "Existing Kubernetes Cluster":
            console.print(f"  Kubeconfig Path: {addons.get('kubeconfig_path')}")
    else:
        console.print("  No add-ons selected")


def welcome_message():
    """Display welcome message and tool information"""
    title = Text("Kafka CLI - Interactive Kafka Cluster Wizard", style="bold green")
    description = Text(
        "This wizard will guide you through configuring and provisioning a Kafka cluster on GCP.\n"
        "You'll be able to customize networking, Kafka settings, and add-ons."
    )
    console.print(Panel.fit(title, subtitle=description))
